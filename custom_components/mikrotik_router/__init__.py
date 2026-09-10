"""Mikrotik Router integration."""

from __future__ import annotations

import voluptuous as vol
import logging

from homeassistant.components import zone
from homeassistant.components.device_tracker import DOMAIN as DEVICE_TRACKER_DOMAIN
from homeassistant.components.device_tracker.const import CONF_ASSOCIATED_ZONE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.config_entries import ConfigEntry

from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SSL,
    CONF_VERIFY_SSL,
    CONF_ZONE,
    STATE_HOME,
)
from homeassistant.util import slugify

from .const import PLATFORMS, DOMAIN, DEFAULT_VERIFY_SSL
from .coordinator import MikrotikData, MikrotikCoordinator, MikrotikTrackerCoordinator
from .helper import router_unique_id

SCRIPT_SCHEMA = vol.Schema(
    {vol.Required("router"): cv.string, vol.Required("script"): cv.string}
)

_LOGGER = logging.getLogger(__name__)


# ---------------------------
#   async_setup_entry
# ---------------------------
async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    coordinator = MikrotikCoordinator(hass, config_entry)
    await coordinator.async_config_entry_first_refresh()
    _async_update_router_unique_id(hass, config_entry, coordinator)
    coordinatorTracker = MikrotikTrackerCoordinator(hass, config_entry, coordinator)
    await coordinatorTracker.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = MikrotikData(
        data_coordinator=coordinator,
        tracker_coordinator=coordinatorTracker,
    )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))

    return True


# ---------------------------
#   _async_update_router_unique_id
# ---------------------------
def _async_update_router_unique_id(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    coordinator: MikrotikCoordinator,
) -> None:
    """Upgrade a fallback config-entry ID to a RouterBOARD serial."""
    if config_entry.unique_id and not config_entry.unique_id.startswith("endpoint:"):
        return

    unique_id = router_unique_id(
        config_entry.data[CONF_HOST],
        config_entry.data[CONF_PORT],
        config_entry.data[CONF_SSL],
        coordinator.ds["routerboard"].get("serial-number"),
    )
    if unique_id == config_entry.unique_id:
        return

    existing_entry = hass.config_entries.async_entry_for_domain_unique_id(
        DOMAIN, unique_id
    )
    if existing_entry and existing_entry.entry_id != config_entry.entry_id:
        _LOGGER.warning(
            "Mikrotik %s has the same RouterBOARD identifier as configuration %s; preserving both existing entries",
            config_entry.title,
            existing_entry.title,
        )
        return

    hass.config_entries.async_update_entry(config_entry, unique_id=unique_id)


# ---------------------------
#   async_reload_entry
# ---------------------------
async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the config entry when it changed."""
    await hass.config_entries.async_reload(config_entry.entry_id)


# ---------------------------
#   async_unload_entry
# ---------------------------
async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


# ---------------------------
#   async_remove_config_entry_device
# ---------------------------
async def async_remove_config_entry_device(
    hass, config_entry: ConfigEntry, device_entry: device_registry.DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    return True


# ---------------------------
#   async_migrate_entry
# ---------------------------
def _legacy_zone_entity_id(hass: HomeAssistant, legacy_zone) -> str:
    """Convert the legacy integration-wide zone to a zone entity ID."""
    zone_name = str(legacy_zone or STATE_HOME).strip()
    normalized_zone_name = zone_name.casefold()

    if normalized_zone_name in (STATE_HOME, zone.ENTITY_ID_HOME):
        return zone.ENTITY_ID_HOME

    if normalized_zone_name.startswith(f"{zone.DOMAIN}."):
        return normalized_zone_name

    for zone_state in hass.states.async_all(zone.DOMAIN):
        if zone_state.name.casefold() == normalized_zone_name:
            return zone_state.entity_id

    return f"{zone.DOMAIN}.{slugify(zone_name)}"


def _async_migrate_device_tracker_zones(
    hass: HomeAssistant, config_entry: ConfigEntry, legacy_zone
) -> None:
    """Move the integration-wide zone to per-entity tracker options."""
    registry = entity_registry.async_get(hass)
    associated_zone = _legacy_zone_entity_id(hass, legacy_zone)

    for entry in entity_registry.async_entries_for_config_entry(
        registry, config_entry.entry_id
    ):
        if entry.domain != DEVICE_TRACKER_DOMAIN or entry.platform != DOMAIN:
            continue

        tracker_options = dict(entry.options.get(DEVICE_TRACKER_DOMAIN, {}))
        if CONF_ASSOCIATED_ZONE in tracker_options:
            continue

        tracker_options[CONF_ASSOCIATED_ZONE] = associated_zone
        registry.async_update_entity_options(
            entry.entity_id, DEVICE_TRACKER_DOMAIN, tracker_options
        )


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    _LOGGER.debug(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    new_data = {**config_entry.data}
    new_options = {**config_entry.options}
    new_version = config_entry.version
    new_minor_version = config_entry.minor_version
    new_unique_id = config_entry.unique_id

    if new_version < 2:
        new_data[CONF_VERIFY_SSL] = DEFAULT_VERIFY_SSL
        new_version = 2
        new_minor_version = 1

    if new_version == 2 and new_minor_version < 2:
        if new_unique_id is None:
            new_unique_id = router_unique_id(
                new_data[CONF_HOST],
                new_data[CONF_PORT],
                new_data[CONF_SSL],
            )
        new_minor_version = 2

    if new_version < 3:
        legacy_zone = new_options.get(CONF_ZONE, STATE_HOME)
        _async_migrate_device_tracker_zones(hass, config_entry, legacy_zone)
        new_options.pop(CONF_ZONE, None)
        new_version = 3
        new_minor_version = 1

    if (
        new_data != config_entry.data
        or new_options != config_entry.options
        or new_version != config_entry.version
        or new_minor_version != config_entry.minor_version
        or new_unique_id != config_entry.unique_id
    ):
        hass.config_entries.async_update_entry(
            config_entry,
            data=new_data,
            options=new_options,
            unique_id=new_unique_id,
            version=new_version,
            minor_version=new_minor_version,
        )

    _LOGGER.debug(
        "Migration to configuration version %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
    )
    return True
