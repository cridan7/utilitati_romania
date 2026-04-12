from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er

from .const import CONF_FURNIZOR, CONF_PREMISE_LABEL, DOMENIU, PLATFORME, FURNIZOR_ADMIN_GLOBAL, SERVICIU_RELOAD_ALL
from .coordonator import CoordonatorUtilitatiRomania
from .deer_device import alias_loc_deer, slug_loc_deer
from .eon_device import alias_loc_eon, slug_loc_eon
from .hidro_device import alias_loc_consum, slug_loc_consum
from .myelectrica_device import alias_loc_myelectrica, slug_loc_myelectrica
from .ebloc_device import alias_apartament_ebloc, slug_apartament_ebloc
from .naming import build_provider_slug, extract_street_slug


def _slug_legacy(text: str | None) -> str:
    value = str(text or "cont").lower()
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")[:100] or "cont"


APA_CANAL_OBJECT_KEY_MAP = {
    "last_consumption": "ultimul_consum",
    "last_meter_reading": "ultimul_index",
    "current_balance": "sold_curent",
    "last_invoice": "ultima_factura",
    "last_payment": "ultima_plata",
}


def _safe_entity_id(domain: str, object_id: str) -> str:
    object_id = object_id[:240].strip("_")
    return f"{domain}.{object_id}"



async def _async_reload_all_entries(hass: HomeAssistant) -> None:
    for existing_entry in list(hass.config_entries.async_entries(DOMENIU)):
        if existing_entry.data.get(CONF_FURNIZOR) == FURNIZOR_ADMIN_GLOBAL:
            continue
        await hass.config_entries.async_reload(existing_entry.entry_id)


def _async_ensure_services(hass: HomeAssistant) -> None:
    if hass.data[DOMENIU].get("_services_registered"):
        return

    async def _async_handle_reload_all(call: ServiceCall) -> None:
        await _async_reload_all_entries(hass)

    hass.services.async_register(DOMENIU, SERVICIU_RELOAD_ALL, _async_handle_reload_all)
    hass.data[DOMENIU]["_services_registered"] = True


def _async_remove_services_if_unused(hass: HomeAssistant) -> None:
    remaining = [e for e in hass.config_entries.async_entries(DOMENIU) if e.state is not None]
    if remaining:
        return
    if hass.services.has_service(DOMENIU, SERVICIU_RELOAD_ALL):
        hass.services.async_remove(DOMENIU, SERVICIU_RELOAD_ALL)
    hass.data[DOMENIU]["_services_registered"] = False


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMENIU, {})
    _async_ensure_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _async_ensure_services(hass)
    if entry.data.get(CONF_FURNIZOR) == FURNIZOR_ADMIN_GLOBAL:
        hass.data[DOMENIU][entry.entry_id] = {"admin": True}
        await hass.config_entries.async_forward_entry_setups(entry, [Platform.SENSOR, Platform.BUTTON])
        return True

    coordonator = CoordonatorUtilitatiRomania(hass, entry)
    await coordonator.async_config_entry_first_refresh()
    await _migrare_unique_ids(hass, entry, coordonator)
    hass.data[DOMENIU][entry.entry_id] = coordonator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORME)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if entry.data.get(CONF_FURNIZOR) == FURNIZOR_ADMIN_GLOBAL:
        descarcat = await hass.config_entries.async_unload_platforms(entry, [Platform.SENSOR, Platform.BUTTON])
        if descarcat:
            hass.data[DOMENIU].pop(entry.entry_id, None)
        _async_remove_services_if_unused(hass)
        return descarcat

    descarcat = await hass.config_entries.async_unload_platforms(entry, PLATFORME)
    if descarcat:
        hass.data[DOMENIU].pop(entry.entry_id, None)
    _async_remove_services_if_unused(hass)
    return descarcat


