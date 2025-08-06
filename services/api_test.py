import sys
import os
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import TEST_MODE
from services import api_client

def main():
    print(f"TEST_MODE = {TEST_MODE}")
    attractions = api_client.fetch_attractions()
    print("Fetched attractions:")
    for a in attractions:
        print(f"- {a['name']} ({a['wait_time']} min)")


# Replace with your real credentials or move to env vars
USERNAME = "cat@dog.com"        # will be device uid@example.com
PASSWORD = "catdog"             # will be device uid
API_ROOT = "https://lqrpus.api.nextgen.dev.lo-q.com/v2"

auth_token = None  # Cache token during runtime

def login():
    global auth_token
    if TEST_MODE:
        print("[TEST] Skipping real login")
        return

    r = requests.post(
        f"{API_ROOT}/root/actions/signin.password",
        json={
            "username": USERNAME,
            "password": PASSWORD,
            "terms_and_conditions": True
        }
    )

    r.raise_for_status()
    auth_token = r.json()["storedResponseData"]["authCode"]
    print("[API] Login successful. Token acquired.")


def fetch_attractions():
    if TEST_MODE:
        print("[TEST] Returning mock attractions")
        return [
            {"id": "mock1", "name": "Mock Coaster", "wait_time": 5},
            {"id": "mock2", "name": "Mock Flume", "wait_time": 12}
        ]

    if auth_token is None:
        login()

    headers = {"Authorization": f"Bearer {auth_token}"}
    r = requests.get(f"{API_ROOT}/attractions", headers=headers)
    r.raise_for_status()
    response = r.json() 

    raw_items = r.json()["items"]
    parsed = [
        {
            "id": item["data"]["id"],
            "name": item["data"]["name"],
            "wait_time": item["data"].get("wait_time_mins", 0)
        }
        for item in raw_items
    ]

    return parsed

if __name__ == "__main__":
    main()