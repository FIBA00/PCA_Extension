from core.schemas import PromptSchema, PromptSchemaOutput
from utility.logger import get_logger

from core.config import settings
from systems.ollama_client import OllamaClient

lg = get_logger(script_path=__file__)


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
            use_ai (bool): Whether AI generation is enabled (verified users only).
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

        result = None
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
            if isinstance(response, dict) and "error" in response:
                raise RuntimeError(response["error"])
            # Extract content from response (assuming OpenAI format as implied by endpoint structure)
            if "choices" in response and len(response["choices"]) > 0:
                ai_content = response["choices"][0]["message"]["content"]
            else:
                lg.warning(f"Unexpected AI response format: {response}")
                return self.create_prompt_normal_way(prompt_data)

            # For now, we populate 'structured_prompt' with the AI Version
            # and keep 'natural_prompt' as the baseline assembled version
            result = PromptSchemaOutput(
                structured_prompt=ai_content,
                natural_prompt=natural_base,
                details=prompt_data,
            )
            if not result:
                # If use_ai is False, don't attempt AI generation
                lg.debug("AI generation disabled. Using normal prompt generation.")
                result = self.create_prompt_normal_way(prompt_data)
            return result
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
