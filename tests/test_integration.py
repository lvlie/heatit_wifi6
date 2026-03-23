import time
import requests
import json
import logging
import sys

HA_URL = "http://localhost:8123"
LOG_PATH = "ha_config/home-assistant.log"

def main():
    print("Waiting for Home Assistant API to become ready...")
    # Polling until REST API is reachable
    for _ in range(30):
        try:
            res = requests.get(f"{HA_URL}/api/")
            if res.status_code in [200, 401]:
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
    else:
        print("Timeout waiting for HA API.")
        try:
            with open(LOG_PATH, "r") as f:
                print("----- ha_config/home-assistant.log -----")
                print(f.read())
        except FileNotFoundError:
            print("Log file not found.")
        sys.exit(1)

    print("Checking Home Assistant logs for Heatit WiFi6 initialization...")
    entity_loaded = False
    for _ in range(15):
        try:
            with open(LOG_PATH, "r") as f:
                logs = f.read()
                if "Heatit WiFi6" in logs and "added to the list of entities" in logs:
                    entity_loaded = True
                    break
        except FileNotFoundError:
            pass
        time.sleep(2)

    if not entity_loaded:
        print("FAILED: Entity did not load.")
        try:
            with open(LOG_PATH, "r") as f:
                print(f.read())
        except FileNotFoundError:
            print("Log file not found.")
        sys.exit(1)

    print("Entity loaded! Attempting to set HVAC mode...")

    # Because trusted networks is enabled for localhost, we shouldn't necessarily need a token.
    # But just in case, we will generate a valid one dynamically using PyJWT to avoid expiration issues.
    # The JWT token is created using the secret `0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef`
    # corresponding to the refresh token ID `22222222222222222222222222222222`.

    try:
        import jwt
        from datetime import datetime, timedelta, timezone

        # HA `jwt_wrapper.verify_and_decode` expects strictly integer timestamps
        now_ts = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "iss": "22222222222222222222222222222222",
            "iat": now_ts,
            "exp": now_ts + 3600 * 24 * 365
        }
        token = jwt.encode(payload, bytes.fromhex("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"), algorithm="HS256")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    except ImportError:
        # Fallback if jwt is not installed, though we pip installed PyJWT in workflow
        print("PyJWT not installed. Sending request without token (relying on trusted_networks)...")
        headers = {
            "Content-Type": "application/json"
        }

    # We will get the entity ID first by calling the states API
    entity_id = "climate.mocked_heatit_thermostat"
    try:
        res = requests.get(f"{HA_URL}/api/states", headers=headers)
        if res.status_code == 200:
            states = res.json()
            for state in states:
                if state["entity_id"].startswith("climate.") and "heatit" in state["entity_id"]:
                    entity_id = state["entity_id"]
                    print(f"Found climate entity: {entity_id}")
                    break
        else:
            print(f"Failed to fetch states, got {res.status_code}. Proceeding with fallback {entity_id}")
    except Exception as e:
        print(f"Error fetching states: {e}")

    payload = {"entity_id": entity_id, "hvac_mode": "heat"}
    try:
        res = requests.post(f"{HA_URL}/api/services/climate/set_hvac_mode", json=payload, headers=headers)
        if res.status_code in [200, 201]:
            print(f"Successfully sent set_hvac_mode request to {entity_id}.")
        else:
            print(f"Service call returned {res.status_code}. Checking logs anyway...")
            print(res.text)
    except Exception as e:
        print(f"Error calling HA service: {e}")

    # Check logs for "set_parameter" which confirms the API client was called
    for _ in range(10):
        try:
            with open(LOG_PATH, "r") as f:
                logs = f.read()
                # Check for the specific log output from our api call setting the hvac mode
                if "set_parameter(operatingMode" in logs or "Set parameter to the thermostat" in logs:
                    print("SUCCESS: Integration initialized, entities added, and HVAC mode set successfully.")
                    sys.exit(0)
        except FileNotFoundError:
            pass
        time.sleep(2)

    print("FAILED: Did not detect setting HVAC mode.")
    try:
        with open(LOG_PATH, "r") as f:
            print(f.read())
    except FileNotFoundError:
        print("Log file not found.")
    sys.exit(1)

if __name__ == "__main__":
    main()
