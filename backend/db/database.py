from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import settings
from fastapi import HTTPException
from utility.logger import get_logger

lg = get_logger(__file__)

SQLALCHEMY_DATABASE_URL = f"postgresql://{settings.DATABASE_USERNAME}:{settings.DATABASE_PASSWORD}@{settings.DATABASE_HOSTNAME}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"

try:
    lg.info(
        f"Connecting to database at {settings.DATABASE_HOSTNAME}:{settings.DATABASE_PORT}..."
    )
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    # Test the connection immediately on startup
    with engine.connect() as connection:
        lg.info("Successfully connected to the PostgreSQL database!")
    # Session factory
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # Declarative base
    Base = declarative_base()
    # Import models to ensure they are registered with SQLAlchemy's metadata
    from db import models
    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)
except Exception as e:
    lg.critical(
        f"FATAL: Database connection failed! \nURL: {SQLALCHEMY_DATABASE_URL} \nError: {e}"
    )
    # Re-raise if the app cannot function without DB
    raise e

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    except HTTPException as http_exc:
        # Re-raise authentication errors without logging to avoid console noise
        raise http_exc
    except Exception as e:
        lg.error(f"Database Session Error: {e}")
        db.rollback()
        raise e
    finally:
        db.close()
