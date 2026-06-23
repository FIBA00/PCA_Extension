import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import urllib.parse


from core.schemas import UserCreateSchema, UserOutSchema
from db.models import User
from utility.logger import get_logger
from auth.oauth2 import hash_password, create_access_token
from core.custom_error_handlers import (
    UserAlreadyExists,
    UserNotFound,
    InvalidCredentials,
    RateLimitExceeded,
    WeakPasswordError,
)
from pydantic import EmailStr
from core.config import settings
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import HTTPException
from datetime import timedelta
import os

lg = get_logger(__file__)

_google_flow_cache = {}


class UserService:
    def get_google_login_url(self):
        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        }
        flow = Flow.from_client_config(
            client_config=client_config,
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
            ],
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
        authorization_url, state = flow.authorization_url(
            access_type="offline", include_granted_scopes="true"
        )
        _google_flow_cache[state] = flow
        return authorization_url

    # Duplicate simple process_google_auth removed; use main implementation below

    def get_or_create_anonymous_user(self, db: Session, anonymous_id: str):
        try:
            user = db.query(User).filter(User.user_id == anonymous_id).first()
            if not user:
                lg.info(f"Creating anonymous user with ID: {anonymous_id}")
                new_user = User(
                    user_id=anonymous_id,
                    username="Anonymous",
                    email="anonymous@promptcrafter.local",
                    password=hash_password(
                        "anonymous_secret_dummy_password"
                    ),  # Needs a dummy password
                    is_verified=False,
                    is_admin=False,
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                return new_user
            return user
        except SQLAlchemyError as e:
            db.rollback()
            lg.error(f"Error getting/creating anonymous user: {str(e)}")
            raise e

    def validate_password_strength(self, password: str):
        if len(password) < 8:
            raise WeakPasswordError("Password must be at least 8 characters long")
        if not any(char.isdigit() for char in password):
            raise WeakPasswordError("Password must contain at least one digit")
        if not any(char.isupper() for char in password):
            raise WeakPasswordError(
                "Password must contain at least one uppercase letter"
            )
        if not any(char.islower() for char in password):
            raise WeakPasswordError(
                "Password must contain at least one lowercase letter"
            )

    def create_new_user(self, user_data: UserCreateSchema, db: Session):
        try:
            try:
                user_exists = self.get_user_by_email(email=user_data.email, db=db)
                if user_exists:
                    raise UserAlreadyExists()
            except UserNotFound:
                # User does not exist, which is what we want for signup
                pass

            # create new user, first conver the shcema to dictionary
            user_data_dict = user_data.model_dump()

            # Validate password strength
            self.validate_password_strength(user_data_dict["password"])

            # check if the user has an id with the request
            if not user_data_dict.get("user_id"):
                user_data_dict["user_id"] = str(uuid.uuid4())

            # create a data base model
            new_user = User(**user_data_dict)
            # hash the password
            new_user.password = hash_password(user_data_dict["password"])

            lg.debug(f"Creating new user: {new_user.user_id}")

            # append the user to database
            db.add(new_user)
            db.commit()
            db.refresh(new_user)

            return UserOutSchema.model_validate(new_user)
        except IntegrityError as e:
            # Likely duplicate email
            db.rollback()
            lg.error(f"Integrity error creating user: {str(e)}")
            raise UserAlreadyExists()
        except SQLAlchemyError as e:
            # This catches ANY database error (connection lost, constraint violation, etc.)
            db.rollback()  # CRITICAL: Reset the db so it's clean for the next request
            lg.error(f"Database Error saving user: {str(e)}")
            raise e  # Re-raise it so the router knows something went wrong

        except Exception as e:
            # This catches any other unexpected Python error (like a bug in our code)
            lg.error(f"Unexpected Error in save_user: {str(e)}")
            raise e

    def get_user_by_id(self, user_id: str, db: Session):
        try:
            lg.debug(f"Getting user by id: {user_id}")
            user = db.query(User).filter(User.user_id == user_id).first()
            if user is None:
                raise UserNotFound()
            lg.debug(f"Found user by id: {user_id}: , user email: {user.email}")
            return UserOutSchema.model_validate(user)
        except SQLAlchemyError as e:
            # This catches ANY database error (connection lost, constraint violation, etc.)
            db.rollback()  # CRITICAL: Reset the db so it's clean for the next request
            lg.error(f"Database Error saving prompt: {str(e)}")
            raise e  # Re-raise it so the router knows something went wrong

        except Exception as e:
            # This catches any other unexpected Python error (like a bug in our code)
            lg.error(f"Unexpected Error in save_prompt: {str(e)}")
            raise e

    def ensure_anonymous_user(self, db: Session, user_id: str):
        """Ensure the anonymous user exists in the database."""
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                lg.info(f"Creating anonymous user {user_id}")
                # Create with dummy data
                anon_user = User(
                    user_id=user_id,
                    username="anonymous_guest",
                    email="anonymous@guest.com",
                    password=hash_password("anonymous"),
                    is_verified=False,
                    is_admin=False,
                )
                db.add(anon_user)
                db.commit()
        except IntegrityError:
            db.rollback()
            # Already exists (race condition)
            pass
        except Exception as e:
            lg.error(f"Error ensuring anonymous user: {str(e)}")
            # Log but don't crash, prompt save might fail with FK error but we tried

    def get_user_by_email(self, email: EmailStr, db: Session):
        try:
            lg.debug(f"Getting user by email: {email}")
            user = db.query(User).filter(User.email == email).first()
            if user is None:
                raise UserNotFound()
            lg.debug(f"Found user by email: {email}: , user id: {user.user_id}")
            return user  # NOTE:do not validate the user here becuase we need all the fields for the login function including hashed password!
        except SQLAlchemyError as e:
            # This catches ANY database error (connection lost, constraint violation, etc.)
            db.rollback()  # CRITICAL: Reset the db so it's clean for the next request
            lg.error(f"Database Error saving prompt: {str(e)}")
            raise e  # Re-raise it so the router knows something went wrong

        except Exception as e:
            # This catches any other unexpected Python error (like a bug in our code)
            lg.error(f"Unexpected Error in save_prompt: {str(e)}")
            raise e

    def delete_user(self, email: str, db: Session):
        return None

    def check_daily_limit(self, db: Session, user_id: str, cost: int = 1) -> bool:
        """
        Check if user has enough tokens for the request.
        Resets quota if it's a new day.
        Raises RateLimitExceeded if not enough tokens.
        """
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise UserNotFound()

            # Check date
            today = datetime.utcnow().date()
            if user.last_token_reset != today:
                # Reset
                lg.debug(f"Resetting tokens for user {user_id}")
                user.tokens_used_today = 0
                user.last_token_reset = today
                db.add(user)
                db.commit()
                db.refresh(user)

            if user.tokens_used_today + cost > user.daily_token_limit:
                lg.warning(f"User {user_id} exceeded daily token limit")
                raise RateLimitExceeded

            # Deduct (add usage)
            user.tokens_used_today += cost
            db.add(user)
            db.commit()
            db.refresh(user)

            lg.debug(
                f"User {user_id} used {cost} tokens. Balance: {user.daily_token_limit - user.tokens_used_today}"
            )
            return True

        except RateLimitExceeded as e:
            raise e
        except Exception as e:
            lg.error(f"Error checking daily limit: {str(e)}")
            raise e

    def update_user(self, user: User, user_data: dict, db: Session):
        lg.info(f"Updating user with email: {user.email}")
        # Update user fields based on provided data
        for key, value in user_data.items():
            if hasattr(user, key):
                setattr(user, key, value)
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
            lg.info(f"User updated successfully: {user.email}")
            return UserOutSchema.model_validate(user)
        except SQLAlchemyError as e:
            db.rollback()
            lg.error(f"Database Error updating user: {str(e)}")
            raise e
        except Exception as e:
            lg.error(f"Unexpected Error updating user: {str(e)}")
            raise e

        return None

    def store_refresh_token(
        self, user_id: str, token: str, expires_at: datetime, db: Session
    ):
        from db.models import RefreshToken
        from auth.oauth2 import hash_token

        try:
            token_hash = hash_token(token)
            refresh_token = RefreshToken(
                id=str(uuid.uuid4()),
                token_hash=token_hash,
                user_id=user_id,
                expires_at=expires_at,
            )
            db.add(refresh_token)
            db.commit()
            db.refresh(refresh_token)
            return refresh_token.id
        except Exception as e:
            db.rollback()
            lg.error(f"Error storing refresh token: {str(e)}")
            raise e

    def invalidate_refresh_token(self, token: str, db: Session):
        from db.models import RefreshToken
        from auth.oauth2 import verify_token

        try:
            refresh_tokens = (
                db.query(RefreshToken)
                .filter(RefreshToken.expires_at > datetime.now())
                .all()
            )
            for rt in refresh_tokens:
                if verify_token(token, rt.token_hash):
                    db.delete(rt)
                    db.commit()
                    lg.info(f"Refresh token invalidated for user {rt.user_id}")
                    return True
            return False
        except Exception as e:
            db.rollback()
            lg.error(f"Error invalidating refresh token: {str(e)}")
            raise e

    def invalidate_all_user_refresh_tokens(self, user_id: str, db: Session):
        from db.models import RefreshToken

        try:
            db.query(RefreshToken).filter(RefreshToken.user_id == user_id).delete()
            db.commit()
            lg.info(f"All refresh tokens invalidated for user {user_id}")
        except Exception as e:
            db.rollback()
            lg.error(f"Error invalidating all refresh tokens: {str(e)}")
            raise e

    def process_google_auth(self, request_url: str, db: Session):
        # Allow http for local testing
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        client_config = {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            }
        }

        # Retrieve the Flow object saved during login initiation using the state parameter
        parsed = urllib.parse.urlparse(request_url)
        query_params = urllib.parse.parse_qs(parsed.query)
        state = query_params.get("state", [None])[0]
        if not state:
            raise HTTPException(status_code=400, detail="Missing state parameter")
        flow = _google_flow_cache.pop(state, None)
        if not flow:
            raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

        try:
            flow.fetch_token(authorization_response=request_url)
        except Exception as e:
            lg.error(f"Error fetching token from Google: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail="Authorization failed. Ensure you are approving the request.",
            )

        credentials = flow.credentials

        try:
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")

        email = id_info.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email not provided by Google")

        try:
            # Check if user exists using direct query to avoid exception flow control
            user = db.query(User).filter(User.email == email).first()

            if not user:
                # Create new user
                username = id_info.get("name", email.split("@")[0])
                new_user = User(
                    user_id=str(uuid.uuid4()),
                    username=username,
                    password=hash_password("oauth_dummy"),
                    email=email,
                    is_verified=True,
                    oauth_provider="google",
                    oauth_id=id_info.get("sub"),
                )
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
                user = new_user
            else:
                # Update existing user to verified if not
                if not user.is_verified:
                    user.is_verified = True
                    user.oauth_provider = "google"
                    user.oauth_id = id_info.get("sub")
                    db.commit()
                    db.refresh(user)

            # Create tokens
            access_token = create_access_token(
                user_data={
                    "user_id": user.user_id,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "is_verified": user.is_verified,
                }
            )
            refresh_token = create_access_token(
                user_data={
                    "user_id": user.user_id,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "is_verified": user.is_verified,
                },
                refresh=True,
                expiry=timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRY_MINUTES),
            )

            # Store refresh token
            expires_at = datetime.now() + timedelta(
                minutes=settings.JWT_REFRESH_TOKEN_EXPIRY_MINUTES
            )
            self.store_refresh_token(user.user_id, refresh_token, expires_at, db)

            lg.info(f"User {user.email} logged in via Google")
            return {
                "message": "Login Successful",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {"email": user.email, "user_id": str(user.user_id)},
            }

        except SQLAlchemyError as e:
            db.rollback()
            lg.error(f"Database Error processing google auth: {str(e)}")
            raise e
        except Exception as e:
            lg.error(f"Unexpected Error processing google auth: {str(e)}")
            raise e
