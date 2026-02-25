import json
from dotenv import load_dotenv
from openai import OpenAI

# Load API key from .env
load_dotenv()

client = OpenAI()

TAXONOMY = [
    "subsidy",
    "tax_credit",
    "grant",
    "loan",
    "export_control",
    "local_content",
    "procurement",
    "standard",
    "other"
]

def classify_policy_text(text: str) -> dict:
    prompt = f"""
You are classifying industrial policy instruments.

Classify the policy text into exactly ONE instrument_type from:
{TAXONOMY}

Return ONLY valid JSON with keys:
- instrument_type (string)
- confidence (number between 0 and 1)
- evidence_span (short quote from text, <= 20 words)

If unclear, use instrument_type="other" and confidence<=0.4.

TEXT:
{text}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    try:
        return json.loads(response.output_text)
    except json.JSONDecodeError:
        # Fallback in case model returns malformed JSON
        return {
            "instrument_type": "other",
            "confidence": 0.0,
            "evidence_span": "",
            "error": "Invalid JSON response"
        }