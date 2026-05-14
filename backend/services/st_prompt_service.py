import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError


from db.models import StructuredPrompts
from core.schemas import PromptSchema, PromptSchemaOutput
from utility.logger import get_logger


from core.ollama_client import OllamaClient
from core.celery_tasks import send_prompt_to_ai
from core.config import settings

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
        self, db: Session, prompt_data: PromptSchema, use_ai: bool = False
    ):
        """
        Create a structured prompt using the provided prompt data and save it to the database.
        This method first saves a placeholder (None) and then generates the structured prompt using PromptSystem.
        Args:
            db (Session): SQLAlchemy database session.
            prompt_data (PromptSchema): Data required to generate the prompt.
            use_ai (bool): Whether to use AI for prompt generation.
        Returns:
            PromptSchemaOutput: The generated structured and natural prompt.
        """
        try:
            if use_ai:
                # Async AI Flow
                prompt_id = str(uuid.uuid4())
                natural = self.psystem.build_natural_prompt(
                    prompt_data.role,
                    prompt_data.task,
                    prompt_data.constraints,
                    prompt_data.output,
                    prompt_data.personality,
                )

                # Create Pending Object
                st_prompt = PromptSchemaOutput(
                    structured_prompt_id=prompt_id,
                    structured_prompt=None,
                    natural_prompt=natural,
                    status="PENDING",
                    details=prompt_data,
                )

                # Save immediately to DB with PENDING status
                self.save_structured_prompt(
                    structured_prompt=st_prompt,
                    db=db,
                    author_id=prompt_data.author_id,
                    original_prompt_id=prompt_data.prompt_id,
                    prompt_id=prompt_id,
                )

                # Prepare and Dispatch Celery Task
                messages = self.psystem.prepare_ai_messages(prompt_data)
                send_prompt_to_ai.delay(messages=messages, prompt_id=prompt_id)

                return st_prompt

            else:
                # Synchronous Normal Flow
                prompt_id = str(uuid.uuid4())
                st_prompt = self.psystem.create_prompt_normal_way(
                    prompt_data=prompt_data
                )
                st_prompt.structured_prompt_id = prompt_id

                self.save_structured_prompt(
                    structured_prompt=st_prompt,
                    db=db,
                    author_id=prompt_data.author_id,
                    original_prompt_id=prompt_data.prompt_id,
                    prompt_id=prompt_id,
                )

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

    def delete_structured_prompt(self, structured_prompt_id: str, db: Session):
        """
        Delete a structured prompt from the database by its ID.
        Args:
            structured_prompt_id (str): The ID of the prompt to delete.
            db (Session): SQLAlchemy database session.
        Returns:
            None
        """
        lg.debug("Deleting the restructured prompts.")
        return None

    def update_structured_prompt(self, structured_prompt_id: str, db: Session):
        """
        Update a structured prompt in the database by its ID.
        Args:
            structured_prompt_id (str): The ID of the prompt to update.
            db (Session): SQLAlchemy database session.
        Returns:
            None
        """
        lg.debug("Updating the restructured prompts.")
        return None

    def delete_all_structured_prompt(self, user_id: str, db: Session):
        """
        Delete all structured prompts for a given user.
        Args:
            user_id (str): The ID of the user whose prompts should be deleted.
            db (Session): SQLAlchemy database session.
        Returns:
            None
        """
        lg.debug("Deleting all the restructured prompts.")
        return None

    def get_all_restructured_prompt(self, db: Session):
        """
        Retrieve all restructured prompts from the database.
        Args:
            db (Session): SQLAlchemy database session.
        Returns:
            None
        """
        lg.debug("Getting all the restructured prompts.")
        return None

    def get_all_restructured_prompt_by_user_id(self, id: str, db: Session):
        """
        Retrieve all restructured prompts for a specific user by user ID.
        Args:
            id (str): The user ID.
            db (Session): SQLAlchemy database session.
        Returns:
            None
        """
        lg.debug("Getting all the restructured prompts.")
        return None

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

    def get_one_structured_prompt_by_user_id(self, id: str, db: Session):
        """
        Retrieve a single structured prompt for a specific user by user ID.
        Args:
            id (str): The user ID.
            db (Session): SQLAlchemy database session.
        Returns:
            None
        """
        lg.debug("Getting all the restructured prompts.")
        return None


