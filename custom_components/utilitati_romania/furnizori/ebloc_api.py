from __future__ import annotations

import hashlib
import logging
from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.e-bloc.ro/ajax"
READ_URL = "https://read.e-bloc.ro/ajax"
API_KEY = "58126855-ef70-4548-a35e-eca020c24570"
APP_VERSION = "8.90"
OS_VERSION = "14"
DEVICE_BRAND = "samsung"
DEVICE_MODEL = "SM-S928B"
DEVICE_TYPE = 1
API_TIMEOUT = 30
NR_PERS_MULTIPLIER = 1000
HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 14; SM-S928B Build/UP1A.231005.007)",
    "Accept": "application/json",
    "Accept-Language": "ro-RO,ro;q=0.9",
}


class EroareApiEbloc(Exception):
    pass


class EroareAutentificareEbloc(EroareApiEbloc):
    pass


def _pass_sha512(password: str) -> str:
    return hashlib.sha512(password.encode("utf-8")).hexdigest().zfill(128)


def _pass_complexity(password: str) -> int:
    has_letters = any(c.isalpha() for c in password)
    has_digits = any(c.isdigit() for c in password)
    return 2 if len(password) >= 8 and has_letters and has_digits else 1


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


class ClientApiEbloc:
    def __init__(self, session: ClientSession, email: str, password: str) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._pass_sha = _pass_sha512(password)
        self._pass_complexity = _pass_complexity(password)
        self._timeout = ClientTimeout(total=API_TIMEOUT)
        self.session_id: str | None = None
        self.id_user: int | None = None
        self.asociations: list[dict[str, Any]] = []
        self.apartamente: dict[str, list[dict[str, Any]]] = {}
        self.home_ap_data: dict[str, dict[str, Any]] = {}
        self.get_info_data: dict[str, Any] = {}
        self.luna_curenta: str = ""

    async def _api_get(self, endpoint: str, params: dict[str, Any], use_read_server: bool = False) -> dict[str, Any]:
        base = READ_URL if use_read_server else BASE_URL
        url = f"{base}/{endpoint}"
        payload = dict(params)
        payload["debug"] = 0
        try:
            async with self._session.get(url, params=payload, timeout=self._timeout, headers=HEADERS) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                return data if isinstance(data, dict) else {"result": "ERROR", "error": "Răspuns invalid"}
        except aiohttp.ClientError as err:
            raise EroareApiEbloc(str(err)) from err
        except Exception as err:
            raise EroareApiEbloc(str(err)) from err

    async def _api_post_json(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{BASE_URL}/{endpoint}"
        try:
            async with self._session.post(url, json=payload, timeout=self._timeout, headers={**HEADERS, "Content-Type": "application/json"}) as resp:
                resp.raise_for_status()
                data = await resp.json(content_type=None)
                return data if isinstance(data, dict) else {"result": "ERROR", "error": "Răspuns invalid"}
        except aiohttp.ClientError as err:
            raise EroareApiEbloc(str(err)) from err
        except Exception as err:
            raise EroareApiEbloc(str(err)) from err

    async def async_login(self) -> None:
        data = await self._api_get("AppLogin.php", {
            "key": API_KEY,
            "user": self._email,
            "pass_sha": self._pass_sha,
            "pass_complexity": self._pass_complexity,
            "app_version": APP_VERSION,
            "os_version": OS_VERSION,
            "device_brand": DEVICE_BRAND,
            "device_model": DEVICE_MODEL,
            "device_type": DEVICE_TYPE,
            "facebook_id": "",
            "google_id": "",
            "apple_id": "",
            "nume_user": "",
            "prenume_user": "",
            "facebook_access_token": "",
            "google_id_token": "",
        })
        if data.get("result") != "ok":
            raise EroareAutentificareEbloc(data.get("message") or "Autentificare eșuată")
        self.session_id = str(data.get("session_id") or "")
        try:
            self.id_user = int(data.get("id_user"))
        except Exception:
            self.id_user = None

    async def async_validate_session(self) -> bool:
        if not self.session_id:
            return False
        try:
            data = await self._api_get("AppGetInfo.php", {"session_id": self.session_id})
        except EroareApiEbloc:
            return False
        return data.get("result") == "ok"

    async def async_ensure_authenticated(self) -> None:
        if self.session_id and await self.async_validate_session():
            return
        await self.async_login()

    async def async_autodescoperire(self) -> None:
        await self.async_ensure_authenticated()
        data = await self._api_get("AppGetInfo.php", {"session_id": self.session_id})
        if data.get("result") != "ok":
            raise EroareApiEbloc("AppGetInfo eșuat")
        self.get_info_data = data
        self.asociations = _as_dict_list(data.get("aInfoAsoc"))
        self.apartamente = {}
        self.home_ap_data = {}
        self.luna_curenta = ""
        for assoc in self.asociations:
            id_asoc = str(assoc.get("id") or "")
            if not id_asoc:
                continue
            ap_data = await self._api_get("AppHomeGetAp.php", {"session_id": self.session_id, "id_asoc": id_asoc})
            if ap_data.get("result") != "ok":
                continue
            self.apartamente[id_asoc] = _as_dict_list(ap_data.get("aInfoAp"))
            self.home_ap_data[id_asoc] = {
                "right_email": ap_data.get("right_email", "0"),
                "right_global_edit_users": ap_data.get("right_global_edit_users", "0"),
                "right_edit_users": ap_data.get("right_edit_users", "0"),
                "can_edit_index": ap_data.get("can_edit_index", "0"),
                "indecsi_start": ap_data.get("indecsi_start", ""),
                "indecsi_end": ap_data.get("indecsi_end", ""),
                "luna": ap_data.get("luna", ""),
                "luna_start": ap_data.get("luna_start", ""),
                "luna_end": ap_data.get("luna_end", ""),
                "data_scadenta": ap_data.get("data_scadenta", ""),
                "plata_card": ap_data.get("plata_card", "0"),
            }
            if not self.luna_curenta:
                self.luna_curenta = str(ap_data.get("luna") or "")

    async def async_get_contoare_index(self, id_asoc: str | int, luna: str) -> dict[str, Any]:
        return await self._api_get("AppContoareGetIndex.php", {"session_id": self.session_id, "id_asoc": id_asoc, "luna": luna})

    async def async_get_facturi(self, id_asoc: str | int, id_ap: str | int, luna: str) -> dict[str, Any]:
        return await self._api_get("AppFacturiGetData.php", {"session_id": self.session_id, "id_asoc": id_asoc, "id_ap": id_ap, "luna": luna})

    async def async_get_contact_tickets(self, id_asoc: str | int, id_ap: str | int) -> dict[str, Any]:
        return await self._api_get("AppContactGetTickets.php", {"session_id": self.session_id, "id_asoc": id_asoc, "id_ap": id_ap, "this_user": 1})

    async def async_get_ticket_detail(self, id_ticket: str | int) -> dict[str, Any]:
        return await self._api_get("AppContactGetTicketData.php", {"session_id": self.session_id, "id_ticket": id_ticket})

    async def async_get_istoric_plati(self, id_asoc: str | int, id_ap: str | int) -> dict[str, Any]:
        return await self._api_get("AppIstoricPlatiGetPlati.php", {"session_id": self.session_id, "id_asoc": id_asoc, "id_ap": id_ap})

    async def async_get_wallet(self, id_asoc: str | int, id_ap: str | int) -> dict[str, Any]:
        return await self._api_get("AppHomeGetWalletItems.php", {"session_id": self.session_id, "id_asoc": id_asoc, "id_ap": id_ap})

    async def async_get_plateste_ap(self, id_asoc: str | int, id_ap: str | int) -> dict[str, Any]:
        return await self._api_get("AppPlatesteGetAp.php", {"session_id": self.session_id, "id_asoc": id_asoc, "id_ap": id_ap})

    async def async_set_nr_persoane(self, id_asoc: str | int, id_ap: str | int, luna: str, nr_pers: int) -> dict[str, Any]:
        if nr_pers < 0 or nr_pers > 10:
            return {"result": "ERROR", "error": "nr_pers invalid"}
        return await self._api_get("AppHomeSetNrPers.php", {
            "session_id": self.session_id,
            "id_asoc": id_asoc,
            "id_ap": id_ap,
            "luna": luna,
            "nr_pers": nr_pers * NR_PERS_MULTIPLIER,
        })

    async def async_set_index_contoare(self, indexes: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "session_id": self.session_id,
            "aIndex": [
                {
                    "id_asoc": item["id_asoc"],
                    "id_ap": item["id_ap"],
                    "id_contor": item["id_contor"],
                    "index_nou": item["index_nou"],
                    "img_data": "",
                    "img_guid": "",
                }
                for item in indexes
            ],
        }
        return await self._api_post_json("AppContoareSetIndexes.php", payload)

    async def async_colecteaza_date(self) -> dict[str, Any]:
        await self.async_autodescoperire()
        data: dict[str, Any] = {
            "get_info": self.get_info_data,
            "asociatii": self.asociations,
            "apartamente": self.apartamente,
            "home_ap_data": self.home_ap_data,
            "luna": self.luna_curenta,
            "per_apartament": {},
        }
        for id_asoc, lista_ap in self.apartamente.items():
            luna = str((self.home_ap_data.get(str(id_asoc)) or {}).get("luna") or self.luna_curenta or "")
            contoare = await self.async_get_contoare_index(id_asoc, luna)
            contoare_idx = {str(item.get("id_contor")): item for item in _as_dict_list(contoare.get("aInfoIndex")) if item.get("id_contor") is not None}
            contoare_def = _as_dict_list(contoare.get("aInfoContoare"))
            contact_cache: dict[str, dict[str, Any]] = {}
            for ap in lista_ap:
                id_ap = str(ap.get("id_ap") or ap.get("id") or "")
                if not id_ap:
                    continue
                plati = await self.async_get_istoric_plati(id_asoc, id_ap)
                wallet = await self.async_get_wallet(id_asoc, id_ap)
                plateste = await self.async_get_plateste_ap(id_asoc, id_ap)
                facturi = await self.async_get_facturi(id_asoc, id_ap, luna)
                contact = await self.async_get_contact_tickets(id_asoc, id_ap)
                ticket_details: dict[str, dict[str, Any]] = {}
                for ticket in _as_dict_list(contact.get("aTickets"))[:5]:
                    tid = str(ticket.get("id_ticket") or ticket.get("id") or "")
                    if not tid:
                        continue
                    if tid not in contact_cache:
                        try:
                            contact_cache[tid] = await self.async_get_ticket_detail(tid)
                        except Exception:
                            contact_cache[tid] = {}
                    ticket_details[tid] = contact_cache[tid]
                ainfo = _as_dict_list(contoare.get("aInfoAp"))
                ap_contoare = next((item for item in ainfo if str(item.get("id_ap") or item.get("id") or "") == id_ap), {})
                data["per_apartament"][f"{id_asoc}:{id_ap}"] = {
                    "contoare": {
                        "aInfoAp": ap_contoare,
                        "aInfoContoare": contoare_def,
                        "aInfoIndex": list(contoare_idx.values()),
                    },
                    "plati": plati,
                    "wallet": wallet,
                    "plateste": plateste,
                    "facturi": facturi,
                    "contact": contact,
                    "ticket_details": ticket_details,
                }
        return data
