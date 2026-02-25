import pandas as pd

pd.set_option("display.max_colwidth", None)
pd.set_option("display.max_columns", None)

df = pd.read_csv("data/test_extraction.csv")
print(df)