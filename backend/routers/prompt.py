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
from fastapi import APIRouter, status, Depends, Request, HTTPException

from core.schemas import PromptSchema, PromptSchemaOutput, PromptTaskResponse
from sqlalchemy.orm import Session
from db.database import get_db
from services.prompt_service import PromptService
from services.st_prompt_service import RestructuredPromptService
from utility.logger import get_logger


router = APIRouter(prefix="/pcrafter", tags=["prompts"])
prompt_service = PromptService()
st_prompt_service = RestructuredPromptService()
lg = get_logger(__file__)

author_id = str(uuid.uuid4())

# Note: We rely on the global exception handler in main.py to catch and log any DB errors
# This keeps our router code clean and the logging consistent.


# route for recieving prompts
@router.post(
    "/process",
    status_code=status.HTTP_200_OK,
    response_model=PromptSchemaOutput,
)
def create_new_prompt(
    prompt_data: PromptSchema,
    request: Request,
    db: Session = Depends(get_db),
) -> PromptSchemaOutput:
    """
    Create a new prompt and its structured version.

    Returns the structured prompt if created, otherwise returns the original prompt.
    """
    # Attempt to create structured prompt (synchronous normal flow)
    st_prompt = st_prompt_service.create_structured_prompt(
        db=db, prompt_data=prompt_data
    )
    if st_prompt:
        return st_prompt

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Failed to generate structured prompt.",
    )
