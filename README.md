The Heatit WiFi6 integration for Home Assistant.

This integration supports Heatit WiFi6 thermostat. 
The same device is branded also many other marketing names in many countries.
In Finland, this device is sold under names "Heatit WiFi6" and "Älytermostaatti Pistesarjat WiFi6". Maybe also others.

# Disclaimer
You may use this software at your own risk "as is" without any warranty from anyone.
This software was made by 3rd party. The device manufacturer ("Heatit") has no any involvement or responsibility for usage of this integration.

# Supported Devices
* Heatit WiFi6 - Firmware v2.20

# Installation
* Initially, the thermostat must be configured correctly and connected to your wifi network using the manufacturer's Heatit mobile app.
* Go in HACS, click on Integrations, click on the three little dots at top of the screen and selection "custom repositories", add this github url, select   "Integration" as repository, and click ADD. Then go to the Integrations tab of HACS, and install the "HeatIT WiFi Thermostat" integration.
* Restart Home Assistant.
* Be sure, that the thermostat is online and connected to your wifi, before trying to add it into HA.
* Goto Home Assistant -> Settings -> Devices & Services -> Add Integration
* Select from list "Heatit WiFi6 Thermostat"
* Give some descriptive name for your thermostat
* Enter the base url to your device. The correct ip-address what your thermostat has. E.g. http://192.168.3.20
* Accept / submit entered values and that's it.
* Check the added thermostat visibility on HA dashboard and enjoy.

# Statuses and communication
* Status and parameter values of thermostat are updated a once per minute.
* All thermostat's statuses and parameter values are exposed as device attributes on HA.
* Any parameter value can changed by direct http-post request to the thermostat device by Node-Red or what ever method.
    Http-path to change parameter: /api/parameters
    Post request body should contain json: { "parameterName": "newValue" }  where string values are with quotes and numeric values w/o quotes.
    The manufacturer's OpenAPI document is in the docs folder, where you can found all parameters and their possible values.
    Be careful, especially with configuration parameters.
* The kWh meter on thermostat device can reset to zero using an http request using delete method direct to the device path: /api/reset/kwh

## Version History

* 0.9.4
    * The current temperature is now based on the **sensorMode** configured on the device. 
      Temperature source can be floor, internal or external sensor.
* 0.9.3
    * Initial Release

## License
This software is licensed under MIT License.
