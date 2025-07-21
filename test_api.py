#!/usr/bin/env python3
import requests
import json

# Test the analyze endpoint without authentication
url = "http://localhost:8000/api/v2/analyze"
data = {
    "log_content": "Test log entry",
    "application_name": "test-app",
    "enable_memory": False,
    "enable_enhanced_analysis": False
}

print("Testing /api/v2/analyze endpoint...")
response = requests.post(url, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}...")

# Test the streaming endpoint
stream_url = "http://localhost:8000/api/v2/analyze/stream"
print("\nTesting /api/v2/analyze/stream endpoint...")
response = requests.post(stream_url, json=data, stream=True)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    for line in response.iter_lines():
        if line:
            print(f"Stream: {line.decode()}")
            break
else:
    print(f"Response: {response.text}")