from datetime import datetime, timedelta
import logging

import aiohttp

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .parser import URL, find, parse

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=10)
# cmteb.ro answers 403 to the default aiohttp/HomeAssistant user agent
HEADERS = {"User-Agent": "Mozilla/5.0 (Home Assistant; termoalert)"}
TZ = dt_util.get_time_zone("Europe/Bucharest")


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([HotWaterOutage(entry)], True)


def _eta(s):
    try:
        return datetime.strptime(s, "%d.%m.%Y %H:%M").replace(tzinfo=TZ).isoformat()
    except ValueError:
        return s or None


class HotWaterOutage(BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:water-boiler-alert"
    _attr_has_entity_name = True
    _attr_translation_key = "hot_water"
    _attr_attribution = "Date: CMTEB / TermoAlert"

    def __init__(self, entry):
        self._strada = entry.data["strada"]
        self._bloc = entry.data.get("bloc")
        self._attr_unique_id = entry.unique_id
        self._attr_device_info = {"identifiers": {("termoalert", entry.entry_id)}, "name": entry.title,
                                  "manufacturer": "CMTEB", "model": "TermoAlert", "entry_type": DeviceEntryType.SERVICE}

    async def async_update(self):
        try:
            resp = await async_get_clientsession(self.hass).get(
                URL, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30))
            resp.raise_for_status()
            rows = find(parse(await resp.text()), self._strada, self._bloc)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            if self._attr_available:
                _LOGGER.warning("Nu pot citi avariile CMTEB: %s", err)
            self._attr_available = False
            return
        self._attr_available = True
        acc = [r for r in rows if "ACC" in r["agent"]]
        self._attr_is_on = bool(acc)
        r = acc[0] if acc else None
        self._attr_extra_state_attributes = {
            "tip": r and r["agent"],
            "motiv": r and r["motiv"],
            "estimare_remediere": r and _eta(r["estimare"]),
            "punct_termic": r and r["punct_termic"],
            # heating-only outages on the same address, for info
            "alte_avarii": [f'{x["agent"]}: {x["motiv"]} (estimare {x["estimare"]})' for x in rows if x not in acc],
        }
