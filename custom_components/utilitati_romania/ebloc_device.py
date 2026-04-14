from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMENIU
from .naming import clean_association_name, slugify_text


def alias_apartament_ebloc(cont) -> str:
    raw = getattr(cont, 'date_brute', None) or {}
    asociatie = clean_association_name(raw.get('nume_asociatie') or getattr(cont, 'nume', None) or 'Asociație')
    ap = raw.get('apartament') or raw.get('numar_apartament') or getattr(cont, 'id_cont', None) or 'Apartament'
    return f"{asociatie} - Ap. {ap}"


def slug_apartament_ebloc(cont) -> str:
    raw = getattr(cont, 'date_brute', None) or {}
    asociatie = clean_association_name(raw.get('nume_asociatie') or getattr(cont, 'nume', None) or 'asociatie')
    ap = raw.get('apartament') or raw.get('numar_apartament') or getattr(cont, 'id_cont', None) or 'apartament'
    return slugify_text(f"{asociatie}_ap_{ap}")


def info_device_ebloc(entry_id: str) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMENIU, f"{entry_id}_ebloc")},
        name='eBloc',
        manufacturer='onitium',
        model='serviciu',
    )


def info_device_ebloc_apartament(entry_id: str, cont) -> DeviceInfo:
    raw = getattr(cont, 'date_brute', None) or {}
    id_asoc = raw.get('id_asoc', 'asoc')
    id_ap = raw.get('id_ap', 'ap')
    return DeviceInfo(
        identifiers={(DOMENIU, f"{entry_id}_ebloc_{id_asoc}_{id_ap}")},
        name=f"eBloc – {alias_apartament_ebloc(cont)}",
        manufacturer='onitium',
        model='apartament',
    )
