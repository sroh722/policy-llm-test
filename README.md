# LLM-assisted Industrial Policy PDF Pipeline (Hong Kong Demo)

This repository is an experimental environment for designing robust, reproducible LLM pipelines for industrial policy research. You **do need** an OpenAI account and an **API key** to run.

The project demonstrates a staged approach to:

- Downloading and parsing official policy PDFs (The example is based on a single file)
- Performing document-level analysis (typology and feasibility)  
- Generating a thematic taxonomy using LLM guidance  
- Running structured extraction using a frozen taxonomy  

It emphasizes:
- Modular pipeline design
- Taxonomy stabilization
- Separation between analysis and extraction
- Reproducibility and cost control

---

## 📂 Repository Structure

```
.
├── pilot_with_pdf/
│   ├── run_pdf_analysis.py                # Document analysis + taxonomy proposal
│   ├── run_pdf_extract_naive.py           # Naive extraction baseline (no analysis/taxonomy)
│   ├── run_pdf_extract_after_analysis.py  # Extraction using taxonomy from analysis
│   └── data/
│       ├── pdf/              # Downloaded PDFs
│       ├── raw/              # JSON outputs (doc analysis, taxonomy plan)
│       ├── extract_naive/    # Outputs from naive extraction
│       └── extract_analysis/ # Outputs from extraction after analysis
│
├── pilot_without_pdf/
│   ├── run_batch_demo.py
│   ├── run_classification.py
│   ├── run_extraction.py
│   ├── check_outputs.py
│   ├── test_openai.py
│   ├── src/                  # Reusable modules (prompts, pipeline, classify, extract)
│   └── data/                 # CSV outputs for toy examples
│
└── requirements.txt
```

---

## 📦 Note on `data_saved/` folder: Snapshot at Initial Publication

The `data_saved/` folder contains output files (JSON and CSV) that were generated when this repository was first published.

Purpose:
- Provide a reproducible snapshot of results
- Allow users to inspect outputs without running the full pipeline
- Preserve taxonomy and extraction outputs used at initial release

Important notes:
- Files in `data_saved/` are static and not automatically updated.
- Running the pipeline again may produce slightly different outputs due to LLM stochasticity.
- The authoritative workflow remains the scripts under `pilot_with_pdf/`.

If you wish to regenerate outputs, run the scripts directly.

---

## ⚙️ Setup

### 1. Create and activate a virtual environment (Mac/Linux)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add OpenAI API key

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_key_here
```

⚠️ When you share, do **not** commit `.env`. Add it to `.gitignore`.

Recommended `.gitignore` entries:

```
.env
.venv/
__pycache__/
*.pyc
```

---

## 🚀 How to Run

### A) Toy Workflow (No PDF)

Test API connection:

```bash
python pilot_without_pdf/test_openai.py
```

Run classification and extraction demos:

```bash
python pilot_without_pdf/run_classification.py
python pilot_without_pdf/run_extraction.py
python pilot_without_pdf/run_batch_demo.py
```

Outputs are written to:

```
pilot_without_pdf/data/
```

---

### B) Real PDF Workflow (Hong Kong Blueprint)

#### Step 1: Run PDF Analysis (Document Typology + Taxonomy Proposal)

```bash
python pilot_with_pdf/run_pdf_analysis.py
```

Outputs:

- `pilot_with_pdf/data/raw/doc_analysis_*.json`
- `pilot_with_pdf/data/raw/taxonomy_plan_*.json`
- (will be used in Step 2) `taxonomy_plan_recent.json`

This stage:
- Classifies document type
- Estimates instrument density
- Proposes a thematic taxonomy
- Suggests extraction schema

---

#### Step 2: Run Naive Extraction Baseline

```bash
python pilot_with_pdf/run_pdf_extract_naive.py
```

Outputs:

```
pilot_with_pdf/data/extract_naive/
```

---

#### Step 3: Run Extraction Using Designed Taxonomy

```bash
python pilot_with_pdf/run_pdf_extract_after_analysis.py
```

Outputs:

```
pilot_with_pdf/data/extract_analysis/
```

This stage:
- Loads frozen taxonomy
- Detects policy initiatives
- Assigns thematic category
- Extracts structured attributes

---

## 🧠 Methodology

This project uses a staged LLM-assisted design:

### 1. Document Typology & Feasibility
- Classify document type (strategic vs operational)
- Estimate instrument density
- Determine whether extraction is viable

### 2. Taxonomy Design
- Generate thematic coding scheme
- Suggest structured schema fields
- Define decision rules to reduce hallucination

### 3. Structured Extraction
- Detect policy initiatives
- Assign thematic categories
- Extract structured fields
- Export to CSV

---

## 📌 Important Notes

- Strategic blueprint documents typically contain high-level initiatives rather than granular instrument details.
- Funding scheme guides or regulatory documents yield richer structured data.
- Taxonomy should be reviewed and frozen before running full extraction.
- Token usage is controlled by:
  - Skipping cover pages
  - Limiting page range
  - Limiting chunk size
  - Capping output tokens
---

## 🔐 API & Billing

OpenAI API usage is billed per token (input + output).

To reduce cost:

- Limit number of pages processed
- Reduce chunk size
- Use conservative prompts
- Cap `max_output_tokens`

---

## 🤖 AI Assistance

Portions of this project were developed with assistance from large language models (e.g., OpenAI ChatGPT and GitHub Copilot).

AI tools were used to:
- Draft and refine code structure
- Suggest prompt formulations
- Assist in debugging and refactoring
- Generate initial documentation drafts

All design decisions, model configuration choices, taxonomy validation, and methodological structure were reviewed and curated by the author.