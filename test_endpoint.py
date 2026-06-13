import requests
import sys

url = "https://api.neo4j.io/v2beta1/organizations/d3c8d600-b9a0-4429-9865-11d039f017fb/projects/d3c8d600-b9a0-4429-9865-11d039f017fb/agents/31e5e5b7-3485-40d2-bbdf-85d629a263e3/invoke"

print("Testing with payload: {\"messages\": [{\"role\": \"user\", \"content\": \"hello\"}]}")
response = requests.post(
    url, 
    json={"messages": [{"role": "user", "content": "hello"}]},
    headers={"Content-Type": "application/json"}
)

print(f"Status Code: {response.status_code}")
print(f"Response Body: {response.text}")

print("\n---")
print("Testing with payload: {\"input\": \"hello\"}")
response2 = requests.post(
    url, 
    json={"input": "hello"},
    headers={"Content-Type": "application/json"}
)

print(f"Status Code: {response2.status_code}")
print(f"Response Body: {response2.text}")
