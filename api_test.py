import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("OPENROUTER_API_KEY")

response = requests.get(
    url="https://openrouter.ai/api/v1/key",
    headers={"Authorization": f"Bearer {API_KEY}"}
)

if response.status_code == 200:
    data = response.json()['data']
    print(f"Label: {data['label']}")
    print(f"Usage (All time): ${data['usage']}")
    print(f"Credits Remaining: ${data['limit_remaining']}")
else:
    print("Error fetching key info")