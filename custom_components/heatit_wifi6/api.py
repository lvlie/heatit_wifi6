import aiohttp
import logging
import json
from .const import API_STATUS, API_PARAMETERS, API_RESET

_LOGGER = logging.getLogger(__name__)

# should an other side certificate verified when https used. (True/False)
# if certificate not verified, https works also with self signed certs.
TLS_CHECK = True

class HeatitWiFi6API:
    def __init__(self, host):
        self.__host = host.rstrip("/")

    async def _get(self, endpoint):  # simple general http-get
        url = f"{self.__host}{endpoint}"
        _LOGGER.debug("aiohttp - Get url: %s", url)

        try:
            async with aiohttp.TCPConnector(ssl=TLS_CHECK, resolver=aiohttp.resolver.ThreadedResolver()) as conn:
                async with aiohttp.ClientSession(connector=conn, trust_env=False) as session:
                    async with session.get(url, timeout=5) as response:
                        text = await response.text()
                        _LOGGER.debug(f"Response (get %s) data:\n%s", url, str(text))
                        return await self._parse_json(text)
        except Exception as e:
            _LOGGER.error("GET %s failed: %s", url, str(e))
            return {}


    async def _post(self, endpoint, data):  # simple general http-post
        url = f"{self.__host}{endpoint}"
        _LOGGER.debug("aiohttp - Post url: %s", url)

        try:
            async with aiohttp.TCPConnector(ssl=TLS_CHECK, resolver=aiohttp.resolver.ThreadedResolver()) as conn:
                async with aiohttp.ClientSession(connector=conn, trust_env=False) as session:
                    async with session.post(url, json=data, timeout=5) as response:
                        text = await response.text()
                        _LOGGER.debug(f"Response (post %s) data:\n%s", url, str(text))
                        return await self._parse_json(text)
        except Exception as e:
            _LOGGER.error("POST %s failed: %s", url, str(e))
            return {}


    async def _delete(self, endpoint):  # simple general http-delete
        url = f"{self.__host}{endpoint}"
        _LOGGER.debug("aiohttp - Delete url: %s", url)

        try:
            async with aiohttp.TCPConnector(ssl=TLS_CHECK, resolver=aiohttp.resolver.ThreadedResolver()) as conn:
                async with aiohttp.ClientSession(connector=conn, trust_env=False) as session:
                    async with session.delete(url, timeout=5) as response:
                        text = await response.text()
                        _LOGGER.debug(f"Response (delete %s) data:\n%s", url, str(text))
                        return await self._parse_json(text)
        except Exception as e:
            _LOGGER.error("DELETE %s failed: %s", url, str(e))
            return {}


    # aiohttp response.json() require a correct content-type header on the http response.
    # parse json from response.text() is immune of content-type header.
    async def _parse_json(self, text):
       if not isinstance(text, str): return {}  # non string?
       text = text.strip()
       if not bool(text) or not text.startswith("{") or not text.endswith("}"): return {}  # not empty string and look like a json string?
       try:
           data = json.loads(text)
       except json.JSONDecodeError as e:
           data = {}
           _LOGGER.error("Json parsing failed. %s ", str(e))
       return data


    async def get_device_id(self) -> str:
        _LOGGER.debug("get_device_id() - Fetch device_id from the API..")
        data = await self._get(API_STATUS.rstrip("/"))
        return data.get("id", "unknown")


    async def get_status(self) -> dict:
        _LOGGER.debug("get_status() - Fetch full status from the API..")
        return await self._get(API_STATUS.rstrip("/"))


    async def set_parameter(self, parameter, value) -> dict:
        _LOGGER.info("set_parameter(%s, %s) - Set parameter to the thermostat..", parameter, value)

        data = {parameter: value}
        response = await self._post(API_PARAMETERS.rstrip("/"), data)

        if response and response.get("status", "Failed") == "Success":
            _LOGGER.debug(f"set_parameter({parameter, value}): {response.get("value", "Success, but no value of response: %s")}", str(response))
            return response
        
        _LOGGER.error("set_parameter({parameter, value}): %s", str(response))
        return {}


    async def reset_device(self, reset_type="kwh") -> dict:
        _LOGGER.info("reset_device() - Resetting the Heatit thermostat. Reset type: %s", reset_type)

        if reset_type not in ["factory", "settings", "kwh"]:
            _LOGGER.error("Unknown reset_type: %s", reset_type)
            return { "status": "Failed", "detail": "Unknown reset_type." }
        
        response = await self._delete(f"{API_RESET.rstrip("/")}/{reset_type}")

        if response and response.get("status", "Failed") == "Success":
            _LOGGER.info(f"reset_device({reset_type}): {response.get("value", "Success, but no value of response. (?)")}")
            return response
        
        _LOGGER.error("reset_device({reset_type}): %s", str(response))
        return {}
