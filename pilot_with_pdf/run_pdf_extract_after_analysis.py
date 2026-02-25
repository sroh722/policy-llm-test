import re
import json
import requests
import glob
import os
import time
import pdfplumber
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
from datetime import datetime

# ---------- Config ----------
PDF_URL = "https://www.itib.gov.hk/en/publications/I%26T%20Blueprint%20Book_EN_single_Digital.pdf"
MODEL = "gpt-4.1-mini"

# ---------- Setup ----------
load_dotenv()
client = OpenAI()

# ---------- Few-shot block ----------
TAXONOMY = ["subsidy","tax_credit","grant","loan","export_control","local_content","procurement","standard","other"]


def load_latest_taxonomy(raw_dir: str = "pilot_with_pdf/data/raw") -> dict:
    """Load the most recent taxonomy_plan_recent.json from the analysis outputs.

    Returns a dict with keys `taxonomy` (list of {category,definition}) and `schema_fields` if found.
    Falls back to a minimal default if no file is found.
    """
    pattern = os.path.join(raw_dir, "taxonomy_plan_recent.json")
    files = glob.glob(pattern)
    if not files:
        return {
            "taxonomy": [{"category": c, "definition": ""} for c in TAXONOMY],
            "schema_fields": [
                "policy_name",
                "category",
                "description",
                "implementing_body",
                "target_sector",
                "funding_amount",
            ],
        }

    latest = sorted(files)[-1]
    try:
        with open(latest, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception:
        return {
            "taxonomy": [{"category": c, "definition": ""} for c in TAXONOMY],
            "schema_fields": [
                "policy_name",
                "category",
                "description",
                "implementing_body",
                "target_sector",
                "funding_amount",
            ],
        }


TAXONOMY_PLAN = load_latest_taxonomy()
TAXONOMY_CATEGORIES = [t.get("category") for t in TAXONOMY_PLAN.get("taxonomy", [])]
SCHEMA_FIELDS = TAXONOMY_PLAN.get("schema_fields", ["policy_name", "category", "description", "implementing_body", "target_sector", "funding_amount"])[:-0]

FEWSHOT_BLOCK = f"""
You are building a structured dataset of industrial policy and regulatory instruments.

Use the following category choices exactly as provided: {TAXONOMY_CATEGORIES}

Return ONLY valid JSON with the following keys (use null or empty list when missing):
{SCHEMA_FIELDS}

Rules:
- Do NOT invent details.
- Use exact quotes from the text when providing `evidence_spans` or quoted descriptions.
- If information is ambiguous, return null for that field.

Examples (illustrative):
Text: "Eligible firms may receive matching grants up to HKD 10 million for automation equipment upgrades."
JSON: {{"policy_name": null, "category": "grant", "description": "matching grants for automation equipment upgrades", "implementing_body": null, "target_sector": "manufacturing", "funding_amount": "up to HKD 10 million", "evidence_spans": ["matching grants up to HKD 10 million"]}}
""".strip()

# ---------- 1) Download PDF ----------
def download_pdf(url: str, out_path: Path, timeout: int = 60) -> None:
    headers = {"User-Agent": "Mozilla/5.0"}
    with requests.get(url, headers=headers, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

# ---------- 2) PDF -> text ----------
def pdf_to_text_limited(path: Path, skip_first: int = 8, max_pages: int = 5) -> str:
    pages = []
    with pdfplumber.open(path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Total pages in PDF: {total_pages}")

        start = skip_first
        end = min(skip_first + max_pages, total_pages)

        print(f"Processing pages {start} to {end - 1}")

        for i in range(start, end):
            text = pdf.pages[i].extract_text() or ""
            pages.append(text)

    return "\n".join(pages)

# ---------- 3) Chunking ----------
def chunk_text(text: str, max_chars: int = 5000, overlap: int = 500) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + max_chars])
        i += max_chars - overlap
    return chunks

# ---------- 4) LLM extraction (few-shot + retries + robust JSON parsing) ----------
def extract_fields(chunk: str) -> dict:
    prompt = FEWSHOT_BLOCK + f"""

Now process the next text.

Text:
{chunk}

Return ONLY JSON:
"""
    attempts = 3
    r = None
    for attempt in range(attempts):
        try:
            r = client.responses.create(
                model=MODEL,
                input=prompt,
                temperature=0,
                max_output_tokens=500,  # cost + consistency
            )
            break
        except Exception:
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)
                continue
            else:
                raise

    raw = getattr(r, "output_text", None)
    if not raw:
        try:
            raw = r.output[0].content[0].text
        except Exception:
            raw = str(r)

    clean = raw.strip()
    clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean)

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", clean, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

    return {"error": "Invalid JSON", "raw_output": clean[:1000]}

def main():
    timestamp_ymd = datetime.now().strftime("%Y%m%d")

    pdf_dir = Path("pilot_with_pdf/data/pdf")
    raw_dir = Path("pilot_with_pdf/data/raw")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    out_csv = Path(f"pilot_with_pdf/data/extract_analysis/hk_it_blueprint_extraction_{timestamp_ymd}.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    # Prefer an existing downloaded PDF if available
    candidates = list(pdf_dir.glob("hk_it_blueprint_*.pdf")) + list(raw_dir.glob("hk_it_blueprint_*.pdf"))
    if candidates:
        pdf_path = sorted(candidates)[-1]
        print(f"Using existing PDF: {pdf_path.resolve()}")
    else:
        pdf_path = pdf_dir / f"hk_it_blueprint_{timestamp_ymd}.pdf"
        print("Downloading PDF...")
        download_pdf(PDF_URL, pdf_path)
        print(f"Saved to {pdf_path.resolve()}")

    print("Extracting text...")
    text = pdf_to_text_limited(pdf_path, skip_first=8, max_pages=15)
    chunks = chunk_text(text, max_chars=4000, overlap=300)

    print("Number of chunks:", len(chunks))

    rows = []
    for idx, ch in enumerate(tqdm(chunks, desc="LLM extracting")):
        try:
            out = extract_fields(ch)
            out["chunk_id"] = idx
            rows.append(out)
        except Exception as e:
            rows.append({"chunk_id": idx, "error": str(e)})

    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    print(f"Done. Wrote {out_csv.resolve()}")

if __name__ == "__main__":
    main()