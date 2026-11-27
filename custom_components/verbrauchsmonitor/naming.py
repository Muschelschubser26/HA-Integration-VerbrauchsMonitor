"""Stable Home Assistant object-id helpers."""
from __future__ import annotations
import re
import unicodedata

_TRANSLITERATION = str.maketrans({"ä":"a", "ö":"o", "ü":"u", "Ä":"a", "Ö":"o", "Ü":"u", "ß":"ss"})

def slugify_meter_name(name: str) -> str:
    """Convert configured meter name to a stable, HA-safe ASCII slug."""
    value = str(name or "").translate(_TRANSLITERATION).casefold()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value or "stromzahler"

def balance_entity_ids(name: str, *, feed_in: bool) -> dict[str, str]:
    """Return balance entity IDs derived from the configured meter name."""
    slug = slugify_meter_name(name)
    result = {"consumption": f"sensor.verbrauchsmonitor_{slug}_verbrauch_kontostand"}
    if feed_in:
        result["feed_in"] = f"sensor.verbrauchsmonitor_{slug}_einspeisung_kontostand"
    return result


def meter_entity_object_ids(name: str) -> dict[str, str]:
    """Return canonical entity object IDs for all meter measurement roles."""
    slug = slugify_meter_name(name)
    prefix = f"verbrauchsmonitor_{slug}"
    return {
        "consumption_counter": f"{prefix}_verbrauch_zaehlerstand",
        "consumption_power": f"{prefix}_verbrauch_leistung",
        "feed_in_counter": f"{prefix}_einspeisung_zaehlerstand",
        "feed_in_power": f"{prefix}_einspeisung_leistung",
        "consumption_balance": f"{prefix}_verbrauch_kontostand",
        "feed_in_balance": f"{prefix}_einspeisung_kontostand",
        "consumption_today": f"{prefix}_tagesverbrauch",
        "feed_in_today": f"{prefix}_tageseinspeisung",
        "consumption_week": f"{prefix}_wochenverbrauch",
        "consumption_month": f"{prefix}_monatsverbrauch",
        "consumption_year": f"{prefix}_jahresverbrauch",
        "feed_in_week": f"{prefix}_wocheneinspeisung",
        "feed_in_month": f"{prefix}_monatseinspeisung",
        "feed_in_year": f"{prefix}_jahreseinspeisung",
    }
