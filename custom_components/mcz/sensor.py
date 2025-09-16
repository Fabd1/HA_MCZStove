from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device import MczStove


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    stove: MczStove = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MczStoveStateSensor(stove)])


class MczStoveStateSensor(SensorEntity):
    """Expose l’état du poêle MCZ comme un capteur."""

    def __init__(self, stove: MczStove):
        self._stove = stove
        self._attr_name = f"{stove.name} State"
        self._attr_unique_id = f"{stove.id}_state"

    @property
    def native_value(self):
        """Retourne l’état courant du poêle (OFF, STARTUP, HEATING, SHUTDOWN)."""
        return self._stove.state.name
