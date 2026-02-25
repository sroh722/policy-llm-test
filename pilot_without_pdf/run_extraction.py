# Example 2 — Structured extraction (text → dataset row)
import pandas as pd
from pilot_without_pdf.src.extract import extract_instrument_fields

# Example real-style policy text
paragraphs = [
    """
    Re-industrialisation Funding Scheme: The Government provides matching funding.
    Each approved project may receive funding up to HKD 15 million.
    Applicants must be companies registered in Hong Kong.
    """,

    """
    Exports of advanced semiconductor equipment require prior license approval
    from the relevant authority.
    """
]

rows = []

for i, text in enumerate(paragraphs):
    print(f"Processing paragraph {i}...")
    result = extract_instrument_fields(text)
    result["text"] = text
    result["id"] = i
    rows.append(result)


pd.set_option("display.max_colwidth", None)
pd.set_option("display.max_columns", None)

df = pd.DataFrame(rows)

df.to_csv("pilot_without_pdf/data/test_extraction.csv", index=False)

print("\nFinal output:")
print(df)