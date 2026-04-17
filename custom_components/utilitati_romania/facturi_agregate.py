from __future__ import annotations

from datetime import date, datetime
from typing import Any

from .const import DOMENIU, FURNIZOR_ADMIN_GLOBAL
from .coordonator import CoordonatorUtilitatiRomania
from .helpers_facturi_locatie import (
    build_facturi_location_label,
    normalize_facturi_location_key,
)
from .modele import ContUtilitate, FacturaUtilitate, InstantaneuFurnizor
from .naming import normalize_text


_PROVIDER_LABELS = {
    "apa_canal": "Apă Canal Sibiu",
    "apacanal2000": "Apă Canal 2000 Pitești",
    "deer": "DEER",
    "digi": "Digi",
    "ebloc": "eBloc",
    "eon": "E.ON",
    "hidroelectrica": "Hidroelectrica",
    "myelectrica": "myElectrica",
    "nova": "Nova",
}

_STATUS_PAID_TOKENS = {
    "achitat",
    "achitata",
    "paid",
    "platit",
    "platita",
    "plătită",
    "stins",
    "stinsa",
    "nu",
    "no",
    "false",
    "0",
}

_STATUS_UNPAID_TOKENS = {
    "de plata",
    "de_plata",
    "neachitat",
    "neachitata",
    "neplatit",
    "neplatita",
    "neplătită",
    "restant",
    "restanta",
    "scadent",
    "scadenta",
    "unpaid",
    "overdue",
    "da",
    "yes",
    "true",
    "1",
}

_UNPAID_RAW_KEYS = (
    "amount_remaining",
    "AmountRemaining",
    "remainingAmount",
    "UnpaidValue",
    "rest_plata",
    "restToPay",
    "amountToPay",
    "remainingValue",
    "remaining",
    "amountRemaining",
)

_PDF_RAW_KEYS = (
    "pdf_url",
    "download_url",
    "document_url",
    "pdf",
    "url",
)


def _provider_label(provider: str | None) -> str:
    key = str(provider or "").strip().lower()
    return _PROVIDER_LABELS.get(key, key.replace("_", " ").title() or "Furnizor")


def _to_float(value: Any) -> float | None:
    if value in (None, "", "None"):
        return None
    try:
        if isinstance(value, str):
            value = value.replace(" ", "").replace(",", ".")
        return float(value)
    except (TypeError, ValueError):
        return None


def _sort_key_for_date(value: date | datetime | str | None) -> tuple[int, str]:
    if value is None:
        return (0, "")
    if isinstance(value, datetime):
        return (1, value.isoformat())
    if isinstance(value, date):
        return (1, value.isoformat())
    return (1, str(value))


