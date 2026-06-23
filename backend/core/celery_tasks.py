from celery import Celery

from utility.logger import get_logger
from systems.ollama_client import OllamaClient
from db.database import SessionLocal
from db.models import StructuredPrompts

lg = get_logger(__file__)
c_app = Celery()
c_app.config_from_object("core.config")


@c_app.task(name="send_prompt_to_ai")
def send_prompt_to_ai(messages: list, prompt_id: str):
    """
    Background task to send prompt to AI and update database record.
    Args:
        messages (list): List of message dicts [{"role": "user", "content": "..."}]
        prompt_id (str): UUID of the StructuredPrompts record to update
    """
    lg.info(f"Processing AI prompt task for prompt_id: {prompt_id}")

    db = SessionLocal()
    st_prompt = None
    try:
        # Check if prompt exists
        st_prompt = (
            db.query(StructuredPrompts)
            .filter(StructuredPrompts.prompt_id == prompt_id)
            .first()
        )
        if not st_prompt:
            lg.error(f"StructuredPrompts with id {prompt_id} not found.")
            return

        st_prompt.status = "PROCESSING"
        db.commit()

        client = OllamaClient()
        # Ensure we're using the correct payload structure expected by OllamaClient
        payload = {"messages": messages, "stream": False}

        response = client.generate_chat_completion(payload)

        # Handle OllamaClient internal error handling convention
        if isinstance(response, dict) and "error" in response:
            lg.error(f"OllamaClient returned error: {response['error']}")
            st_prompt.status = "FAILED"
            st_prompt.error_message = response["error"]

        # Validate response structure for content
        elif "choices" in response and len(response["choices"]) > 0:
            ai_content = response["choices"][0]["message"]["content"]
            st_prompt.structured_prompt = ai_content
            st_prompt.status = "COMPLETED"

        # Fallback for unexpected success response structure
        else:
            lg.warning(f"Unexpected response format: {response}")
            st_prompt.status = "FAILED"
            st_prompt.error_message = "Unexpected response format from AI service"

        db.commit()

    except Exception as e:
        lg.error(f"Exception in send_prompt_to_ai task: {str(e)}")
        if st_prompt:
            try:
                st_prompt.status = "FAILED"
                st_prompt.error_message = str(e)
                db.commit()
            except Exception as db_e:
                lg.error(f"Failed to save error status to DB: {db_e}")
                db.rollback()
    finally:
        db.close()
