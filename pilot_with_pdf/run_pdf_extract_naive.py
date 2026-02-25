import re
import json
import requests
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

FEWSHOT_BLOCK = f"""
You are building a structured dataset of industrial policy and regulatory instruments.

Definition:
A "policy instrument" is a concrete, actionable measure such as:
- financial support (grant/subsidy/loan) with clear support terms
- tax incentive (credit/deduction/allowance)
- export restriction or licensing requirement
- local content/sourcing requirement
- procurement preference/requirement
- mandatory standard/compliance requirement

If the text is only strategy/vision/narrative without a concrete instrument, use instrument_type="other".

Return ONLY valid JSON with keys:
- instrument_type: one of {TAXONOMY}
- target_sector: string|null
- funding_amount_or_cap: string|null
- eligibility_rules: list[string]
- evidence_spans: list[string]  (exact quotes <= 20 words from the text)

Rules:
- Do NOT invent details.
- If not explicitly stated, use null or empty list.
- evidence_spans must be copied verbatim from the text.
- Prefer "other" when unclear.

Examples:
Text: "The Government aims to strengthen Hong Kong’s innovation ecosystem and build a vibrant I&T hub."
JSON: {{"instrument_type":"other","target_sector":null,"funding_amount_or_cap":null,"eligibility_rules":[],"evidence_spans":[]}}

Text: "Eligible firms may receive matching grants up to HKD 10 million for automation equipment upgrades."
JSON: {{"instrument_type":"grant","target_sector":"manufacturing","funding_amount_or_cap":"up to HKD 10 million","eligibility_rules":["eligible firms","automation equipment upgrades"],"evidence_spans":["matching grants up to HKD 10 million"]}}

Text: "Exports of dual-use advanced chips require an export license before shipment."
JSON: {{"instrument_type":"export_control","target_sector":"semiconductors","funding_amount_or_cap":null,"eligibility_rules":["export license required"],"evidence_spans":["require an export license"]}}
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
    timestamp = datetime.now().strftime("%Y%m%d")

    pdf_path = Path(f"pilot_with_pdf/data/pdf/hk_it_blueprint_{timestamp}.pdf")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    out_csv = Path(f"pilot_with_pdf/data/extract_naive/hk_it_blueprint_extraction_naive_{timestamp}.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)

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