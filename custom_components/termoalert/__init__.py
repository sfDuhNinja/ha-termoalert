"""TermoAlert București: hot water and heating outages from CMTEB."""
from datetime import timedelta
import logging

import aiohttp

from homeassistant.const import Platform
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .parser import URL, parse

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BINARY_SENSOR]
# cmteb.ro answers 403 to the default aiohttp/HomeAssistant user agent
HEADERS = {"User-Agent": "Mozilla/5.0 (Home Assistant; termoalert)"}
# ponytail: after a restart, sensors keep their restored state until this long after HA has
# started, so automations are attached in time to see an outage that ended during the restart
STARTUP_DELAY = 60


class CMTEBCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, _LOGGER, name="termoalert", config_entry=entry,
                         update_interval=timedelta(minutes=10))
        self.last_success = None

    async def _async_update_data(self):
        try:
            resp = await async_get_clientsession(self.hass).get(
                URL, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30))
            resp.raise_for_status()
            data = parse(await resp.text())
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Nu pot citi avariile CMTEB: {err}") from err
        self.last_success = dt_util.now().isoformat()
        return data


async def async_setup_entry(hass, entry):
    coordinator = entry.runtime_data = CMTEBCoordinator(hass, entry)
    if hass.is_running:
        await coordinator.async_refresh()
    else:
        @callback
        def _refresh(_now):
            entry.async_create_background_task(hass, coordinator.async_refresh(), "termoalert_refresh")

        @callback
        def _started(_hass):
            entry.async_on_unload(async_call_later(hass, STARTUP_DELAY, _refresh))

        entry.async_on_unload(async_at_started(hass, _started))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
