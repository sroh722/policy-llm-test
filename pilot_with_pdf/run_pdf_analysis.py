import re
import json
import time
import requests
import pdfplumber
from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
from datetime import datetime
from collections import Counter

# =========================
# Config
# =========================

PDF_URL = "https://www.itib.gov.hk/en/publications/I%26T%20Blueprint%20Book_EN_single_Digital.pdf"
MODEL = "gpt-4.1-mini"

SKIP_FIRST_PAGES = 8
MAX_PAGES_AFTER_SKIP = 15
CHUNK_MAX_CHARS = 3500
CHUNK_OVERLAP = 300

KEYWORD_SCAN = [
    "grant", "fund", "funding", "scheme",
    "subsidy", "loan", "tax", "incentive",
    "standard", "procurement", "regulation",
    "eligible", "million", "HK$"
]

# =========================
# Setup
# =========================

load_dotenv()
client = OpenAI()

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
timestamp_ymd = datetime.now().strftime("%Y%m%d")

BASE_DIR = Path("pilot_with_pdf")
PDF_PATH = BASE_DIR / "data" / "pdf" / f"hk_it_blueprint_{timestamp_ymd}.pdf"
PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
OUT_DIR = BASE_DIR / "data" / "raw"

# =========================
# Utility functions
# =========================

def download_pdf(url: str, out_path: Path):
    headers = {"User-Agent": "Mozilla/5.0"}
    with requests.get(url, headers=headers, stream=True, timeout=60) as r:
        r.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def pdf_to_text_limited(path: Path, skip_first: int, max_pages: int) -> str:
    pages = []
    with pdfplumber.open(path) as pdf:
        total_pages = len(pdf.pages)
        start = skip_first
        end = min(skip_first + max_pages, total_pages)

        print(f"Total pages in PDF: {total_pages}")
        print(f"Using pages {start} to {end - 1}")

        for i in range(start, end):
            text = pdf.pages[i].extract_text() or ""
            pages.append(text)

    return "\n".join(pages)


def chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + max_chars])
        i += max_chars - overlap
    return chunks


def call_llm_json(prompt: str, max_output_tokens: int = 600):
    for attempt in range(3):
        try:
            r = client.responses.create(
                model=MODEL,
                input=prompt,
                temperature=0,
                max_output_tokens=max_output_tokens,
            )
            raw = r.output_text
            break
        except Exception:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise

    clean = raw.strip()
    clean = re.sub(r"^```(?:json)?\s*", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean)

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON", "raw_output": clean[:1500]}


# =========================
# Step 1: Basic PDF Diagnostics (No AI)
# =========================

def keyword_scan(text: str):
    text_lower = text.lower()
    counts = Counter()

    for kw in KEYWORD_SCAN:
        counts[kw] = text_lower.count(kw.lower())

    print("\nKeyword frequency scan:")
    for k, v in counts.items():
        print(f"{k}: {v}")

    return counts


# =========================
# Step 2: Document Typology
# =========================

def analyze_document(text: str):
    sample = text[:7000]

    prompt = f"""
You are helping build a dataset from a government PDF.

Return ONLY JSON with:
- doc_type
- instrument_density
- extraction_feasibility
- likely_instrument_types
- recommended_next_step
- notes

Be conservative and analytical.
No policy advice.

TEXT:
{sample}
"""
    return call_llm_json(prompt, max_output_tokens=500)


# =========================
# Step 3: Taxonomy Proposal
# =========================

def propose_taxonomy(chunks: list[str], k: int = 4):
    sample_chunks = chunks[:k]
    joined = "\n\n".join(sample_chunks)

    prompt = f"""
Based on the text below:

1) Propose a taxonomy (8-12 categories) for coding industrial policy instruments.
2) Provide short definitions.
3) Suggest minimal extraction schema fields.
4) Provide 5 coding decision rules.

Return ONLY JSON.

TEXT:
{joined}
"""
    return call_llm_json(prompt, max_output_tokens=800)


# =========================
# Main
# =========================

def main():

    print("Downloading PDF...")
    download_pdf(PDF_URL, PDF_PATH)

    print("Extracting text...")
    text = pdf_to_text_limited(PDF_PATH, SKIP_FIRST_PAGES, MAX_PAGES_AFTER_SKIP)

    print(f"\nExtracted text length: {len(text)} characters")

    # Step 1: Cheap diagnostics
    keyword_scan(text)

    chunks = chunk_text(text, CHUNK_MAX_CHARS, CHUNK_OVERLAP)
    print(f"\nNumber of chunks: {len(chunks)}")

    # Step 2: AI Document Analysis
    print("\n==============================")
    print("STEP 2: DOCUMENT ANALYSIS")
    print("==============================")
    analysis = analyze_document(text)
    print(json.dumps(analysis, indent=2))

    # ✅ Save analysis (optional but useful)
    analysis_path = OUT_DIR / f"doc_analysis_{timestamp}.json"
    analysis_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(f"\nSaved analysis to: {analysis_path.resolve()}")

    # Step 3: AI Taxonomy Proposal
    print("\n==============================")
    print("STEP 3: TAXONOMY PROPOSAL")
    print("==============================")
    taxonomy = propose_taxonomy(chunks)
    print(json.dumps(taxonomy, indent=2))

    # ✅ Save taxonomy
    taxonomy_path = OUT_DIR / f"taxonomy_plan_{timestamp}.json"
    taxonomy_path_recent = OUT_DIR / f"taxonomy_plan_recent.json"
    taxonomy_path.write_text(json.dumps(taxonomy, indent=2), encoding="utf-8")
    taxonomy_path_recent.write_text(json.dumps(taxonomy, indent=2), encoding="utf-8")
    print(f"\nSaved taxonomy to: {taxonomy_path.resolve()}")

    print("\nDone.")


if __name__ == "__main__":
    main()