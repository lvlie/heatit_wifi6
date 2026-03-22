#!/bin/bash
mkdir -p ha_config_test/custom_components
cp -r custom_components/heatit_wifi6 ha_config_test/custom_components/
cat << 'CONF' > ha_config_test/configuration.yaml
default_config:
logger:
  default: info
  logs:
    custom_components.heatit_wifi6: debug
CONF

# Start HA
docker run -d \
  --name ha_test_local \
  --network host \
  -v $(pwd)/ha_config_test:/config \
  ghcr.io/home-assistant/home-assistant:stable

sleep 30
docker logs ha_test_local
cat ha_config_test/home-assistant.log
docker stop ha_test_local
docker rm ha_test_local
