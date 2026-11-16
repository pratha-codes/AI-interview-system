from litellm import completion
import os
import json
import re
import time
from dotenv import load_dotenv
from litellm.exceptions import ServiceUnavailableError

load_dotenv()

LLM_MODEL = os.environ.get("LLM_MODEL", "gemini/gemini-3.1-flash-lite")
fallback_models = os.environ.get("LLM_FALLBACK_MODELS")
if fallback_models is None:
    fallback_models = "gemini/gemini-3.6-flash" if LLM_MODEL.startswith("gemini/") else ""
LLM_MODELS = tuple(
    dict.fromkeys(
        [
            LLM_MODEL,
            *(model.strip() for model in fallback_models.split(",") if model.strip()),
        ]
    )
)


def get_response_from_llm(prompt):
    """
    Calls the LLM and returns the response.

    Args:
        prompt (str): The string to prompt the LLM with.

    Returns:
        str: The response from the LLM.
    """
    for model_index, model in enumerate(LLM_MODELS):
        for attempt in range(2):
            try:
                response = completion(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content
            except ServiceUnavailableError:
                if attempt == 0:
                    time.sleep(1)
                elif model_index == len(LLM_MODELS) - 1:
                    raise


def parse_json_response(response):
    """Parse JSON from LLM response, handling markdown blocks and extra text."""
    if not response:
        return None

    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None
