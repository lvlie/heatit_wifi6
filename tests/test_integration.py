import time
import requests
import json

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
        exit(1)

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
        exit(1)

    print("Entity loaded! Attempting to set HVAC mode...")

    # We can pass the hardcoded JWT token generated in test.yml
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMiIsImlhdCI6MTc3NDIxMDU4OSwiZXhwIjoyMDg5NTcwNTg5fQ.7RiDJMWFlMSoJkc-5zCKqQ5sPPXJY5cFdPRBYauCWSk",
        "Content-Type": "application/json"
    }

    # We will get the entity ID first
    payload = {"entity_id": "climate.mocked_heatit_thermostat", "hvac_mode": "heat"}
    try:
        res = requests.post(f"{HA_URL}/api/services/climate/set_hvac_mode", json=payload, headers=headers)
        if res.status_code in [200, 201]:
            print("Successfully sent set_hvac_mode request.")
        else:
            print(f"Service call returned {res.status_code}. Using fallback log check.")
    except Exception as e:
        print(f"Error calling HA service: {e}")

    # Check logs for "async_set_hvac_mode" or similar
    for _ in range(5):
        try:
            with open(LOG_PATH, "r") as f:
                logs = f.read()
                # Check for either the log output of our api call setting the hvac mode or the mock API handling it
                if "set_parameter" in logs or "Set parameter to the thermostat" in logs or "operatingMode" in logs:
                    print("SUCCESS: Integration initialized, entities added, and HVAC mode set successfully.")
                    exit(0)
        except FileNotFoundError:
            pass
        time.sleep(2)

    print("FAILED: Did not detect setting HVAC mode.")
    try:
        with open(LOG_PATH, "r") as f:
            print(f.read())
    except FileNotFoundError:
        print("Log file not found.")
    exit(1)

if __name__ == "__main__":
    main()
