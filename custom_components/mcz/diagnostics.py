from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Retourne les données de diagnostique pour une config_entry."""
    
    data_integration = hass.data[DOMAIN].get(entry.entry_id, {})

    diagnostics: dict = {
        "entry_data": entry.data,       # données de config
        "options": entry.options,       # options de l’entrée
        "internal_state": data_integration,  # état interne qu’on veut exposer
    }

    return diagnostics
