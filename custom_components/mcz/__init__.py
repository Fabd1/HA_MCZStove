"""
The "hello world" custom component.

This component implements the bare minimum that a component should implement.

Configuration:

To use the hello_world component you will need to add the following to your
configuration.yaml file.

hello_world:
"""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import entity_platform
from homeassistant.helpers.discovery import async_load_platform
from .device import MczStove
from .switch import MczStoveSwitch
from .number import MczStoveFan, MczStoveFlame


from .const import DOMAIN, PLATFORMS
# Forcer l'import pour éviter les appels bloquants à import_module pendant la boucle event loop
from . import climate  # ou sensor, switch, etc. selon les plateformes que tu as

# The domain of your component. Should be equal to the name of your component.
#DOMAIN = "mcz"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up a skeleton component."""
    # States are in the format DOMAIN.OBJECT_ID.
#    hass.states.set('mcz.world', 'Works!')
    await hass.loop.run_in_executor(None, lambda: hass.states.set('mcz.world', 'Works!'))
    """Set up MCZ from configuration.yaml."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN in config:
        # Vérifie s'il existe déjà une config_entry pour ce domaine
        existing_entries = [
            entry for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.source == "import"
        ]

        if not existing_entries:
            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": "import"},
                    data=config[DOMAIN]
                )
            )



    # Return boolean to indicate that initialization was successfully.
    return True



async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MCZ from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Crée l’objet qui représente le poêle
    stove = MczStove(
        hass,
        device_id=entry.data["device_id"],
        name=entry.data.get("name", "Poêle MCZ"),
    )

    # Stocke l’instance pour que climate.py (ou autres plateformes) puisse l’utiliser
    hass.data[DOMAIN][entry.entry_id] = stove

    # Charger les plateformes modernes
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
