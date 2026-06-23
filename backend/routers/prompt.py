# Procssing prompt
"""
This module defines the API endpoints for prompt management within the promptCrafter backend.

Imports:
    FileResponse (fastapi.responses): Used for sending files as responses from endpoints, if needed.
    Other imports provide schema definitions, authentication dependencies, database session management, and prompt-related services.

Note:
    FileResponse is currently imported for potential future use in endpoints that may need to return files (e.g., prompt exports or downloads).
"""

from typing import List, Union, Optional
from fastapi import APIRouter, status, Depends, HTTPException, Request

from core.schemas import PromptSchema, PromptSchemaOutput, PromptTaskResponse, TokenData
from auth.dependencies import get_current_user, get_optional_current_user
from core.custom_error_handlers import PromptNotModified, PromptsNotFoundForCurrentUser
from sqlalchemy.orm import Session
from db.database import get_db
from services.prompt_service import PromptService
from services.st_prompt_service import RestructuredPromptService
from services.user_service import UserService
from utility.logger import get_logger
from redis import Redis
from core.config import settings


router = APIRouter(prefix="/pcrafter", tags=["prompts"])
# router.mount("/static", StaticFiles(directory="static"), name="static")
prompt_service = PromptService()
st_prompt_service = RestructuredPromptService()
user_service = UserService()
lg = get_logger(__file__)

ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"

# Note: We rely on the global exception handler in main.py to catch and log any DB errors
# This keeps our router code clean and the logging consistent.


# route for recieving prompts
@router.post(
    "/process",
    status_code=status.HTTP_200_OK,
    response_model=Union[PromptSchemaOutput, PromptTaskResponse, PromptSchema],
)
def create_new_prompt(
    prompt_data: PromptSchema,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[TokenData] = Depends(get_current_user),
) -> Union[PromptSchemaOutput, PromptTaskResponse, PromptSchema]:
    """
    Create a new prompt and its structured version.

    Returns the structured prompt if created, otherwise returns the original prompt.
    """
    author_id = current_user.user_id if current_user else ANONYMOUS_USER_ID
    use_ai = current_user.is_verified if current_user else False

    # Rate limiting
    if current_user and current_user.is_verified:
        user_service.check_daily_limit(db=db, user_id=current_user.user_id, cost=1)
    elif not current_user:
        redis = Redis.from_url(settings.REDIS_URL)
        client_ip = request.client.host
        key = f"anonymous_limit:{client_ip}"
        count = redis.get(key)
        if count and int(count) >= 3:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded for anonymous users. Please login to continue using the service."
            )
        redis.incr(key)
        redis.expire(key, 86400)

    # Ensure anonymous user exists
    if author_id == ANONYMOUS_USER_ID:
        user_service.get_or_create_anonymous_user(db=db, anonymous_id=ANONYMOUS_USER_ID)
        user_service.ensure_anonymous_user(db=db, user_id=ANONYMOUS_USER_ID)

    # Save original prompt
    new_prompt = prompt_service.save_prompt(db=db, prompt_data=prompt_data, author_id=author_id)
    lg.debug(f"Original prompt: {new_prompt}")

    # Attempt to create structured prompt
    st_prompt = st_prompt_service.create_structured_prompt(
        db=db, prompt_data=new_prompt, use_ai=use_ai
    )
    if st_prompt:
        if use_ai:
            return PromptTaskResponse(
                prompt_id=st_prompt.structured_prompt_id,
                status=st_prompt.status,
            )
        return st_prompt
    # Fallback: return the original prompt data
    return new_prompt


@router.get(
    "/status/{prompt_id}",
    status_code=status.HTTP_200_OK,
    response_model=PromptSchemaOutput,
)
def get_generation_status(
    prompt_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Check the status of an AI prompt generation task.
    """
    st_prompt = st_prompt_service.get_structured_prompt_by_id(
        prompt_id=prompt_id, db=db
    )
    if not st_prompt:
        raise HTTPException(status_code=404, detail="Structured prompt not found")

    # Ensure user owns it
    if str(st_prompt.details.author_id) != str(current_user.user_id):
        raise HTTPException(
            status_code=403, detail="Not authorized to view this prompt"
        )

    return st_prompt


# NOTE: so instead of separately returning the prompt and structured prompt for this routes
# we can create schema to return all the info related to the prompt id
# since author_id is tied to the restructured prompt and non structured prompt


# If user is implemented the uncomment the below path operator
@router.get("/", status_code=status.HTTP_200_OK, response_model=List[PromptSchema])
def get_all_previous_prompts(
    current_user=Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Retrieve all previously created prompts.
    This endpoint fetches all prompts stored in the database.

    Args:
        db (Session, optional): SQLAlchemy database session dependency.

    Returns:
        List[PromptSchema]: A list of all prompt records.
    """
    # get historical prompts
    # TODO: this requeires user id  dependency to retrieve the desired prompt
    # later implement user based retreival , something prompts for the current user onl.
    all_previous_prompts = prompt_service.get_all_prompt(
        user_id=current_user.user_id, db=db
    )
    if all_previous_prompts is None:
        raise PromptsNotFoundForCurrentUser
    return all_previous_prompts


@router.get("/{prompt_id}", status_code=status.HTTP_200_OK, response_model=PromptSchema)
def get_all_previous_prompt_by_id(
    prompt_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve a prompt by its unique identifier.

    This endpoint fetches a single prompt from the database using its prompt_id. User-based retrieval is
    planned for future implementation to allow fetching prompts specific to the current user.

    Args:
        prompt_id (str): The unique identifier of the prompt.
        db (Session, optional): SQLAlchemy database session dependency.

    Returns:
        PromptSchema: The prompt record matching the given ID.
    """
    # get historical prompts
    # TODO: this requeires user id  dependency to retrieve the desired prompt
    # later implement user based retreival , something prompts for the current user onl.
    all_previous_prompts = prompt_service.get_prompt_by_id(
        user_id=current_user.user_id, prompt_id=prompt_id, db=db
    )
    if all_previous_prompts is None:
        raise PromptsNotFoundForCurrentUser
    return all_previous_prompts


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(
    prompt_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a prompt by its unique identifier.

    This endpoint deletes a prompt from the database using its prompt_id. User-based authorization is
    required for this operation and will be implemented in the future.

    Args:
        prompt_id (str): The unique identifier of the prompt to delete.
        db (Session, optional): SQLAlchemy database session dependency.

    Returns:
        None
    """
    # NOTE: this requires user id to operate
    if prompt_service.delete_prompt(
        user_id=current_user.user_id, prompt_id=prompt_id, db=db
    ):
        return HTTPException(
            status_code=status.HTTP_204_NO_CONTENT,
            detail="Prompt deleted successfully.",
        )


@router.post("/{prompt_id}", status_code=status.HTTP_200_OK)
def update_prompt(
    prompt_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing prompt by its unique identifier.

    This endpoint is a placeholder for updating a prompt in the database using its prompt_id. User-based
    authorization is required for this operation and will be implemented in the future.

    Args:
        prompt_id (str): The unique identifier of the prompt to update.
        db (Session, optional): SQLAlchemy database session dependency.

    Returns:
        None
    """
    # NOTE: this also requires user id to operate
    pass
