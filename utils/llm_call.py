from litellm import completion
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

LLM_MODEL = os.environ.get("LLM_MODEL", "mistral/mistral-large-latest")


def get_response_from_llm(prompt):
    """
    Calls the LLM and returns the response.

    Args:
        prompt (str): The string to prompt the LLM with.

    Returns:
        str: The response from the LLM.
    """
    response = completion(
        model=LLM_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


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
