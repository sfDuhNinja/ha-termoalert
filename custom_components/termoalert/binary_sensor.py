from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .parser import find

TZ = dt_util.get_time_zone("Europe/Bucharest")
# translation key -> (CMTEB code, icon)
KINDS = {"hot_water": ("ACC", "mdi:water-boiler-alert"), "heating": ("INC", "mdi:radiator-off")}
ATTRS = ("tip", "motiv", "estimare_remediere", "punct_termic", "alte_avarii", "ultima_citire")


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(Outage(entry.runtime_data, entry, kind) for kind in KINDS)


def _eta(s):
    try:
        return datetime.strptime(s, "%d.%m.%Y %H:%M").replace(tzinfo=TZ).isoformat()
    except ValueError:
        return s or None


class Outage(CoordinatorEntity, RestoreEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_has_entity_name = True
    _attr_attribution = "Date: CMTEB / TermoAlert"

    def __init__(self, coordinator, entry, kind):
        super().__init__(coordinator)
        self._entry = entry
        self._code, self._attr_icon = KINDS[kind]
        self._attr_translation_key = kind
        # hot water keeps the pre-1.1 unique id so existing entity ids survive the upgrade
        self._attr_unique_id = entry.unique_id if kind == "hot_water" else f"{entry.unique_id}|inc"
        self._attr_device_info = {"identifiers": {("termoalert", entry.entry_id)}, "name": entry.title,
                                  "manufacturer": "CMTEB", "model": "TermoAlert",
                                  "entry_type": DeviceEntryType.SERVICE}

    @property
    def available(self):
        # a failed fetch keeps the last known state instead of going unavailable
        return self._attr_is_on is not None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self.coordinator.data is not None:
            self._from_data()
        elif (last := await self.async_get_last_state()) and last.state in ("on", "off"):
            self._attr_is_on = last.state == "on"
            self._attr_extra_state_attributes = {k: last.attributes.get(k) for k in ATTRS}

    @callback
    def _handle_coordinator_update(self):
        if self.coordinator.data is not None:
            self._from_data()
        super()._handle_coordinator_update()

    def _from_data(self):
        rows = find(self.coordinator.data, self._entry.data["strada"], self._entry.data.get("bloc"))
        mine = [r for r in rows if self._code in r["agent"]]
        self._attr_is_on = bool(mine)
        r = mine[0] if mine else None
        self._attr_extra_state_attributes = {
            "tip": r and r["agent"],
            "motiv": r and r["motiv"],
            "estimare_remediere": r and _eta(r["estimare"]),
            "punct_termic": r and r["punct_termic"],
            "alte_avarii": [f'{x["agent"]}: {x["motiv"]} (estimare {x["estimare"]})' for x in rows if x not in mine],
            "ultima_citire": self.coordinator.last_success,
        }