class PromptSystem:
    """
    System for generating structured and natural prompts from user input.
    Provides methods for both functional and AI-based prompt creation.
    """

    def create_prompt_normal_way(self, prompt_data: PromptSchema) -> PromptSchemaOutput:
        """
        Generate a structured and natural prompt using functional template rendering.
        Args:
            prompt_data (PromptSchema): The input data for prompt creation.
        Returns:
            PromptSchemaOutput: The structured and natural prompt output.
        """
        role = prompt_data.role
        task = prompt_data.task
        constraints = prompt_data.constraints
        output = prompt_data.output
        personality = prompt_data.personality

        structured = self.build_structured_prompt(
            role=role,
            task=task,
            constraints=constraints,
            output=output,
            personality=personality,
        )
        natural = self.build_natural_prompt(
            role=role,
            task=task,
            constraints=constraints,
            output=output,
            personality=personality,
        )
        return PromptSchemaOutput(
            structured_prompt=structured,
            natural_prompt=natural,
            details=prompt_data,
            status="COMPLETED",
        )

    def prepare_ai_messages(self, prompt_data: PromptSchema) -> list:
        natural_base = self.build_natural_prompt(
            prompt_data.role,
            prompt_data.task,
            prompt_data.constraints,
            prompt_data.output,
            prompt_data.personality,
        )
        system_instruction = (
            "You are an expert prompt engineer. Refine the following user request into a clear, "
            "structured, and highly effective prompt. Return ONLY the improved prompt text."
        )
        return [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": natural_base},
        ]

    def create_prompt_using_ai(self, prompt_data: PromptSchema) -> PromptSchemaOutput:
        """
        Generate a structured and natural prompt using an AI model (e.g., OllamaClient).
        Args:
            prompt_data (PromptSchema): The input data for prompt creation.
        Returns:
            PromptSchemaOutput: The structured and natural prompt output.
        """
        # Fallback to normal way if anything goes wrong or for comparison
        natural_base = self.build_natural_prompt(
            prompt_data.role,
            prompt_data.task,
            prompt_data.constraints,
            prompt_data.output,
            prompt_data.personality,
        )

        try:
            # TODO: add option for changing client in the future for openai or custom ai.
            client = OllamaClient(
                host=settings.OLLAMA_HOST,
                model=settings.OLLAMA_MODEL,
                timeout=settings.OLLAMA_TIMEOUT,
            )

            system_instruction = (
                "You are an expert prompt engineer. Refine the following user request into a clear, "
                "structured, and highly effective prompt. Return ONLY the improved prompt text."
            )

            payload = {
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": natural_base},
                ],
                "stream": False,
            }

            response = client.generate_chat_completion(payload)

            # Extract content from response (assuming OpenAI format as implied by endpoint structure)
            if "choices" in response and len(response["choices"]) > 0:
                ai_content = response["choices"][0]["message"]["content"]
            else:
                lg.warning(f"Unexpected AI response format: {response}")
                return self.create_prompt_normal_way(prompt_data)

            # For now, we populate 'structured_prompt' with the AI Version
            # and keep 'natural_prompt' as the baseline assembled version
            return PromptSchemaOutput(
                structured_prompt=ai_content,
                natural_prompt=natural_base,
                details=prompt_data,
            )

        except Exception as e:
            lg.error(f"Error in create prompt using ai: {str(e)}")
            return self.create_prompt_normal_way(prompt_data)

    def build_structured_prompt(self, role, task, constraints, output, personality):
        """
        Build a structured prompt string from the provided components.
        Args:
            role (str): The role or contextual setting.
            task (str): The objective or task.
            constraints (str): Constraints and resources.
            output (str): Preferred output style.
            personality (str): Personal touch/personality.
        Returns:
            str: The formatted structured prompt.
        """
        return f"""
    [1. ROLE or CONTEXTUAL SETTING]: Imagine you are a {role}.

    [2. OBJECTIVE or TASK]: I want you to help me {task}.
    [3. CONSTRAINTS & RESOURCES]: Here’s what I already have / can't do / must consider:
    {constraints}

    [4. PREFERRED OUTPUT STYLE]: I want the response to be in {output}.

    [5. BONUS – PERSONAL TOUCH]: Think like {personality}.
    """.strip()

    def build_natural_prompt(self, role, task, constraints, output, personality):
        """
        Build a natural language prompt string from the provided components.
        Args:
            role (str): The role or contextual setting.
            task (str): The objective or task.
            constraints (str): Constraints and resources.
            output (str): Preferred output style.
            personality (str): Personal touch/personality.
        Returns:
            str: The formatted natural prompt.
        """
        return f"""
    Imagine you are {role}.
    I want you to help me {task}.
    Constraints: {constraints}
    Output: {output}
    Act like {personality}.
    """.strip()
