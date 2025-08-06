import os
import sys
import requests

from kiosk_py.config import MOCK_API, API_ROOT

# Configuration
USERNAME = "cat@dog.com"
PASSWORD = "catdog"

# Token cache
auth_token = None
current_user = None

def login(email=None, password=None):
    global auth_token, current_user

    if MOCK_API and (email is None or password is None):
        email = USERNAME
        password = PASSWORD
        print(f"[TEST] Skipping real login for {email}")
        current_user = email
        return "MOCK_DEVICE_ID"

    email = email or USERNAME
    password = password or PASSWORD

    # Step 1: Submit email to get action_invocation_id
    email_payload = {"username": email}
    email_response = requests.post(
        f"{API_ROOT}/root/actions/signin.password",
        json=email_payload
    )
    email_response.raise_for_status()
    email_data = email_response.json()

    action = email_data.get("action", {})
    href = action.get("href")
    result_code = action.get("data", {}).get("resultCode")
    action_type = action.get("type")

    print(f"[DEBUG] Received action type: {action_type}, resultCode: {result_code}")
    print(f"[DEBUG] Href: {href}")

    if not href or "action_invocation_id=" not in href:
        raise ValueError("Login step 1 failed: missing or invalid action_invocation_id")

    if action_type == "forgot_password":
        raise ValueError("Email already registered. Use password recovery or login flow.")

    if action_type != "signin.password":
        raise ValueError(f"Unexpected action type: {action_type}")

    # Step 2: Determine payload based on resultCode
    if result_code == "registration":
        password_payload = {
            "password": password,
            "terms_and_conditions": True
        }
        print(f"[DEBUG] Registering new user: {email}")
    else:
        password_payload = {
            "password": password
        }
        print(f"[DEBUG] Logging in existing user: {email}")

    # Step 3: Submit password
    password_response = requests.post(href, json=password_payload)
    password_response.raise_for_status()
    password_data = password_response.json()

    if "storedResponseData" not in password_data:
        raise ValueError("Login step 2 failed: missing authCode")

    auth_token = password_data["storedResponseData"]["authCode"]
    current_user = email

    if result_code == "registration":
        print(f"[API] Account created and logged in for {email}.")
    else:
        print(f"[API] Login successful for {email}. Token acquired.")

    return auth_token


def get_token(email=None, password=None):
    global auth_token, current_user

    if MOCK_API:
        return "mock-token"

    if auth_token is None or (email and email != current_user):
        login(email, password)

    return auth_token

def fetch_attractions():
    if MOCK_API:
        print("[TEST] Returning mock attractions")
        return [
            {"id": "mock1", "name": "Mock Coaster", "wait_time": 5},
            {"id": "mock2", "name": "Mock Flume", "wait_time": 12}
        ]

    headers = {"Authorization": f"Bearer {get_token()}"}
    response = requests.get(f"{API_ROOT}/attractions", headers=headers)
    response.raise_for_status()

    raw_items = response.json()["items"]
    return [
        {
            "id": item["data"]["id"],
            "name": item["data"]["name"],
            "wait_time": int(item["data"].get("wait_time_mins", 0)),
            "image": item["data"]["images"].get("qng_attraction_banner", [{}])[0].get("href")
        }
        for item in raw_items
    ]

def fetch_attraction_details(attraction_id):
    if MOCK_API:
        print(f"[TEST] Returning mock details for {attraction_id}")
        return {
            "data": {"id": attraction_id, "name": "Mock Ride"},
            "actions": [
                {
                    "type": "reserve",
                    "href": "https://mock.api/reserve",
                    "method": "post"
                }
            ]
        }

    headers = {"Authorization": f"Bearer {get_token()}"}
    response = requests.get(f"{API_ROOT}/attractions/{attraction_id}", headers=headers)
    response.raise_for_status()
    return response.json()

def make_reservation(device_id, attraction_id, guest_count=1):
    if MOCK_API:
        print(f"[TEST] Simulating reservation for ride ID: {attraction_id}")
        return {
            "ride_id": attraction_id,
            "wait_time": 15,
            "confirmation_id": "MOCK-RESERVATION-001"
        }

    headers = {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json"
    }

    # Step 1: Fetch attraction details
    detail_url = f"{API_ROOT}/attractions/{attraction_id}"
    response = requests.get(detail_url, headers=headers)
    response.raise_for_status()
    data = response.json()

    # Step 2: Find the reserve action
    reserve_action = next(
        (action for action in data.get("actions", []) if action["type"] == "reserve"),
        None
    )
    if not reserve_action:
        raise Exception("No reservation action available.")

    reserve_url = reserve_action["href"]
    method = reserve_action["method"].lower()

    # Step 3: Make the initial reservation attempt
    if method == "post":
        payload = {"guest_count": guest_count}
        reserve_response = requests.post(reserve_url, json=payload, headers=headers)
        reserve_response.raise_for_status()
        reserve_data = reserve_response.json()

        # Step 4: Check for follow-up confirmation action
        follow_up_action = reserve_data.get("action")
        if follow_up_action and follow_up_action.get("href"):
            confirm_url = follow_up_action["href"]
            print("[INFO] Confirming replacement of existing reservation...")
            confirm_response = requests.post(confirm_url, headers=headers)
            confirm_response.raise_for_status()
            return confirm_response.json()

        # No follow-up needed, return reservation result
        return reserve_data

    else:
        raise Exception(f"Unsupported reservation method: {method}")


if __name__ == "__main__":
    main()
