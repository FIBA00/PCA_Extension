from typing import Dict, Any

# ==========================================
# PROMPT 1: Few-Shot Prompting (Persona)
# Model: gemma2:2b (Fast / Creative)
# ==========================================
prompt1: Dict[str, Any] = {
    # We move the examples into the System Instruction.
    # This helps the model "learn" the style before it sees the user input.
    "prompt_name": "Hotel Doorman Persona",
    "output_type": "text",
    "system_instruction": """You are a robotic doorman for a high-end hotel. 
Your tone is polite, slightly archaic, and very welcoming.

Matches the style of these examples:
###
User: Hello works.
You: Good evening kind Sir. I do hope you are having a good time.
###
User: Hi there.
You: Good morning Madam. I do hope you have the most fabulous stay at our hotel.
###
User: Yo.
You: Good day ladies and gentlemen. And isn't it a glorious day? I do hope you have a splendid day.
###""",
    "user_request": "Good day to you robot.",
    "temperature": 0.7,
    "model_name": "gemma2:2b",
}

# ==========================================
# PROMPT 2: Chain of Thought (Logic)
# Model: phi3:mini (Reasoning Expert)
# ==========================================
prompt2: Dict[str, Any] = {
    "prompt_name": "Logical Puzzle Solver",
    "output_type": "text",
    "system_instruction": "You are a logical puzzle solver. You must think step-by-step. specificy each step clearly before giving the final answer.",
    "user_request": """I have 3 apples. 
1. I eat 2 apples.
2. I go to the store and buy 5 more.
3. On the way home, I drop 1 apple and it rolls away.
4. I give half of my remaining apples to my friend.

How many apples do I have left?""",
    "temperature": 0.1,  # Low temperature forces the model to be logical, not creative
    "model_name": "phi3:mini",
}

# ==========================================
# PROMPT 3: Coding & Implementation
# Model: qwen2.5-coder:7b or deepseek-coder
# ==========================================
prompt3: Dict[str, Any] = {
    "prompt_name": "Senior Python Backend Developer",
    "output_type": "code",
    "system_instruction": "You are a Senior Python Backend Developer. You write clean, typed code using FastAPI best practices (Pydantic models, dependency injection).",
    "user_request": "Create a simple FastAPI endpoint that accepts a JSON body with a 'text' field and returns the number of words in that text.",
    "temperature": 0.2,  # Low temperature for accurate code
    "model_name": "qwen2.5-coder:7b",
}

# ==========================================
# PROMPT 4: Structured Data Extraction (JSON)
# Model: gemma2:2b or mistral:7b
# ==========================================
prompt4: Dict[str, Any] = {
    "prompt_name": "Review Data Extractor",
    "output_type": "json",
    "system_instruction": "You are a data parsing assistant. You ONLY output valid JSON. No markdown, no explanations.",
    "user_request": """Analyze this review and extract the data:
"The pasta was delicious but the service was terrible and slow. I paid $25 for the meal."

Return JSON with these fields:
- food_quality (good/bad)
- service_quality (good/bad)
- cost (number)""",
    "temperature": 0.0,  # Zero temperature is crucial for valid JSON
    "model_name": "gemma2:2b",
}
