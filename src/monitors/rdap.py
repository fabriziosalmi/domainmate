"""
RDAP domain lookups (RFC 9083).

WHOIS speaks a line protocol on port 43, which is blocked in a great many
containers, CI runners and corporate networks, is rate-limited, and answers
with unstructured text that has to be parsed registrar by registrar. RDAP is
the IETF replacement: HTTPS on 443, so it survives a proxy, and structured
JSON, so there is nothing to guess at.

This module only reads a response. Deciding what to do when it fails belongs
to DomainMonitor, which falls back to WHOIS.
"""

from datetime import datetime, timezone
from typing import Optional

import requests

from src.constants import RDAP_BOOTSTRAP_URL, TIMEOUT_RDAP

#: RFC 9083 calls the expiry event "expiration"; a few servers use the older
#: spelling, so both are accepted.
_EXPIRY_ACTIONS = ("expiration", "expiry")


class RDAPError(Exception):
    """RDAP could not answer for this domain."""


def _parse_event_date(value: str) -> datetime:
    """
    Parse an RDAP eventDate. They are RFC 3339, but servers vary on the zone
    suffix and on sub-second precision.
    """
    text = str(value).strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _expiration_from(payload: dict) -> Optional[datetime]:
    for event in payload.get("events") or []:
        if not isinstance(event, dict):
            continue
        action = str(event.get("eventAction", "")).strip().lower()
        if action in _EXPIRY_ACTIONS and event.get("eventDate"):
            try:
                return _parse_event_date(event["eventDate"])
            except (ValueError, TypeError):
                continue
    return None


def _registrar_from(payload: dict) -> Optional[str]:
    """
    Pull the registrar's display name out of the entity carrying that role.

    The name lives in a jCard (RFC 7095): vcardArray is ["vcard", [entry, ...]]
    and each entry is [name, params, type, value], so the display name is the
    value of the "fn" entry.
    """
    for entity in payload.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        roles = [str(r).lower() for r in (entity.get("roles") or [])]
        if "registrar" not in roles:
            continue

        vcard = entity.get("vcardArray")
        if isinstance(vcard, list) and len(vcard) > 1 and isinstance(vcard[1], list):
            for entry in vcard[1]:
                if isinstance(entry, list) and len(entry) > 3 and entry[0] == "fn":
                    name = str(entry[3]).strip()
                    if name:
                        return name

        # Some registries omit the jCard and only carry a handle
        handle = entity.get("handle")
        if handle:
            return str(handle)
    return None


def lookup(domain: str, timeout: float = TIMEOUT_RDAP) -> dict:
    """
    Resolve a domain through the RDAP bootstrap and return
    ``{"expiration_date": datetime, "registrar": str | None}``.

    Raises RDAPError for anything that should send the caller to WHOIS: no
    RDAP server for the TLD, an unregistered domain, a transport failure, or a
    response with no expiration event.
    """
    url = f"{RDAP_BOOTSTRAP_URL}/domain/{domain}"
    try:
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,           # the bootstrap redirects to the registry
            headers={"Accept": "application/rdap+json, application/json"},
        )
    except requests.RequestException as e:
        raise RDAPError(f"request failed: {e}") from e

    if response.status_code == 404:
        raise RDAPError("no RDAP record for this domain")
    if response.status_code != 200:
        raise RDAPError(f"server returned HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as e:
        raise RDAPError(f"response was not JSON: {e}") from e

    if not isinstance(payload, dict):
        raise RDAPError("response was not an RDAP object")

    expiration = _expiration_from(payload)
    if expiration is None:
        raise RDAPError("response carried no expiration event")

    return {"expiration_date": expiration, "registrar": _registrar_from(payload)}
