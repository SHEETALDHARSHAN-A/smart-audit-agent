import requests
import sys
import os

def test_ingest_api(file_path, url="http://127.0.0.1:8000/ingest"):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    print(f"Sending {file_path} to {url}...")
    try:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            print("Success!")
            print("Response JSON:")
            import json
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"Failed with status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_ingest_api(sys.argv[1])
    else:
        test_ingest_api("sample_invoice.png")
