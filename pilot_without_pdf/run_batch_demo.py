from pilot_without_pdf.src.batch_config import SNIPPETS
from pilot_without_pdf.src.batch_pipeline import run_batch

if __name__ == "__main__":
    df = run_batch(SNIPPETS)
    print(df[["id", "instrument_type", "confidence", "target_sector", "funding_amount_or_cap"]])
    df.to_csv("pilot_without_pdf/data/batch_fewshot_output.csv", index=False)
    print("\nSaved: batch_fewshot_output.csv")