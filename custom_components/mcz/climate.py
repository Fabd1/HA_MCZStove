from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import HVACMode, ClimateEntityFeature, HVACAction
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE


from .const import DOMAIN
from .device import MczStove, StoveState  


ACTION_MAP = {
    StoveState.OFF: HVACAction.OFF,
    StoveState.STARTUP: HVACAction.PREHEATING,
    StoveState.HEATING: HVACAction.HEATING,
    StoveState.IDLE: HVACAction.IDLE, 
    StoveState.SHUTDOWN: HVACAction.OFF,  # ou PREHEATING si tu veux montrer un "cooldown"
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up climate entity from config_entry."""
    stove: MczStove = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MczClimate(stove)])


class MczClimate(ClimateEntity):
    """ClimateEntity pour un poêle MCZ."""

    PRESET_MODES = ["eco", "comfort", "sleep", "away", "boost"]

    def __init__(self, stove: MczStove):
        self._stove = stove
        self._attr_name = stove.name
        self._attr_unique_id = stove.id
        self._attr_preset_modes = self.PRESET_MODES 
        self._attr_preset_mode = None  # état initial



    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS

    @property
    def current_temperature(self):
        return self._stove.current_temperature

    @property
    def target_temperature(self):
        return self._stove.target_temperature

    @property
    def hvac_mode(self):
        if not self._stove.is_on:
            return HVACMode.OFF
        if self._stove.is_auto:  # <-- tu dois exposer un attribut .is_auto dans MczStove
            return HVACMode.AUTO
        return HVACMode.HEAT
        """return HVACMode.HEAT if self._stove.is_on else HVACMode.OFF"""

    @property
    def hvac_modes(self):
        return [HVACMode.HEAT, HVACMode.AUTO, HVACMode.OFF]

    @property
    def preset_modes(self):
        return self._attr_preset_modes

    @property
    def hvac_action(self):
        return ACTION_MAP.get(self._stove.state, HVACAction.OFF)


    @property
    def preset_mode(self):
        # Retourne simplement le mode du stove, mais s'assure que c'est un mode valide
        if self._stove.mode in self._attr_preset_modes:
            return self._stove.mode
        return None  # ou "eco" seulement si tu veux un fallback


    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            await self._stove.async_set_temperature(kwargs[ATTR_TEMPERATURE])
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.OFF:
            await self._stove.async_turn_off()
        elif hvac_mode == HVACMode.HEAT:
            await self._stove.async_turn_on()
            await self._stove.async_set_manual()
        elif hvac_mode == HVACMode.AUTO:
            await self._stove.async_turn_on()
            await self._stove.async_set_auto()
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str):
        if preset_mode in self._attr_preset_modes:
            await self._stove.async_set_mode(preset_mode)
            self._attr_preset_mode = preset_mode
            self.async_write_ha_state()

    @property
    def supported_features(self):
        return ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