def _migrare_senzori_hidro(entry_id: str, data) -> dict[str, tuple[str, str]]:
    from .sensor import SENZORI_CONT_HIDRO

    mapping: dict[str, tuple[str, str]] = {}
    for cont in data.conturi:
        alias_nou = alias_loc_consum(cont.nume, cont.adresa, cont.id_cont)
        slug_nou = slug_loc_consum(cont.id_cont, alias_nou, cont.adresa)
        old_slugs = {
            _slug_legacy(getattr(cont, "id_cont", None) or getattr(cont, "nume", None) or getattr(cont, "adresa", None)),
            build_provider_slug("hidro", getattr(cont, "adresa", None) or alias_nou, getattr(cont, "id_cont", None)),
            build_provider_slug("hidroelectrica", getattr(cont, "adresa", None) or alias_nou, getattr(cont, "id_cont", None)),
        }
        for descriere in SENZORI_CONT_HIDRO:
            new_unique = f"{entry_id}_hidro_{cont.id_cont}_{descriere.key}"
            new_object_id = f"hidro_{cont.id_cont}_{slug_nou}_{descriere.key}"
            mapping[new_unique] = (new_unique, new_object_id)
            mapping[f"{entry_id}_{slug_nou}_{descriere.key}"] = (new_unique, new_object_id)
            for old_slug in old_slugs:
                mapping[f"{entry_id}_hidro_{old_slug}_{descriere.key}"] = (new_unique, new_object_id)
                mapping[f"{entry_id}_{old_slug}_{descriere.key}"] = (new_unique, new_object_id)
    return mapping


def _migrare_senzori_eon(entry_id: str, data) -> dict[str, tuple[str, str]]:
    from .sensor import SENZORI_CONT_EON, SENZORI_CONT_EON_EXTINS, _an_curent_loc_eon

    mapping: dict[str, tuple[str, str]] = {}
    for cont in data.conturi:
        alias_nou = alias_loc_eon(cont.nume, cont.adresa, cont.id_cont)
        slug_nou = slug_loc_eon(cont.id_cont, alias_nou, cont.adresa)
        old_slugs = {
            _slug_legacy(getattr(cont, "id_cont", None) or getattr(cont, "nume", None) or "cont"),
            build_provider_slug("eon", getattr(cont, "adresa", None) or alias_nou, getattr(cont, "id_cont", None)),
            build_provider_slug("eon", getattr(cont, "nume", None) or alias_nou, getattr(cont, "id_cont", None)),
        }
        for descriere in SENZORI_CONT_EON:
            new_unique = f"{entry_id}_{slug_nou}_{descriere.key}"
            new_object_id = f"{slug_nou}_{descriere.key}"
            mapping[new_unique] = (new_unique, new_object_id)
            for old_slug in old_slugs:
                mapping[f"{entry_id}_eon_{old_slug}_{descriere.key}"] = (new_unique, new_object_id)
                mapping[f"{entry_id}_{old_slug}_{descriere.key}"] = (new_unique, new_object_id)
        an = _an_curent_loc_eon(cont)
        tip = (getattr(cont, "tip_serviciu", None) or getattr(cont, "tip_utilitate", None) or "curent")
        for descriere in SENZORI_CONT_EON_EXTINS:
            suffix = an if descriere.key.startswith("arhiva_") else "base"
            if descriere.key == "arhiva_consum":
                object_suffix = f"arhiva_consum_{'gaz' if tip == 'gaz' else 'energie_electrica'}_{an}"
            elif descriere.key == "arhiva_index":
                object_suffix = f"arhiva_index_{'gaz' if tip == 'gaz' else 'energie_electrica'}_{an}"
            elif descriere.key == "arhiva_plati":
                object_suffix = f"arhiva_plati_{an}"
            else:
                object_suffix = descriere.key
            new_unique = f"{entry_id}_{slug_nou}_{descriere.key}_{suffix}"
            new_object_id = f"{slug_nou}_{object_suffix}"
            mapping[new_unique] = (new_unique, new_object_id)
            for old_slug in old_slugs:
                mapping[f"{entry_id}_eon_{old_slug}_{descriere.key}_{suffix}"] = (new_unique, new_object_id)
                mapping[f"{entry_id}_{old_slug}_{descriere.key}_{suffix}"] = (new_unique, new_object_id)
    return mapping


