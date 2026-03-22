import time
import requests

HA_URL = "http://localhost:8123"

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

    print("Checking for Heatit WiFi6 entities...")
    # Because trusted networks is enabled, we need to supply the right headers or just fetch it
    # But HA API normally requires a Bearer token.
    # Let's read from the REST API if we can, or we can use Home Assistant's websocket API
    # Since trusted networks is for the frontend, the REST API might still complain without a token.
    # To reliably test, we should pass a generated token or check the states via another means.
    # An easy way to check if it's loaded without a token is to grep the logs for "Heatit WiFi6".

    print("Checking Home Assistant logs for Heatit WiFi6 initialization...")
    # Let's just look at the home-assistant.log file
    log_path = "ha_config/home-assistant.log"
    for _ in range(15):
        try:
            with open(log_path, "r") as f:
                logs = f.read()
                if "Heatit WiFi6" in logs and "added to the list of entities" in logs:
                    print("SUCCESS: Integration initialized and entities added.")
                    exit(0)
                if "Error communicating with API" in logs:
                    print("FAILED: Error communicating with mock API.")
                    exit(1)
                if "Traceback" in logs and "heatit_wifi6" in logs:
                    print("FAILED: Python exception in component.")
                    exit(1)
        except FileNotFoundError:
            pass
        time.sleep(2)

    print("FAILED: Timeout waiting for entity initialization. Check the logs.")
    print("----- ha_config/home-assistant.log -----")
    try:
        with open(log_path, "r") as f:
            print(f.read())
    except FileNotFoundError:
        print("Log file not found.")
    exit(1)

if __name__ == "__main__":
    main()
