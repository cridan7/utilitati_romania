from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import CONF_FURNIZOR, DOMENIU, FURNIZOR_ADMIN_GLOBAL
from .licentiere import async_obtine_licenta_globala


def _admin_device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMENIU, entry.entry_id)},
        name="Administrare integrare",
        manufacturer="onitium",
        model="Utilitati Romania",
        entry_type=None,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    if entry.data.get(CONF_FURNIZOR) != FURNIZOR_ADMIN_GLOBAL:
        return

    async_add_entities([TextCodLicentaNoua(entry)])


class TextCodLicentaNoua(RestoreEntity, TextEntity):
    _attr_icon = "mdi:key-outline"
    _attr_native_min = 0
    _attr_native_max = 128
    _attr_mode = "text"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_admin_cod_licenta_noua"
        self._attr_name = "Cod licență nou"
        self._attr_suggested_object_id = f"{DOMENIU}_cod_licenta_noua"
        self.entity_id = f"text.{DOMENIU}_cod_licenta_noua"
        self._attr_device_info = _admin_device_info(entry)
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_value = ""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        storage = await async_obtine_licenta_globala(self.hass)
        storage_key = str(storage.get("cheie_licenta", "")).strip() if isinstance(storage, dict) else ""

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (None, "unknown", "unavailable"):
            self._attr_native_value = last_state.state
        elif storage_key:
            self._attr_native_value = storage_key

    async def async_set_value(self, value: str) -> None:
        self._attr_native_value = value[: self._attr_native_max]
        self.async_write_ha_state()