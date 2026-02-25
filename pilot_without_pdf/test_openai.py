from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

r = client.responses.create(
    model="gpt-4.1-mini",
    input="Give me 3 examples of industrial policy instruments."
)

print(r.output_text)