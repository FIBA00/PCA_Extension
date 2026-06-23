# Procssing prompt
"""
This module defines the API endpoints for prompt management within the promptCrafter backend.

Imports:
    FileResponse (fastapi.responses): Used for sending files as responses from endpoints, if needed.
    Other imports provide schema definitions, authentication dependencies, database session management, and prompt-related services.

Note:
    FileResponse is currently imported for potential future use in endpoints that may need to return files (e.g., prompt exports or downloads).
"""

import uuid
from typing import Union
from fastapi import APIRouter, status, Depends, HTTPException, Request

from core.schemas import PromptSchema, PromptSchemaOutput, PromptTaskResponse
from sqlalchemy.orm import Session
from db.database import get_db
from services.prompt_service import PromptService
from services.st_prompt_service import RestructuredPromptService
from services.user_service import UserService
from utility.logger import get_logger


router = APIRouter(prefix="/pcrafter", tags=["prompts"])
# router.mount("/static", StaticFiles(directory="static"), name="static")
prompt_service = PromptService()
st_prompt_service = RestructuredPromptService()
user_service = UserService()
lg = get_logger(__file__)

author_id = str(uuid.uuid4())

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
) -> Union[PromptSchemaOutput, PromptTaskResponse, PromptSchema]:
    """
    Create a new prompt and its structured version.

    Returns the structured prompt if created, otherwise returns the original prompt.
    """
    # Ensure anonymous user exists

    # Save original prompt
    new_prompt = prompt_service.save_prompt(
        db=db, prompt_data=prompt_data, author_id=author_id
    )
    lg.debug(f"Original prompt: {new_prompt}")

    # Attempt to create structured prompt
    st_prompt = st_prompt_service.create_structured_prompt(
        db=db, prompt_data=new_prompt
    )
    if st_prompt:
        return PromptTaskResponse(
            prompt_id=st_prompt.structured_prompt_id,
            status=st_prompt.status,
        )
    else:
        return st_prompt
    # Fallback: return the original prompt data
    return new_prompt
