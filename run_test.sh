#!/bin/bash
npx -y @stoplight/prism-cli mock custom_components/heatit_wifi6/docs/Heatit_WiFi6_OpenAPI_v70.yaml -p 4010 &
PRISM_PID=$!
sleep 5

# Set up Home Assistant Config
mkdir -p ha_config/custom_components
cp -r custom_components/heatit_wifi6 ha_config/custom_components/
cat << 'CONF' > ha_config/configuration.yaml
default_config:
logger:
  default: info
  logs:
    custom_components.heatit_wifi6: debug
CONF

# Create an empty core.config_entries to inject our mock setup
mkdir -p ha_config/.storage
cat << 'ENTRIES' > ha_config/.storage/core.config_entries
{
  "version": 1,
  "minor_version": 4,
  "key": "core.config_entries",
  "data": {
    "entries": [
      {
        "entry_id": "e0b8a1c9d4f211ee9c270242ac120002",
        "version": 1,
        "minor_version": 1,
        "domain": "heatit_wifi6",
        "title": "Mocked Heatit Thermostat",
        "data": {
          "host": "http://127.0.0.1:4010"
        },
        "options": {},
        "pref_disable_new_entities": false,
        "pref_disable_polling": false,
        "source": "user",
        "unique_id": null,
        "disabled_by": null
      }
    ]
  }
}
ENTRIES

cat << 'AUTH' > ha_config/.storage/auth
{
  "version": 1,
  "minor_version": 1,
  "key": "auth",
  "data": {
    "users": [
      {
        "id": "11111111111111111111111111111111",
        "is_owner": true,
        "is_active": true,
        "name": "testuser",
        "system_generated": false,
        "credentials": []
      }
    ],
    "groups": [
      {
        "id": "system-admin",
        "name": "Administrators"
      }
    ],
    "refresh_tokens": [
      {
        "id": "22222222222222222222222222222222",
        "user_id": "11111111111111111111111111111111",
        "client_id": null,
        "client_name": "Long-Lived Access Token",
        "client_icon": null,
        "token_type": "long_lived_access_token",
        "created_at": "2024-01-01T00:00:00.000000+00:00",
        "last_used_at": null,
        "last_used_ip": null,
        "jwt_key": "dummy_key_for_testing_12345"
      }
    ]
  }
}
AUTH

# To use the long lived access token we must generate a JWT from it.
# We can also just configure trusted networks so we don't need a token at all.
cat << 'TRUSTED' >> ha_config/configuration.yaml
homeassistant:
  auth_providers:
    - type: trusted_networks
      trusted_networks:
        - 127.0.0.1
        - ::1
        - 172.0.0.0/8
        - 192.168.0.0/16
        - 10.0.0.0/8
      allow_bypass_login: true
TRUSTED

# Start HA
docker run -d \
  --name homeassistant \
  --network host \
  -v $(pwd)/ha_config:/config \
  ghcr.io/home-assistant/home-assistant:stable

echo "Waiting for Home Assistant to start..."
# Wait up to 60s for HA to be responsive
for i in {1..12}; do
  if curl -s http://localhost:8123/api/ > /dev/null; then
    echo "Home Assistant is up!"
    break
  fi
  sleep 5
done

python3 tests/test_integration.py
docker stop homeassistant
docker rm homeassistant
kill $PRISM_PID
