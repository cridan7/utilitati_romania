from __future__ import annotations

from datetime import timedelta
import logging

from aiohttp import ClientSession
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_DIGI_COOKIES,
    CONF_FURNIZOR,
    CONF_INTERVAL_ACTUALIZARE,
    CONF_PAROLA,
    CONF_UTILIZATOR,
    DOMENIU,
)
from .exceptions import EroareAutentificare, EroareConectare, EroareLicenta
from .licentiere import async_salveaza_licenta_in_intrare, async_verifica_licenta, valideaza_rezultat_licenta
from .modele import InstantaneuFurnizor
from .furnizori.registru import obtine_clasa_furnizor

_LOGGER = logging.getLogger(__name__)


class CoordonatorUtilitatiRomania(DataUpdateCoordinator[InstantaneuFurnizor]):
    def __init__(self, hass: HomeAssistant, intrare: ConfigEntry) -> None:
        self.hass = hass
        self.intrare = intrare
        self.cheie_furnizor: str = intrare.data[CONF_FURNIZOR]
        self.sesiune: ClientSession = async_get_clientsession(hass)

        interval_ore = intrare.options.get(
            CONF_INTERVAL_ACTUALIZARE,
            intrare.data.get(CONF_INTERVAL_ACTUALIZARE, 6),
        )

        clasa_furnizor = obtine_clasa_furnizor(self.cheie_furnizor)
        self.client = clasa_furnizor(
            sesiune=self.sesiune,
            utilizator=intrare.options.get(CONF_UTILIZATOR, intrare.data[CONF_UTILIZATOR]),
            parola=intrare.options.get(CONF_PAROLA, intrare.data[CONF_PAROLA]),
            optiuni={**intrare.data, **intrare.options},
        )

        if self.cheie_furnizor == "digi":
            cookies = intrare.options.get(CONF_DIGI_COOKIES, intrare.data.get(CONF_DIGI_COOKIES, []))
            if hasattr(self.client, "importa_cookies"):
                self.client.importa_cookies(cookies)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMENIU}_{self.cheie_furnizor}",
            update_interval=timedelta(hours=interval_ore),
        )

    async def _async_update_data(self) -> InstantaneuFurnizor:
        try:
            rezultat_licenta = await async_verifica_licenta(self.hass, self.intrare)
            valideaza_rezultat_licenta(rezultat_licenta)
            await async_salveaza_licenta_in_intrare(self.hass, self.intrare, rezultat_licenta)
        except EroareLicenta as err:
            raise UpdateFailed(f"Licență invalidă: {err}") from err

        try:
            return await self.client.async_obtine_instantaneu()
        except EroareAutentificare as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except EroareConectare as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            raise UpdateFailed(f"Eroare neașteptată la {self.cheie_furnizor}: {err}") from err