def _migrare_senzori_myelectrica(entry_id: str, data) -> dict[str, tuple[str, str]]:
    from .sensor import SENZORI_CONT_MYELECTRICA

    mapping: dict[str, tuple[str, str]] = {}
    for cont in data.conturi:
        alias_nou = alias_loc_myelectrica(cont.nume, cont.adresa, cont.id_cont)
        slug_nou = slug_loc_myelectrica(cont.id_cont, alias_nou, cont.adresa)
        alias_vechi = str(getattr(cont, "adresa", None) or "").split(",")[0].strip() or str(getattr(cont, "nume", None) or f"NLC {cont.id_cont}")
        old_slugs = {
            _slug_legacy(f"{cont.id_cont}_{alias_vechi}"),
            build_provider_slug("myelectrica", getattr(cont, "adresa", None) or alias_nou, getattr(cont, "id_cont", None)),
            build_provider_slug("myelectrica", getattr(cont, "nume", None) or alias_nou, getattr(cont, "id_cont", None)),
        }
        for descriere in SENZORI_CONT_MYELECTRICA:
            new_unique = f"{entry_id}_{slug_nou}_{descriere.key}"
            new_object_id = f"{slug_nou}_{descriere.key}"
            mapping[new_unique] = (new_unique, new_object_id)
            for old_slug in old_slugs:
                mapping[f"{entry_id}_myelectrica_{old_slug}_{descriere.key}"] = (new_unique, new_object_id)
                mapping[f"{entry_id}_{old_slug}_{descriere.key}"] = (new_unique, new_object_id)
    return mapping


def _migrare_senzori_deer(entry_id: str, data) -> dict[str, tuple[str, str]]:
    from .sensor import SENZORI_CONT_DEER

    mapping: dict[str, tuple[str, str]] = {}
    for cont in data.conturi:
        alias_nou = alias_loc_deer(cont.nume, cont.adresa, cont.id_cont)
        slug_nou = slug_loc_deer(cont.id_cont, alias_nou, cont.adresa)
        old_slugs = {
            _slug_legacy(f"{cont.id_cont}_{getattr(cont, 'adresa', None) or getattr(cont, 'nume', None) or ''}"),
            build_provider_slug("deer", getattr(cont, "adresa", None), getattr(cont, "id_cont", None)),
            build_provider_slug("deer", getattr(cont, "nume", None), getattr(cont, "id_cont", None)),
        }
        street_only = extract_street_slug(getattr(cont, "adresa", None), getattr(cont, "id_cont", None))
        if street_only:
            old_slugs.add(f"deer_loc_{street_only}")
            old_slugs.add(f"deer_{street_only}")
        for descriere in SENZORI_CONT_DEER:
            new_unique = f"{entry_id}_{slug_nou}_{descriere.key}"
            new_object_id = f"{slug_nou}_{descriere.key}"
            mapping[new_unique] = (new_unique, new_object_id)
            for old_slug in old_slugs:
                mapping[f"{entry_id}_{old_slug}_{descriere.key}"] = (new_unique, new_object_id)
    return mapping


def _migrare_senzori_apa_canal(entry, data) -> dict[str, tuple[str, str]]:
    from .sensor import SENZORI_APA_CANAL

    premise_label = str(entry.data.get(CONF_PREMISE_LABEL) or entry.title or "contract").strip()
    slug_nou = build_provider_slug("apa_canal_sibiu", premise_label, premise_label)
    old_slugs = {
        "apa_canal",
        build_provider_slug("apa_canal_sibiu", premise_label, premise_label),
        _slug_legacy(f"apa_canal_sibiu_{premise_label}"),
    }
    mapping: dict[str, tuple[str, str]] = {}
    for descriere in SENZORI_APA_CANAL:
        object_key = APA_CANAL_OBJECT_KEY_MAP.get(descriere.key, descriere.key)
        new_unique = f"{entry.entry_id}_{slug_nou}_{object_key}"
        new_object_id = f"{slug_nou}_{object_key}"
        mapping[new_unique] = (new_unique, new_object_id)
        mapping[f"{entry.entry_id}_apa_canal_{descriere.key}"] = (new_unique, new_object_id)
        for old_slug in old_slugs:
            mapping[f"{entry.entry_id}_{old_slug}_{descriere.key}"] = (new_unique, new_object_id)
    return mapping




def _migrare_senzori_ebloc(entry_id: str, data) -> dict[str, tuple[str, str]]:
    from .sensor import SENZORI_CONT_EBLOC

    mapping: dict[str, tuple[str, str]] = {}
    for cont in data.conturi:
        slug_nou = slug_apartament_ebloc(cont)
        alias_vechi = alias_apartament_ebloc(cont)
        old_slugs = {
            _slug_legacy(alias_vechi),
            _slug_legacy(f"{getattr(cont, 'id_cont', '')}_{alias_vechi}"),
            f"ebloc_{_slug_legacy(alias_vechi)}",
        }
        for descriere in SENZORI_CONT_EBLOC:
            new_unique = f"{entry_id}_ebloc_{slug_nou}_{descriere.key}"
            new_object_id = f"ebloc_{slug_nou}_{descriere.key}"
            mapping[new_unique] = (new_unique, new_object_id)
            for old_slug in old_slugs:
                mapping[f"{entry_id}_ebloc_{old_slug}_{descriere.key}"] = (new_unique, new_object_id)
    return mapping


