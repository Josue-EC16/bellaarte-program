"""Single-request factura.bo adapter. No DB, implicit retry or current-rate fallback."""
import asyncio
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
import re
import unicodedata
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

from app.services.exchange_rate_history_service import validate_rate


BASE_URL = "https://api.factura.bo"
MONTHS = dict(zip(("ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"), range(1, 13)))
WEEKDAYS = ("LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO")
DATE_PATTERN = re.compile(r"(LUNES|MARTES|MIERCOLES|JUEVES|VIERNES|SABADO|DOMINGO) (\d{1,2}) DE ([A-Z]+) DE (\d{4})")


class ProviderError(Exception):
    def __init__(self, state, http_code=None):
        super().__init__(state)
        self.state, self.http_code = state, http_code


@dataclass(frozen=True)
class ProviderQuote:
    value: Decimal
    http_code: int = 200


def _normalize(value):
    if not isinstance(value, str):
        raise ValueError("Text required")
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", value.upper()) if not unicodedata.combining(c)).split())


def _date(value):
    match = DATE_PATTERN.fullmatch(value)
    if not match:
        raise ValueError("Unrecognized validity")
    weekday, day, month, year = match.groups()
    result = date(int(year), MONTHS[month], int(day))
    if WEEKDAYS[result.weekday()] != weekday:
        raise ValueError("Contradictory weekday")
    return result


def validity_range(value):
    value = _normalize(value)
    if not value.startswith("VIGENCIA: "):
        raise ValueError("Missing validity")
    value = value[len("VIGENCIA: "):]
    if value.startswith("DEL "):
        first, last = value[4:].split(" AL ")
        first, last = _date(first), _date(last)
    else:
        first = last = _date(value)
    if first > last:
        raise ValueError("Reversed validity")
    return first, last


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def parse_quote(body: bytes, target: date, *, http_code=200) -> ProviderQuote:
    try:
        def invalid_constant(_value):
            raise ValueError("Nonfinite JSON number")
        payload = json.loads(body, parse_float=Decimal, parse_constant=invalid_constant, object_pairs_hook=_unique_object)
        if not isinstance(payload, dict) or payload.get("ok") is not True or payload.get("error") is not None:
            raise ValueError("Invalid envelope")
        data = payload["datos"]
        if (data["moneda_base"] != "BOB" or data["fuente_usd"] != "tco_publico"
                or _normalize(data["fuente"]) != "BANCO CENTRAL DE BOLIVIA"):
            raise ValueError("Unrecognized source")
        source = urlsplit(data["url_fuente"])
        if (source.scheme != "https" or source.hostname not in {"www.bcb.gob.bo", "bcb.gob.bo"}
                or source.port not in {None, 443} or source.username or source.password or source.query or source.fragment
                or source.path != "/bcb_tco_publico_ultima_cotizacion.php"):
            raise ValueError("Unrecognized BCB source")
        value = validate_rate(data["usd_bob"])
    except (ValueError, TypeError, KeyError, AttributeError, HTTPException, UnicodeError):
        raise ProviderError("ERROR_DATOS", http_code) from None
    try:
        first, last = validity_range(data.get("vigencia_usd"))
        if not first <= target <= last:
            raise ValueError("Requested day outside validity")
    except (ValueError, TypeError, KeyError):
        raise ProviderError("ERROR_VIGENCIA", http_code) from None
    return ProviderQuote(value, http_code)


class FacturaBoClient:
    def __init__(self, *, timeout_seconds=30, transport=None):
        self.timeout_seconds, self.transport = timeout_seconds, transport

    async def _fetch(self, target):
        timeout = httpx.Timeout(min(15, self.timeout_seconds), connect=min(5, self.timeout_seconds))
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False,
                transport=self.transport, headers={"Accept": "application/json", "User-Agent": "BAB-VDOS-USD-Sync/1.0"}) as client:
            async with client.stream("GET", BASE_URL + "/ExchangeRate/history/" + target.isoformat()) as response:
                if not 200 <= response.status_code <= 299:
                    raise ProviderError("ERROR_API", response.status_code)
                media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if media_type != "application/json":
                    raise ProviderError("ERROR_DATOS", response.status_code)
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 65536:
                        raise ProviderError("ERROR_DATOS", response.status_code)
                return parse_quote(bytes(body), target, http_code=response.status_code)

    def fetch(self, target):
        try:
            return asyncio.run(asyncio.wait_for(self._fetch(target), timeout=self.timeout_seconds))
        except ProviderError:
            raise
        except (httpx.RequestError, asyncio.TimeoutError):
            raise ProviderError("ERROR_CONEXION") from None
