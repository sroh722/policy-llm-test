import json
import time
import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI

from src.batch_config import MODEL
from src.batch_prompt import FEWSHOT_BLOCK

load_dotenv()
client = OpenAI()

def call_llm_extract(text: str) -> dict:
    prompt = FEWSHOT_BLOCK + f"\n\nNow process this text:\nText: {text}\nJSON:"
    r = client.responses.create(
        model=MODEL,
        input=prompt,
    )
    return json.loads(r.output_text)

def run_batch(snippets: list[str], sleep_seconds: float = 0.3) -> pd.DataFrame:
    rows = []
    for i, s in enumerate(tqdm(snippets, desc="Batch extracting")):
        try:
            out = call_llm_extract(s)
            out["id"] = i
            out["text"] = s
            rows.append(out)
        except Exception as e:
            rows.append({"id": i, "text": s, "error": str(e)})
            time.sleep(sleep_seconds)
    return pd.DataFrame(rows)