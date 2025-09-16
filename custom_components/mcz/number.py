from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .device import MczStove


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Configure le number (puissance de flamme) à partir de l'entrée de configuration."""
    stove: MczStove = hass.data["mcz"][config_entry.entry_id]
    async_add_entities([
        MczStoveFlame(stove),
        MczStoveFan(stove, 1),
        MczStoveFan(stove, 2),
    ])

class MczStoveFan(NumberEntity):
    """Contrôle d’un ventilateur du poêle."""

    def __init__(self, stove: MczStove, fan_num: int):
        self._stove = stove
        self._fan_num = fan_num
        self._attr_name = f"{stove.name} Fan {fan_num}"
        self._attr_unique_id = f"{stove.id}_fan{fan_num}"
        self._attr_native_min_value = 1
        self._attr_native_max_value = 6  # 6 = auto d'après ton init.py
        self._attr_native_step = 1
        self._attr_mode = "slider"

    @property
    def native_value(self):
        return self._stove.fan1 if self._fan_num == 1 else self._stove.fan2

    async def async_set_native_value(self, value: float):
        await self._stove.async_set_fan(self._fan_num, int(value))
        self.async_write_ha_state()


class MczStoveFlame(NumberEntity):
    """Contrôle de la puissance de la flamme."""

    def __init__(self, stove: MczStove):
        self._stove = stove
        self._attr_name = f"{stove.name} Flame"
        self._attr_unique_id = f"{stove.id}_flame"
        self._attr_native_min_value = 1
        self._attr_native_max_value = 5
        self._attr_native_step = 1
        self._attr_mode = "slider"

    @property
    def native_value(self):
        return self._stove.flame_power

    async def async_set_native_value(self, value: float):
        await self._stove.async_set_flame_power(int(value))
        self.async_write_ha_state()
