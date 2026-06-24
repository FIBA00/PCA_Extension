import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException
from db.models import StructuredPrompts
from core.schemas import PromptSchema, PromptSchemaOutput
from utility.logger import get_logger

from systems.prompt_system import PromptSystem
from core.celery_tasks import send_prompt_to_ai

lg = get_logger(script_path=__file__)


class RestructuredPromptService:
    """
    Service class for managing structured (restructured) prompts in the database.
    Provides methods to create, save, delete, update, and retrieve structured prompts.
    Utilizes PromptSystem for prompt formatting and interacts with the database via SQLAlchemy sessions.
    """

    def __init__(self):
        """
        Initialize the RestructuredPromptService with a PromptSystem instance.
        """
        self.psystem = PromptSystem()

    def create_structured_prompt(
        self,
        db: Session,
        prompt_data: PromptSchema,
    ):
        """
        Create a structured prompt. Tries AI generation first,
        falls back to functional template if AI fails.
        Args:
            db (Session): SQLAlchemy database session.
            prompt_data (PromptSchema): Data required to generate the prompt.
        Returns:
            PromptSchemaOutput: The generated structured and natural prompt.
        """
        prompt_id = str(uuid.uuid4())

        # Try AI-powered generation first
        try:
            st_prompt = self.psystem.create_prompt_using_ai(prompt_data=prompt_data)
            if st_prompt and st_prompt.structured_prompt:
                st_prompt.structured_prompt_id = prompt_id
                lg.info(f"AI prompt generation succeeded for {prompt_id}")
                return st_prompt
            else:
                lg.error("AI prompt generation failed")
                raise HTTPException(status_code=500, detail="AI generation failed")

            lg.warning("AI returned empty result, falling back to functional flow.")
        except Exception as e:
            lg.warning(f"AI prompt generation failed, falling back to functional: {e}")
            raise
       
        # Fallback: functional template-based restructuring
        try:
            st_prompt = self.psystem.create_prompt_normal_way(prompt_data=prompt_data)
            st_prompt.structured_prompt_id = prompt_id
            return st_prompt
        except Exception as e:
            lg.error(f"Error while creating structured_prompt: {str(e)}")
            raise e

    def save_structured_prompt(
        self,
        structured_prompt: PromptSchemaOutput,
        db: Session,
        author_id: str = None,
        original_prompt_id: str = None,
        prompt_id: str = None,
    ):
        """
        Save a structured prompt to the database.
        Args:
            structured_prompt (PromptSchemaOutput): The prompt object to save.
            db (Session): SQLAlchemy database session.
            author_id (str): The ID of the author.
            original_prompt_id (str): The ID of the original prompt (optional).
            prompt_id (str): Explicit Prompt ID (optional)
        Returns:
            PromptSchemaOutput: The validated prompt object after saving.
        Raises:
            ValueError: If author_id is missing.
            SQLAlchemyError: If a database error occurs.
            Exception: For any other unexpected errors.
        """
        lg.debug("Saving the restructured prompts.")
        try:
            st_prompt_dict = structured_prompt.model_dump()
            # Remove details as it is not a column in DB
            if "details" in st_prompt_dict:
                del st_prompt_dict["details"]

            # Remove structured_prompt_id as DB uses prompt_id
            if "structured_prompt_id" in st_prompt_dict:
                del st_prompt_dict["structured_prompt_id"]

            # Generate new PK or use provided for structured_prompts table
            st_prompt_dict["prompt_id"] = (
                str(prompt_id) if prompt_id else str(uuid.uuid4())
            )

            # Assign foreign keys
            if author_id:
                st_prompt_dict["author_id"] = str(author_id)
            if original_prompt_id:
                st_prompt_dict["original_prompt_id"] = str(original_prompt_id)

            if not st_prompt_dict.get("author_id"):
                # NOTE: if we generate new uuid here it creates problem on retreival. so we must warn or raise error if there is no author id in the prompt data.
                raise ValueError("Author ID is required to save structured prompt.")

            new_st_prompt = StructuredPrompts(**st_prompt_dict)
            db.add(instance=new_st_prompt)
            db.commit()
            db.refresh(instance=new_st_prompt)
        except SQLAlchemyError as e:
            # This catches ANY database error (connection lost, constraint violation, etc.)
            db.rollback()  # CRITICAL: Reset the db so it's clean for the next request
            lg.error(f"Database Error saving prompt: {str(e)}")
            raise e  # Re-raise it so the router knows something went wrong

        except Exception as e:
            # This catches any other unexpected Python error (like a bug in our code)
            lg.error(f"Unexpected Error in save_prompt: {str(e)}")
            raise e

    def get_structured_prompt_by_id(
        self, prompt_id: str, db: Session
    ) -> PromptSchemaOutput:
        """
        Retrieve a single structured prompt by its Prompt ID (UUID).
        Args:
            prompt_id (str): The structured prompt ID.
            db (Session): SQLAlchemy database session.
        Returns:
            PromptSchemaOutput: The structure prompt object or None.
        """
        st_prompt_db = (
            db.query(StructuredPrompts)
            .filter(StructuredPrompts.prompt_id == prompt_id)
            .first()
        )
        if not st_prompt_db:
            return None

        # Reconstruct PromptSchema for details
        # Note: We need to fetch original prompt info?
        # The schema requires details: PromptSchema.
        # But StructuredPrompts database model might imply we can reach original prompt via relationship.
        # `st_prompt_db.original_prompt` should be available if relationship is loaded.

        details = PromptSchema(
            prompt_id=st_prompt_db.original_prompt.prompt_id
            if st_prompt_db.original_prompt
            else None,
            author_id=st_prompt_db.author_id,
            created_at=st_prompt_db.original_prompt.created_at
            if st_prompt_db.original_prompt
            else None,
            title=st_prompt_db.original_prompt.title
            if st_prompt_db.original_prompt
            else None,
            role=st_prompt_db.original_prompt.role
            if st_prompt_db.original_prompt
            else None,
            task=st_prompt_db.original_prompt.task
            if st_prompt_db.original_prompt
            else None,
            output=st_prompt_db.original_prompt.output
            if st_prompt_db.original_prompt
            else None,
            tags=st_prompt_db.original_prompt.tags
            if st_prompt_db.original_prompt
            else [],
            constraints=st_prompt_db.original_prompt.constraints
            if st_prompt_db.original_prompt
            else None,
            personality=st_prompt_db.original_prompt.personality
            if st_prompt_db.original_prompt
            else None,
        )

        return PromptSchemaOutput(
            structured_prompt_id=st_prompt_db.prompt_id,
            structured_prompt=st_prompt_db.structured_prompt,
            natural_prompt=st_prompt_db.natural_prompt,
            status=st_prompt_db.status or "COMPLETED",  # Default for old records
            error_message=st_prompt_db.error_message,
            details=details,
        )
