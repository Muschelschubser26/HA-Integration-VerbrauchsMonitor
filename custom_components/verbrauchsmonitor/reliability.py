"""Extensible reliability aggregation for forecast quality.

Modules are registered by key and return a score (0..100), an influence weight,
and evidence metadata. Unavailable modules are omitted from aggregation. The
registry is intentionally open-ended: future modules do not require changes to
the aggregator or frontend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ReliabilityContribution:
    key: str
    score: float
    weight: float
    evidence: dict


Evaluator = Callable[[dict], ReliabilityContribution | None]
_REGISTRY: dict[str, Evaluator] = {}


def register_module(key: str, evaluator: Evaluator, *, replace: bool = False) -> None:
    """Register a named evaluator; arbitrary future module keys are supported."""
    normalized = str(key).strip().lower()
    if not normalized:
        raise ValueError("reliability module key must not be empty")
    if normalized in _REGISTRY and not replace:
        raise ValueError(f"reliability module already registered: {normalized}")
    _REGISTRY[normalized] = evaluator


def registered_modules() -> tuple[str, ...]:
    return tuple(_REGISTRY)


def evaluate_reliability(context: dict, *, module_keys: tuple[str, ...] | None = None) -> dict:
    """Evaluate available modules and return one deterministic percentage.

    A module's weight is its declared impact on the forecast, not a fixed 50/50
    split. Missing modules and unavailable evidence are excluded and remaining
    weights are normalized. No minimum score or fallback value is applied.
    """
    keys = module_keys if module_keys is not None else tuple(_REGISTRY)
    contributions = []
    for key in keys:
        normalized_key = str(key).strip().lower()
        evaluator = _REGISTRY.get(normalized_key)
        if evaluator is None:
            continue
        item = evaluator(context)
        if item is None or item.weight <= 0:
            continue
        if not 0 <= item.score <= 100:
            raise ValueError(f"reliability score out of range for {key}")
        contributions.append(item)
    total_weight = sum(item.weight for item in contributions)
    if total_weight <= 0:
        return {"available": False, "score": None, "modules": {}, "basis": "no_available_modules"}
    score = sum(item.score * item.weight for item in contributions) / total_weight
    return {
        "available": True,
        "score": round(score, 1),
        "modules": {
            item.key: {"score": round(item.score, 1), "weight": item.weight, **item.evidence}
            for item in contributions
        },
        "basis": "weighted_available_reliability_modules",
    }



def derive_impact_weights(forecast_result: dict) -> dict:
    """Derive module weights from monetary forecast components in euros.

    The energy module is weighted by the projected energy amount. The
    financial module is weighted by the complete projected financial exposure
    plus the account movements that change the expected settlement. This keeps
    the weighting data-dependent and avoids dropping module B merely because
    no advance or one-off booking exists yet.
    """
    def amount(key: str) -> float:
        value = forecast_result.get(key, 0)
        if value in (None, ""):
            return 0.0
        result = abs(float(value))
        if not result < float("inf"):
            return 0.0
        return result

    energy_impact = amount("forecast_energy_cost_total_eur")
    financial_impact = sum(amount(key) for key in (
        "annual_value_eur",
        "booked_advances_eur",
        "future_scheduled_advances_eur",
        "additional_payments_eur",
        "credits_eur",
        "corrections_eur",
    ))
    return {
        "forecast_impact_weight": energy_impact,
        "financial_impact_weight": financial_impact,
    }

def _module_a(context: dict) -> ReliabilityContribution | None:
    """Forecast quality: measured accuracy when ready, otherwise live context.

    Measurement history is optional. If absent, its component is not included.
    """
    measured = context.get("measured_forecast_score")
    # Freshness and configuration completeness are not forecast accuracy.
    # They remain useful diagnostic evidence, but cannot create a percentage.
    if measured is None:
        return None
    score = float(measured)
    basis = "forecast_vs_actual"
    # Weight expresses A's actual share of forecast impact supplied by caller.
    weight = max(0.0, float(context.get("forecast_impact_weight", 0.0)))
    return ReliabilityContribution("A", max(0.0, min(100.0, score)), weight,
                                    {"basis": basis, "history_included": measured is not None})


def _module_b(context: dict) -> ReliabilityContribution | None:
    """Financial forecast quality from available tariff, period and ledger data."""
    measured = context.get("measured_financial_score")
    # Tariff/period validity alone does not prove that a financial forecast was
    # accurate. Until forecast-to-settlement comparisons exist, omit module B.
    if measured is None:
        return None
    score = float(measured)
    weight = max(0.0, float(context.get("financial_impact_weight", 0.0)))
    return ReliabilityContribution("B", max(0.0, min(100.0, score)), weight,
                                    {"basis": "available_financial_factors"})


register_module("A", _module_a)
register_module("B", _module_b)



def environmental_reliability_factors(hass, meter_data: dict, now) -> dict:
    """Return quality factors for configured, fresh and plausible weather sensors.

    These are data-quality indicators, not assumed weather benefits. Missing
    optional entities are omitted. Numeric values are range-checked and stale
    readings lose evidence weight through a deterministic freshness score.
    """
    specifications = (
        ("outdoor_temperature_entity", "outdoor_temperature", -80.0, 65.0, 48.0),
        ("outdoor_illuminance_entity", "outdoor_illuminance", 0.0, 200000.0, 36.0),
        ("daily_precipitation_entity", "daily_precipitation", 0.0, 2000.0, 36.0),
        ("outdoor_humidity_entity", "outdoor_humidity", 0.0, 100.0, 48.0),
    )
    factors = {}
    for config_key, factor_key, minimum, maximum, freshness_hours in specifications:
        entity_id = meter_data.get(config_key)
        if not entity_id:
            continue
        state = hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", "none", ""):
            continue
        try:
            value = float(state.state.replace(",", "."))
        except (AttributeError, TypeError, ValueError):
            continue
        if not minimum <= value <= maximum:
            continue
        updated = state.last_updated
        if updated is None:
            continue
        age_hours = max(0.0, (now - updated).total_seconds() / 3600.0)
        factors[factor_key] = max(0.0, min(100.0, 100.0 * (1.0 - age_hours / freshness_hours)))
    # Wind direction may be a numeric azimuth or a cardinal/intercardinal label.
    entity_id = meter_data.get("outdoor_wind_direction_entity")
    if entity_id:
        state = hass.states.get(entity_id)
        if state is not None and state.state not in ("unknown", "unavailable", "none", ""):
            raw = str(state.state).strip().lower()
            valid = raw in {
                "n", "ne", "e", "se", "s", "sw", "w", "nw",
                "north", "northeast", "east", "southeast", "south",
                "southwest", "west", "northwest",
            }
            if not valid:
                try:
                    azimuth = float(raw.replace(",", "."))
                    valid = 0.0 <= azimuth < 360.0
                except ValueError:
                    valid = False
            if valid and state.last_updated is not None:
                age_hours = max(0.0, (now - state.last_updated).total_seconds() / 3600.0)
                factors["wind_direction"] = max(0.0, min(100.0, 100.0 * (1.0 - age_hours / 48.0)))
    return factors

