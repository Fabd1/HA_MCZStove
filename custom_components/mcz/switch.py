from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.switch import SwitchEntity

from .device import MczStove

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Configure le switch à partir de l'entrée de configuration."""
    stove: MczStove = hass.data["mcz"][config_entry.entry_id]
    async_add_entities([MczStoveSwitch(stove)])

class MczStoveSwitch(SwitchEntity):
    """Switch pour allumer/éteindre le poêle."""

    def __init__(self, stove: MczStove):
        self._stove = stove
        self._attr_name = f"{stove.name} Power"
        self._attr_unique_id = f"{stove.id}_power"

    @property
    def is_on(self):
        return self._stove.is_on

    async def async_turn_on(self, **kwargs):
        await self._stove.async_turn_on()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._stove.async_turn_off()
        self.async_write_ha_state()
