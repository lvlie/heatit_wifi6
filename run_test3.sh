#!/bin/bash
npx -y @stoplight/prism-cli mock custom_components/heatit_wifi6/docs/Heatit_WiFi6_OpenAPI_v70.yaml -p 4010 &
PRISM_PID=$!
sleep 5
mkdir -p ha_config3/custom_components
cp -r custom_components/heatit_wifi6 ha_config3/custom_components/
cat << 'CONF' > ha_config3/configuration.yaml
default_config:
logger:
  default: info
  logs:
    custom_components.heatit_wifi6: debug
CONF
mkdir -p ha_config3/.storage
cat << 'ENTRIES' > ha_config3/.storage/core.config_entries
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

cat << 'AUTH' > ha_config3/.storage/auth
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
        "jwt_key": "dummy_key_for_testing_12345678901234567890"
      }
    ]
  }
}
AUTH

cat << 'TRUSTED' >> ha_config3/configuration.yaml
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

docker run -d --name homeassistant3 --network host -v $(pwd)/ha_config3:/config ghcr.io/home-assistant/home-assistant:stable
python3 tests/test_integration.py
docker stop homeassistant3
docker rm homeassistant3
kill $PRISM_PID