def _migrare_senzori_nova(entry_id: str, data) -> dict[str, tuple[str, str]]:
    from .sensor import SENZORI_REZUMAT, SENZORI_REZUMAT_FINANCIAR

    mapping: dict[str, tuple[str, str]] = {}
    conturi = data.conturi or []
    if len(conturi) == 1:
        slug = build_provider_slug("nova", getattr(conturi[0], "adresa", None), getattr(conturi[0], "id_cont", None))
    elif len(conturi) > 1:
        slug = "nova_multi"
    else:
        slug = "nova"
    for descriere in list(SENZORI_REZUMAT) + list(SENZORI_REZUMAT_FINANCIAR):
        new_unique = f"{entry_id}_{descriere.key}"
        new_object_id = f"{slug}_{descriere.key}"
        mapping[new_unique] = (new_unique, new_object_id)
    return mapping

async def _migrare_unique_ids(hass: HomeAssistant, entry: ConfigEntry, coordonator: CoordonatorUtilitatiRomania) -> None:
    data = coordonator.data
    if not data:
        return

    furnizor = entry.data.get("furnizor")
    if furnizor == "hidroelectrica":
        mapping = _migrare_senzori_hidro(entry.entry_id, data)
    elif furnizor == "eon":
        mapping = _migrare_senzori_eon(entry.entry_id, data)
    elif furnizor == "myelectrica":
        mapping = _migrare_senzori_myelectrica(entry.entry_id, data)
    elif furnizor == "deer":
        mapping = _migrare_senzori_deer(entry.entry_id, data)
    elif furnizor == "apa_canal":
        mapping = _migrare_senzori_apa_canal(entry, data)
    elif furnizor == "ebloc":
        mapping = _migrare_senzori_ebloc(entry.entry_id, data)
    elif furnizor == "nova":
        mapping = _migrare_senzori_nova(entry.entry_id, data)
    else:
        return

    registry = er.async_get(hass)
    entities = getattr(registry, "entities", {})
    entries = list(entities.values()) if hasattr(entities, "values") else []

    def _find_by_unique(domain: str, unique_id: str):
        for existing in entries:
            if getattr(existing, "domain", None) == domain and getattr(existing, "platform", None) == DOMENIU and getattr(existing, "unique_id", None) == unique_id:
                return existing
        return None

    def _find_by_entity_id(entity_id: str):
        for existing in entries:
            if getattr(existing, "entity_id", None) == entity_id:
                return existing
        return None

    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        mapped = mapping.get(entity_entry.unique_id)
        if not mapped:
            continue

        new_unique_id, new_object_id = mapped
        desired_entity_id = _safe_entity_id(entity_entry.domain, new_object_id)
        existing_target = _find_by_unique(entity_entry.domain, new_unique_id)

        if existing_target and existing_target.entity_id != entity_entry.entity_id:
            if hasattr(registry, "async_remove"):
                try:
                    registry.async_remove(entity_entry.entity_id)
                except Exception:
                    pass
            continue

        try:
            kwargs = {}
            if new_unique_id != entity_entry.unique_id:
                kwargs["new_unique_id"] = new_unique_id
            existing_entity_id = _find_by_entity_id(desired_entity_id)
            if desired_entity_id != entity_entry.entity_id and not existing_entity_id:
                kwargs["new_entity_id"] = desired_entity_id
            if kwargs:
                er.async_update_entity(registry, entity_entry.entity_id, **kwargs)
        except Exception:
            continue

    if furnizor == "deer":
        seen: dict[str, str] = {}
        for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            if entity_entry.domain != "sensor":
                continue
            key = entity_entry.entity_id
            if not key.startswith("sensor.deer_"):
                continue
            if key in seen and hasattr(registry, "async_remove"):
                try:
                    registry.async_remove(entity_entry.entity_id)
                except Exception:
                    pass
            else:
                seen[key] = entity_entry.entity_id
