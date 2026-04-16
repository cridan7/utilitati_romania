from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from ..exceptions import EroareAutentificare, EroareConectare
from ..modele import ConsumUtilitate, ContUtilitate, InstantaneuFurnizor
from .baza import ClientFurnizor
from .ebloc_api import ClientApiEbloc, EroareApiEbloc, EroareAutentificareEbloc

_LOGGER = logging.getLogger(__name__)
AMOUNT_DIVISOR = 100
INDEX_DIVISOR = 1000
INDEX_NOT_SET = -999999999


def _slug(text: str | None) -> str:
    baza = (text or '').lower()
    out = ''.join(ch if ch.isalnum() else '_' for ch in baza)
    while '__' in out:
        out = out.replace('__', '_')
    return out.strip('_') or 'necunoscut'


def _lista_dicturi(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _int(value: Any, default: int = 0) -> int:
    try:
        if value in (None, '', 'null'):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _lei(value: Any) -> float:
    return round(_int(value, 0) / AMOUNT_DIVISOR, 2)


def _m3(value: Any) -> float | None:
    brut = _int(value, INDEX_NOT_SET)
    if brut == INDEX_NOT_SET:
        return None
    return round(brut / INDEX_DIVISOR, 3)


def _data(value: Any) -> date | None:
    if value in (None, '', 'null'):
        return None
    text = str(value).strip().replace('/', '-')
    if 'T' in text:
        text = text.split('T', 1)[0]
    if ' ' in text:
        text = text.split(' ', 1)[0]
    parts = text.split('-')
    try:
        if len(parts) == 3 and len(parts[0]) == 4:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        if len(parts) == 3:
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
    except Exception:
        return None
    return None


def _citire_permisa(home: dict[str, Any]) -> str:
    start = _data(home.get('indecsi_start'))
    end = _data(home.get('indecsi_end'))
    today = datetime.now().date()
    if start and end:
        return 'Da' if start <= today <= end else 'Nu'
    if start:
        return 'Da' if today >= start else 'Nu'
    return 'Da' if str(home.get('can_edit_index', '0')) == '1' else 'Nu'


def _gaseste_asociatie(asociatii: list[dict[str, Any]], id_asoc: str) -> dict[str, Any]:
    for item in asociatii:
        if str(item.get('id') or '') == str(id_asoc):
            return item
    return {}


def _plateste_ap(plateste: dict[str, Any], id_ap: str) -> dict[str, Any]:
    for item in _lista_dicturi(plateste.get('aInfoAp')):
        if str(item.get('id_ap') or item.get('id') or '') == str(id_ap):
            return item
    return {}


class ClientFurnizorEbloc(ClientFurnizor):
    cheie_furnizor = 'ebloc'
    nume_prietenos = 'eBloc'

    def __init__(self, *, sesiune, utilizator: str, parola: str, optiuni: dict) -> None:
        super().__init__(sesiune=sesiune, utilizator=utilizator, parola=parola, optiuni=optiuni)
        self.api = ClientApiEbloc(sesiune, utilizator, parola)

    async def async_testeaza_conexiunea(self) -> str:
        try:
            await self.api.async_login()
            await self.api.async_autodescoperire()
        except EroareAutentificareEbloc as err:
            raise EroareAutentificare(str(err)) from err
        except EroareApiEbloc as err:
            raise EroareConectare(str(err)) from err
        return str(self.api.id_user or self.utilizator)

    async def async_obtine_instantaneu(self) -> InstantaneuFurnizor:
        try:
            data = await self.api.async_colecteaza_date()
        except EroareAutentificareEbloc as err:
            raise EroareAutentificare(str(err)) from err
        except EroareApiEbloc as err:
            raise EroareConectare(str(err)) from err

        conturi: list[ContUtilitate] = []
        consumuri: list[ConsumUtilitate] = []
        asociatii = _lista_dicturi(data.get('asociatii'))
        apartamente = data.get('apartamente') or {}
        home_ap_data = data.get('home_ap_data') or {}
        per_ap = data.get('per_apartament') or {}

        total_de_plata = 0.0
        total_wallet = 0.0
        total_tichete = 0
        total_apartamente = 0
        scadente: list[date] = []

        for id_asoc, lista_ap in apartamente.items():
            assoc = _gaseste_asociatie(asociatii, str(id_asoc))
            nume_asoc = str(assoc.get('nume') or f'Asociație {id_asoc}')
            home = home_ap_data.get(str(id_asoc), home_ap_data.get(id_asoc, {})) or {}
            scadenta = _data(home.get('data_scadenta'))
            if scadenta:
                scadente.append(scadenta)
            for ap in _lista_dicturi(lista_ap):
                id_ap = str(ap.get('id_ap') or ap.get('id') or '')
                if not id_ap:
                    continue
                total_apartamente += 1
                ap_key = f"{id_asoc}:{id_ap}"
                ap_data = per_ap.get(ap_key, {})
                plateste_info = _plateste_ap(ap_data.get('plateste', {}), id_ap)
                total_plata = _lei(plateste_info.get('total_plata', ap.get('total_plata')))
                wallet_sold = _lei((ap_data.get('wallet') or {}).get('sold'))
                nr_pers = _int(ap.get('nr_pers')) // INDEX_DIVISOR
                tichete = _lista_dicturi((ap_data.get('contact') or {}).get('aTickets'))
                total_tichete += len(tichete)
                total_de_plata += max(total_plata, 0.0)
                total_wallet += wallet_sold

                plati = _lista_dicturi((ap_data.get('plati') or {}).get('aChitante'))
                ultima_plata = plati[0] if plati else {}
                data_ultima_plata = _data(ultima_plata.get('data'))
                valoare_ultima_plata = _lei(ultima_plata.get('suma')) if ultima_plata else None

                idx_by_contor = {str(item.get('id_contor')): item for item in _lista_dicturi(((ap_data.get('contoare') or {}).get('aInfoIndex'))) if item.get('id_contor') is not None}
                contoare = []
                for contor_def in _lista_dicturi(((ap_data.get('contoare') or {}).get('aInfoContoare'))):
                    id_contor = str(contor_def.get('id_contor') or '')
                    if not id_contor:
                        continue
                    contor_val = idx_by_contor.get(id_contor, {})
                    index_actual = _m3(contor_val.get('index_nou'))
                    if index_actual is None:
                        index_actual = _m3(contor_val.get('index_vechi'))
                    tip_map = {'1': 'Apă rece', '2': 'Apă caldă', '3': 'Gaz', '4': 'Energie'}
                    item = {
                        'id_contor': id_contor,
                        'titlu': str(contor_def.get('titlu') or f'Contor {id_contor}'),
                        'slug': _slug(str(contor_def.get('titlu') or f'Contor {id_contor}')),
                        'tip_contor': tip_map.get(str(contor_def.get('tip') or ''), f"Tip {contor_def.get('tip') or ''}"),
                        'tip': str(contor_def.get('tip') or ''),
                        'index_actual': index_actual,
                        'index_nou': _m3(contor_val.get('index_nou')),
                        'editare_permisa': str(contor_val.get('can_edit_index', '0')) == '1',
                        'drept_editare': str(contor_val.get('right_edit_index', '0')) == '1',
                        'serie_contor': contor_val.get('seria') or '',
                        'eticheta_contor': contor_val.get('eticheta') or '',
                        'estimat': str(contor_val.get('estimat', '0')) == '1',
                    }
                    contoare.append(item)
                    if index_actual is not None:
                        consumuri.append(ConsumUtilitate(
                            cheie=f"index_{item['slug']}",
                            valoare=index_actual,
                            unitate='m³',
                            id_cont=ap_key,
                            tip_utilitate='intretinere',
                            tip_serviciu='administrare imobil',
                            date_brute=item,
                        ))

                restante_detalii = _lista_dicturi(plateste_info.get('aDatAp'))
                ticket_details = ap_data.get('ticket_details') or {}
                consumuri.extend([
                    ConsumUtilitate('de_plata', total_plata, 'RON', id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
                    ConsumUtilitate('sold_curent', total_plata, 'RON', id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
                    ConsumUtilitate('factura_restanta', 'Da' if total_plata > 0 else 'Nu', None, id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil', date_brute={'restante_detalii': restante_detalii, 'total': total_plata}),
                    ConsumUtilitate('arhiva_plati', min(len(plati), 12), None, id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil', date_brute={'plati': plati[:12]}),
                    ConsumUtilitate('numar_persoane', nr_pers, None, id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
                    ConsumUtilitate('numar_tichete', len(tichete), None, id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil', date_brute={'tichete': tichete, 'ticket_details': ticket_details}),
                    ConsumUtilitate('citire_permisa', _citire_permisa(home), None, id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil', date_brute={
                        'indecsi_start': home.get('indecsi_start'),
                        'indecsi_end': home.get('indecsi_end'),
                        'data_scadenta': home.get('data_scadenta'),
                        'can_edit_index': home.get('can_edit_index'),
                    }),
                    ConsumUtilitate('sold_wallet', wallet_sold, 'RON', id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
                    ConsumUtilitate('urmatoarea_scadenta', scadenta.isoformat() if scadenta else None, None, id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
                    ConsumUtilitate('asociatie', str(id_asoc), None, id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil', date_brute=assoc),
                ])
                if data_ultima_plata:
                    consumuri.append(ConsumUtilitate('data_ultima_plata', data_ultima_plata.isoformat(), None, id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil'))
                if valoare_ultima_plata is not None:
                    consumuri.append(ConsumUtilitate('valoare_ultima_plata', valoare_ultima_plata, 'RON', id_cont=ap_key, tip_utilitate='intretinere', tip_serviciu='administrare imobil'))

                conturi.append(ContUtilitate(
                    id_cont=ap_key,
                    nume=f"{nume_asoc} - Ap. {ap.get('ap') or ap.get('nr_ap') or id_ap}",
                    tip_cont='apartament',
                    id_contract=str(id_asoc),
                    adresa=_adresa_asociatie(assoc, ap) or f"{nume_asoc} - Ap. {ap.get('ap') or ap.get('nr_ap') or id_ap}",
                    stare='restant' if total_plata > 0 else 'activ',
                    tip_utilitate='intretinere',
                    tip_serviciu='administrare imobil',
                    date_brute={
                        'id_asoc': str(id_asoc),
                        'id_ap': id_ap,
                        'apartament': str(ap.get('ap') or ap.get('nr_ap') or id_ap),
                        'numar_apartament': str(ap.get('ap') or ap.get('nr_ap') or id_ap),
                        'nume_asociatie': nume_asoc,
                        'adresa': _adresa_asociatie(assoc, ap),
                        'asociatie_bruta': assoc,
                        'apartament_brut': ap,
                        'home': home,
                        'conturi_brute': ap_data.get('contoare') or {},
                        'facturi_brute': ap_data.get('facturi') or {},
                        'plati_brute': ap_data.get('plati') or {},
                        'plateste_brut': ap_data.get('plateste') or {},
                        'wallet_brut': ap_data.get('wallet') or {},
                        'contact_brut': ap_data.get('contact') or {},
                        'ticket_details': ticket_details,
                        'contoare': contoare,
                        'right_edit_nr_pers': str(ap.get('right_edit_nr_pers', '0')) == '1',
                        'numar_persoane_curent': nr_pers,
                    },
                ))

        if scadente:
            urm_scad = min(scadente).isoformat()
            consumuri.append(ConsumUtilitate('urmatoarea_scadenta', urm_scad, None, tip_utilitate='intretinere', tip_serviciu='administrare imobil'))
        consumuri.extend([
            ConsumUtilitate('numar_apartamente', total_apartamente, None, tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
            ConsumUtilitate('numar_asociatii', len(asociatii), None, tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
            ConsumUtilitate('numar_tichete', total_tichete, None, tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
            ConsumUtilitate('de_plata', round(total_de_plata, 2), 'RON', tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
            ConsumUtilitate('total_neachitat', round(total_de_plata, 2), 'RON', tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
            ConsumUtilitate('sold_curent', round(total_de_plata, 2), 'RON', tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
            ConsumUtilitate('sold_wallet', round(total_wallet, 2), 'RON', tip_utilitate='intretinere', tip_serviciu='administrare imobil'),
        ])

        _LOGGER.debug('[eBloc] Instantaneu generat: %s apartamente / %s asociații', total_apartamente, len(asociatii))
        return InstantaneuFurnizor(
            furnizor=self.cheie_furnizor,
            titlu=self.nume_prietenos,
            conturi=conturi,
            facturi=[],
            consumuri=consumuri,
            extra={
                'id_user': self.api.id_user,
                'numar_asociatii': len(asociatii),
                'numar_apartamente': total_apartamente,
                'luna': data.get('luna'),
            },
        )

def _extract_first_text(value: Any, preferred_keys: tuple[str, ...]) -> str | None:
    seen: set[int] = set()

    def _walk(node: Any) -> str | None:
        node_id = id(node)
        if node_id in seen:
            return None
        seen.add(node_id)

        if isinstance(node, dict):
            lowered = {str(k).lower(): v for k, v in node.items()}
            for key in preferred_keys:
                if key in lowered:
                    text = str(lowered[key] or '').strip()
                    if text and text.lower() not in {'null', 'none'}:
                        return text
            for value in node.values():
                found = _walk(value)
                if found:
                    return found
            return None

        if isinstance(node, list):
            for item in node:
                found = _walk(item)
                if found:
                    return found
            return None

        return None

    return _walk(value)


def _adresa_asociatie(asociatie: dict[str, Any], apartament: dict[str, Any]) -> str | None:
    preferred = (
        'adresa',
        'address',
        'full_address',
        'service_address',
        'street',
        'strada',
        'adr',
        'adres',
    )
    baza = _extract_first_text(apartament, preferred) or _extract_first_text(asociatie, preferred)
    ap = str(apartament.get('ap') or apartament.get('nr_ap') or apartament.get('apartament') or '').strip()
    if baza and ap:
        lower_baza = baza.lower()
        if f'ap. {ap.lower()}' in lower_baza or f'ap {ap.lower()}' in lower_baza:
            return baza
        return f"{baza} - Ap. {ap}"
    if baza:
        return baza
    return None

