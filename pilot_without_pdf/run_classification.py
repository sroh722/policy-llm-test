#Example 1 — Classification pipeline (document → label)

import pandas as pd
from pilot_without_pdf.src.classify import classify_policy_text

# Example policy paragraphs (you can replace these later)
paragraphs = [
    "The Government provides matching funding up to HKD 15 million for smart production line upgrades.",
    "Applicants must be companies registered in Hong Kong.",
    "Exports of certain dual-use items require a license approval.",
    "Companies must meet 60% local content requirement to qualify for incentives."
]

rows = []

for i, paragraph in enumerate(paragraphs):
    print(f"Processing paragraph {i}...")
    
    result = classify_policy_text(paragraph)
    result["text"] = paragraph
    result["id"] = i
    
    rows.append(result)

df = pd.DataFrame(rows)

# Save results
df.to_csv("pilot_without_pdf/data/test_classification.csv", index=False)

print("\nFinal results:")
print(df)