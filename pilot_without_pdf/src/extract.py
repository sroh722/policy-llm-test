import json
import re
from dotenv import load_dotenv
from openai import OpenAI

# Load API key
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

def extract_instrument_fields(text: str) -> dict:
    prompt = f"""
You extract industrial policy / regulatory instrument fields.

Return ONLY valid JSON with:

- instrument_name: string|null
- instrument_type: one of {TAXONOMY}
- administering_agency: string|null
- target_sector: string|null
- beneficiary: string|null
- funding_amount_or_cap: string|null
- cost_share_or_matching: string|null
- eligibility_rules: list[string]
- application_process: list[string]
- enforceability: one of ["binding","nonbinding","unclear"]
- evidence_spans: list[string] (short quotes <= 20 words; must appear in text)

Rules:
- If a field is not present, use null (or empty list).
- Do NOT guess.
- evidence_spans must be exact text snippets from the text.
- Return JSON only. No explanation.

TEXT:
{text}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )

    # Clean common formatting the model may add (```json ... ```)
    clean = response.output_text.strip()
    clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean)

    # Try parsing
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Fallback: try to extract the first {...} block
        m = re.search(r"\{.*\}", clean, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        return {
            "error": "Invalid JSON",
            "raw_output": response.output_text
        }

# Run if I want to check function module is loaded properly: python -c "import src.extract as e; print('HAS:', hasattr(e,'extract_instrument_fields')); print(dir(e))"