def _format_date(value: date | datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _raw_dict(obj: Any) -> dict[str, Any]:
    raw = getattr(obj, "date_brute", None)
    return raw if isinstance(raw, dict) else {}


def _consum_value(
    instantaneu: InstantaneuFurnizor,
    key: str,
    id_cont: str | None = None,
) -> Any:
    for consum in instantaneu.consumuri or []:
        if getattr(consum, "cheie", None) != key:
            continue
        if id_cont is not None and getattr(consum, "id_cont", None) != id_cont:
            continue
        return getattr(consum, "valoare", None)
    return None


def _cont_for_factura(
    instantaneu: InstantaneuFurnizor,
    factura: FacturaUtilitate,
) -> ContUtilitate | None:
    factura_id_cont = getattr(factura, "id_cont", None)
    if factura_id_cont:
        for cont in instantaneu.conturi or []:
            if getattr(cont, "id_cont", None) == factura_id_cont:
                return cont

    factura_id_contract = getattr(factura, "id_contract", None)
    if factura_id_contract:
        for cont in instantaneu.conturi or []:
            if getattr(cont, "id_contract", None) == factura_id_contract:
                return cont

    if len(instantaneu.conturi or []) == 1:
        return instantaneu.conturi[0]

    return None


def _extract_unpaid_amount(
    instantaneu: InstantaneuFurnizor,
    factura: FacturaUtilitate,
    cont: ContUtilitate | None,
) -> float | None:
    raw = _raw_dict(factura)

    for key in _UNPAID_RAW_KEYS:
        value = _to_float(raw.get(key))
        if value is not None:
            return value

    id_cont = getattr(cont, "id_cont", None) if cont else getattr(factura, "id_cont", None)

    for key in ("sold_factura", "de_plata", "total_neachitat", "sold_curent"):
        value = _to_float(_consum_value(instantaneu, key, id_cont))
        if value is not None:
            return value

    for key in ("factura_restanta",):
        value = normalize_text(_consum_value(instantaneu, key, id_cont)).lower()
        if value in {"da", "yes", "true", "1"}:
            amount = _to_float(getattr(factura, "valoare", None))
            return amount if amount is not None else 1.0
        if value in {"nu", "no", "false", "0"}:
            return 0.0

    return None


def _extract_pdf_url(factura: FacturaUtilitate) -> str | None:
    raw = _raw_dict(factura)
    for key in _PDF_RAW_KEYS:
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _derive_payment_status(
    instantaneu: InstantaneuFurnizor,
    factura: FacturaUtilitate,
    cont: ContUtilitate | None,
) -> tuple[str, bool | None, float | None]:
    amount_value = _to_float(getattr(factura, "valoare", None))
    category = normalize_text(getattr(factura, "categorie", None)).lower()
    status_text = normalize_text(getattr(factura, "stare", None)).lower()

    if category == "injectie" or (amount_value is not None and amount_value < 0):
        return "credit", True, 0.0

    if status_text and any(token in status_text for token in _STATUS_PAID_TOKENS):
        return "paid", True, 0.0

    if status_text and any(token in status_text for token in _STATUS_UNPAID_TOKENS):
        unpaid_amount = _extract_unpaid_amount(instantaneu, factura, cont)
        return "unpaid", False, unpaid_amount

    unpaid_amount = _extract_unpaid_amount(instantaneu, factura, cont)
    if unpaid_amount is not None:
        if unpaid_amount > 0:
            return "unpaid", False, unpaid_amount
        return "paid", True, 0.0

    return "unknown", None, None


def _build_invoice_item(
    coordonator: CoordonatorUtilitatiRomania,
    instantaneu: InstantaneuFurnizor,
    factura: FacturaUtilitate,
) -> dict[str, Any]:
    cont = _cont_for_factura(instantaneu, factura)
    location_key = normalize_facturi_location_key(
        cont or getattr(factura, "id_cont", None) or instantaneu.titlu
    )
    location_label = build_facturi_location_label(cont or instantaneu.titlu)
    payment_status, is_paid, unpaid_amount = _derive_payment_status(
        instantaneu,
        factura,
        cont,
    )

    invoice_title = getattr(factura, "titlu", None) or "Ultima factură"

    # Curățăm titlurile tehnice E.ON de forma "Factura eon_xxx_ultima"
    if (
        instantaneu.furnizor == "eon"
        and isinstance(invoice_title, str)
        and invoice_title.lower().startswith("factura eon_")
    ):
        consum_id = _consum_value(
            instantaneu,
            "id_ultima_factura",
            getattr(factura, "id_cont", None),
        )
        consum_id_text = str(consum_id or "").strip()
        invoice_title = consum_id_text or "Ultima factură"

    return {
        "entry_id": coordonator.intrare.entry_id,
        "entry_title": coordonator.intrare.title,
        "furnizor": instantaneu.furnizor,
        "furnizor_label": _provider_label(instantaneu.furnizor),
        "locatie_cheie": location_key,
        "eticheta_locatie": location_label,
        "adresa_originala": getattr(cont, "adresa", None) if cont else None,
        "id_cont": getattr(factura, "id_cont", None) or (getattr(cont, "id_cont", None) if cont else None),
        "id_contract": getattr(factura, "id_contract", None) or (getattr(cont, "id_contract", None) if cont else None),
        "nume_cont": getattr(cont, "nume", None) if cont else None,
        "tip_utilitate": getattr(factura, "tip_utilitate", None) or (getattr(cont, "tip_utilitate", None) if cont else None),
        "tip_serviciu": getattr(factura, "tip_serviciu", None) or (getattr(cont, "tip_serviciu", None) if cont else None),
        "invoice_id": getattr(factura, "id_factura", None),
        "invoice_title": invoice_title,
        "issue_date": _format_date(getattr(factura, "data_emitere", None)),
        "due_date": _format_date(getattr(factura, "data_scadenta", None)),
        "amount": getattr(factura, "valoare", None),
        "currency": getattr(factura, "moneda", None) or "RON",
        "status_raw": getattr(factura, "stare", None),
        "status": payment_status,
        "payment_status": payment_status,
        "is_paid": is_paid,
        "unpaid_amount": unpaid_amount,
        "pdf_url": _extract_pdf_url(factura),
    }


def _build_eon_fallback_item(
    coordonator: CoordonatorUtilitatiRomania,
    instantaneu: InstantaneuFurnizor,
    cont: ContUtilitate,
) -> dict[str, Any] | None:
    id_cont = getattr(cont, "id_cont", None)
    if not id_cont:
        return None

    hass = coordonator.hass
    cont_raw = cont.date_brute if isinstance(cont.date_brute, dict) else {}

    factura_id = (
        _consum_value(instantaneu, "id_ultima_factura", id_cont)
        or cont_raw.get("id_ultima_factura")
    )
    valoare = _to_float(
        _consum_value(instantaneu, "valoare_ultima_factura", id_cont)
        or cont_raw.get("valoare_ultima_factura")
    )
    data_emitere = (
        _consum_value(instantaneu, "data_ultima_factura", id_cont)
        or cont_raw.get("data_ultima_factura")
    )
    data_scadenta = (
        _consum_value(instantaneu, "urmatoarea_scadenta", id_cont)
        or _consum_value(instantaneu, "data_scadenta", id_cont)
        or _consum_value(instantaneu, "next_due_date", id_cont)
        or cont_raw.get("urmatoarea_scadenta")
        or cont_raw.get("data_scadenta")
        or cont_raw.get("next_due_date")
    )

    if hass:
        if not data_scadenta:
            for state in hass.states.async_all():
                entity_id = state.entity_id
                if not entity_id.startswith("sensor.eon_"):
                    continue

                attrs = state.attributes or {}
                if str(attrs.get("id_cont")) != str(id_cont):
                    continue

                if "urmatoarea_scadenta" in entity_id:
                    state_value = str(state.state or "").strip()
                    if state_value and state_value.lower() not in {"unknown", "unavailable", "none"}:
                        data_scadenta = state_value
                        break

        if not data_emitere:
            for state in hass.states.async_all():
                entity_id = state.entity_id
                if not entity_id.startswith("sensor.eon_"):
                    continue

                attrs = state.attributes or {}
                if str(attrs.get("id_cont")) != str(id_cont):
                    continue

                if "data_ultimei_facturi" in entity_id or "data_ultima_factura" in entity_id:
                    state_value = str(state.state or "").strip()
                    if state_value and state_value.lower() not in {"unknown", "unavailable", "none"}:
                        data_emitere = state_value
                        break

    factura_restanta = (
        _consum_value(instantaneu, "factura_restanta", id_cont)
        or cont_raw.get("factura_restanta")
    )
    de_plata = _to_float(
        _consum_value(instantaneu, "de_plata", id_cont)
        or cont_raw.get("de_plata")
    )
    sold_curent = _to_float(
        _consum_value(instantaneu, "sold_curent", id_cont)
        or cont_raw.get("sold_curent")
    )

    if factura_id in (None, "") and valoare is None and data_scadenta in (None, ""):
        return None

    factura_id_text = (
        str(factura_id).strip()
        if factura_id not in (None, "")
        else f"eon_{id_cont}_ultima"
    )

    factura_restanta_text = normalize_text(factura_restanta).lower()

    if factura_restanta_text in {"da", "yes", "true", "1"}:
        status = "unpaid"
        is_paid = False
        unpaid_amount = (
            de_plata if de_plata is not None and de_plata > 0
            else sold_curent if sold_curent is not None and sold_curent > 0
            else valoare if valoare is not None and valoare > 0
            else 0.0
        )
    elif de_plata is not None and de_plata > 0:
        status = "unpaid"
        is_paid = False
        unpaid_amount = de_plata
    elif sold_curent is not None and sold_curent > 0:
        status = "unpaid"
        is_paid = False
        unpaid_amount = sold_curent
    elif factura_restanta_text in {"nu", "no", "false", "0"}:
        status = "paid"
        is_paid = True
        unpaid_amount = 0.0
    else:
        status = "unknown"
        is_paid = None
        unpaid_amount = None

    issue_date = _format_date(data_emitere)
    due_date = _format_date(data_scadenta)

    return {
        "entry_id": coordonator.intrare.entry_id,
        "entry_title": coordonator.intrare.title,
        "furnizor": instantaneu.furnizor,
        "furnizor_label": _provider_label(instantaneu.furnizor),
        "locatie_cheie": normalize_facturi_location_key(cont),
        "eticheta_locatie": build_facturi_location_label(cont),
        "adresa_originala": getattr(cont, "adresa", None),
        "id_cont": id_cont,
        "id_contract": getattr(cont, "id_contract", None),
        "nume_cont": getattr(cont, "nume", None),
        "tip_utilitate": getattr(cont, "tip_utilitate", None),
        "tip_serviciu": getattr(cont, "tip_serviciu", None),
        "invoice_id": factura_id_text,
        "invoice_title": factura_id_text if factura_id_text and not factura_id_text.lower().startswith("eon_") else "Ultima factură",
        "issue_date": issue_date,
        "due_date": due_date,
        "amount": valoare,
        "currency": "RON",
        "status_raw": factura_restanta,
        "status": status,
        "payment_status": status,
        "is_paid": is_paid,
        "unpaid_amount": unpaid_amount,
        "pdf_url": None,
    }




def _money_to_lei(value: Any) -> float | None:
    parsed = _to_float(value)
    if parsed is None:
        return None
    # eBloc sumele brute vin frecvent în bani (ex. 201496700 pentru 2.014.967,00?)
    # sau în lei deja normalizați. Considerăm "bani" doar valorile întregi mari.
    if isinstance(value, str):
        raw = value.strip().replace(' ', '')
        if raw.isdigit() and len(raw) >= 4:
            return round(float(raw) / 100.0, 2)
    if isinstance(value, int) and abs(value) >= 1000:
        return round(float(value) / 100.0, 2)
    return round(parsed, 2)


def _ebloc_latest_payment_from_raw(cont_raw: dict[str, Any]) -> tuple[float | None, str | None]:
    plati_raw = cont_raw.get('plati_brute') if isinstance(cont_raw.get('plati_brute'), dict) else {}
    chitante = plati_raw.get('aChitante') if isinstance(plati_raw, dict) else None
    if not isinstance(chitante, list) or not chitante:
        return None, None
    latest = chitante[0] if isinstance(chitante[0], dict) else {}
    amount = _money_to_lei(latest.get('suma'))
    payment_date = _format_date(latest.get('data'))
    return amount, payment_date


def _build_ebloc_fallback_item(
    coordonator: CoordonatorUtilitatiRomania,
    instantaneu: InstantaneuFurnizor,
    cont: ContUtilitate,
) -> dict[str, Any] | None:
    id_cont = getattr(cont, 'id_cont', None)
    if not id_cont:
        return None

    cont_raw = cont.date_brute if isinstance(cont.date_brute, dict) else {}
    de_plata = _to_float(_consum_value(instantaneu, 'de_plata', id_cont) or cont_raw.get('de_plata'))
    sold_curent = _to_float(_consum_value(instantaneu, 'sold_curent', id_cont) or cont_raw.get('sold_curent'))
    factura_restanta = _consum_value(instantaneu, 'factura_restanta', id_cont) or cont_raw.get('factura_restanta')
    due_date = _format_date(_consum_value(instantaneu, 'urmatoarea_scadenta', id_cont) or cont_raw.get('data_scadenta'))

    latest_payment_amount = _to_float(_consum_value(instantaneu, 'valoare_ultima_plata', id_cont))
    latest_payment_date = _format_date(_consum_value(instantaneu, 'data_ultima_plata', id_cont))
    if latest_payment_amount is None:
        latest_payment_amount, raw_payment_date = _ebloc_latest_payment_from_raw(cont_raw)
        if latest_payment_date is None:
            latest_payment_date = raw_payment_date

    # Dacă e plătită, în card trebuie afișată ultima plată, nu soldul curent.
    restanta_text = normalize_text(factura_restanta).lower()
    has_unpaid = False
    if restanta_text in {'da', 'yes', 'true', '1'}:
        has_unpaid = True
    elif de_plata is not None and de_plata > 0:
        has_unpaid = True
    elif sold_curent is not None and sold_curent > 0:
        has_unpaid = True

    if has_unpaid:
        status = 'unpaid'
        is_paid = False
        unpaid_amount = de_plata if de_plata is not None and de_plata > 0 else sold_curent
        amount = unpaid_amount
        issue_date = None
        invoice_title = f"Întreținere {cont_raw.get('numar_apartament') or ''}".strip()
        status_raw = factura_restanta or 'Da'
    else:
        status = 'paid'
        is_paid = True
        unpaid_amount = 0.0
        amount = latest_payment_amount
        issue_date = latest_payment_date
        invoice_title = 'Ultima plată'
        status_raw = factura_restanta or 'Nu'

    if amount is None and due_date is None and issue_date is None:
        return None

    return {
        'entry_id': coordonator.intrare.entry_id,
        'entry_title': coordonator.intrare.title,
        'furnizor': instantaneu.furnizor,
        'furnizor_label': _provider_label(instantaneu.furnizor),
        'locatie_cheie': normalize_facturi_location_key(cont),
        'eticheta_locatie': build_facturi_location_label(cont),
        'adresa_originala': getattr(cont, 'adresa', None),
        'id_cont': id_cont,
        'id_contract': getattr(cont, 'id_contract', None),
        'nume_cont': getattr(cont, 'nume', None),
        'tip_utilitate': getattr(cont, 'tip_utilitate', None),
        'tip_serviciu': getattr(cont, 'tip_serviciu', None),
        'invoice_id': f'ebloc_{id_cont}_summary',
        'invoice_title': invoice_title or 'Situație curentă',
        'issue_date': issue_date,
        'due_date': due_date,
        'amount': amount,
        'currency': 'RON',
        'status_raw': status_raw,
        'status': status,
        'payment_status': status,
        'is_paid': is_paid,
        'unpaid_amount': unpaid_amount,
        'pdf_url': None,
    }

def colecteaza_facturi_agregate(hass) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    domain_data = hass.data.get(DOMENIU, {}) if hasattr(hass, "data") else {}

    for maybe_coord in domain_data.values():
        if not isinstance(maybe_coord, CoordonatorUtilitatiRomania):
            continue

        if maybe_coord.intrare.data.get("furnizor") == FURNIZOR_ADMIN_GLOBAL:
            continue

        instantaneu = maybe_coord.data
        if not isinstance(instantaneu, InstantaneuFurnizor):
            continue

        # 1. Facturi reale, dacă există
        for factura in instantaneu.facturi or []:
            item = _build_invoice_item(maybe_coord, instantaneu, factura)

            # Pentru cardul de "ultima factură" ignorăm documentele de tip credit/storno.
            # Altfel, la unii furnizori (ex. myElectrica) putem afișa greșit un credit
            # în locul ultimei facturi reale de consum.
            if item.get("status") == "credit":
                continue

            group_key = (
                item["locatie_cheie"],
                normalize_text(item["furnizor"]).lower(),
            )

            current = grouped.get(group_key)
            if current is None or _sort_key_for_date(item.get("issue_date")) > _sort_key_for_date(current.get("issue_date")):
                grouped[group_key] = item

        # 2. Fallback specific E.ON din consumuri, doar pentru corectarea statusului curent
        if instantaneu.furnizor == "eon":
            for cont in instantaneu.conturi or []:
                fallback_item = _build_eon_fallback_item(maybe_coord, instantaneu, cont)
                if fallback_item is None:
                    continue

                group_key = (
                    fallback_item["locatie_cheie"],
                    normalize_text(fallback_item["furnizor"]).lower(),
                )

                current = grouped.get(group_key)

                if current is None:
                    grouped[group_key] = fallback_item
                    continue

                # Doar dacă fallback-ul spune clar că este neplătită, suprascriem statusul.
                # Dacă fallback-ul spune plătită, lăsăm itemul existent în pace,
                # pentru a nu strica situațiile deja corecte.
                if fallback_item.get("status") == "unpaid":
                    current["status_raw"] = fallback_item.get("status_raw")
                    current["status"] = "unpaid"
                    current["payment_status"] = "unpaid"
                    current["is_paid"] = False
                    current["unpaid_amount"] = fallback_item.get("unpaid_amount")
                    if fallback_item.get("due_date"):
                        current["due_date"] = fallback_item.get("due_date")
                    if fallback_item.get("issue_date"):
                        current["issue_date"] = fallback_item.get("issue_date")
                    if fallback_item.get("amount") is not None:
                        current["amount"] = fallback_item.get("amount")
                    if fallback_item.get("invoice_id"):
                        current["invoice_id"] = fallback_item.get("invoice_id")
                    if fallback_item.get("invoice_title"):
                        current["invoice_title"] = fallback_item.get("invoice_title")

        # 3. Fallback specific eBloc: dacă nu există facturi clasice, afișăm
        # întreținerea curentă sau ultima plată, în funcție de status.
        if instantaneu.furnizor == "ebloc":
            for cont in instantaneu.conturi or []:
                fallback_item = _build_ebloc_fallback_item(maybe_coord, instantaneu, cont)
                if fallback_item is None:
                    continue

                group_key = (
                    fallback_item["locatie_cheie"],
                    normalize_text(fallback_item["furnizor"]).lower(),
                )

                current = grouped.get(group_key)
                if current is None:
                    grouped[group_key] = fallback_item
                    continue

                # eBloc nu expune facturi clasice consistente; fallback-ul este sursa de adevăr.
                grouped[group_key] = fallback_item

    items = list(grouped.values())
    items.sort(
        key=lambda item: (
            normalize_text(item.get("eticheta_locatie")).lower(),
            normalize_text(item.get("furnizor_label")).lower(),
        )
    )
    return items


def sumar_facturi(items: list[dict[str, Any]]) -> dict[str, Any]:
    total_unpaid = 0.0
    grouped_locations: dict[str, dict[str, Any]] = {}

    for item in items:
        if item.get("status") == "unpaid":
            unpaid_amount = _to_float(item.get("unpaid_amount"))
            if unpaid_amount is not None and unpaid_amount > 0:
                total_unpaid += unpaid_amount

        location = grouped_locations.setdefault(
            item.get("locatie_cheie") or "locatie",
            {
                "locatie_cheie": item.get("locatie_cheie") or "locatie",
                "eticheta_locatie": item.get("eticheta_locatie") or "Locație",
                "furnizori": [],
            },
        )
        location["furnizori"].append(item)

    total = 0
    paid = 0
    unpaid = 0
    unknown = 0

    for location in grouped_locations.values():
        for item in location["furnizori"]:
            total += 1

            status = item.get("status")
            if status in {"paid", "credit"}:
                paid += 1
            elif status == "unpaid":
                unpaid += 1
            else:
                unknown += 1

    locations = list(grouped_locations.values())
    locations.sort(key=lambda loc: normalize_text(loc.get("eticheta_locatie")).lower())

    for location in locations:
        location["furnizori"].sort(
            key=lambda item: normalize_text(item.get("furnizor_label")).lower()
        )

        location_total_unpaid = 0.0
        for item in location["furnizori"]:
            if item.get("status") != "unpaid":
                continue
            unpaid_amount = _to_float(item.get("unpaid_amount"))
            if unpaid_amount is not None and unpaid_amount > 0:
                location_total_unpaid += unpaid_amount

        location_total_unpaid = round(location_total_unpaid, 2)
        location["total_neplatit"] = location_total_unpaid
        location["total_neplatit_formatat"] = f"{location_total_unpaid:.2f} RON"

    total_unpaid = round(total_unpaid, 2)

    return {
        "numar_facturi": total,
        "numar_platite": paid,
        "numar_neplatite": unpaid,
        "numar_necunoscute": unknown,
        "numar_status_necunoscut": unknown,
        "total_neplatit": total_unpaid,
        "total_neplatit_formatat": f"{total_unpaid:.2f} RON",
        "moneda": "RON",
        "locatii": locations,
    }
