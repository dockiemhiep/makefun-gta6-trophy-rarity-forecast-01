"""Forecast GTA VI trophy earn-rate quantiles from launch-week reads."""

import json
import math
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

PRIOR_DRIFT = 0.35
WALK_FLOOR = 0.30
DRIFT_SIGMA = 0.30
RESID_FLOOR = 0.25
RESID_CAP = 0.9
RESID_FALLBACK = 0.35

# The grader uses -P, which leaves the script's directory off the import path.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0, 0.674, 1.645]


def clamp_pct(percent: float) -> float:
    return min(99.99, max(0.01, percent))


def logit(percent: float) -> float:
    percent = clamp_pct(percent)
    return math.log(percent / (100 - percent))


def inv_logit(value: float) -> float:
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1 + exp_value)


def round4(value: float) -> float | int:
    """Round half up to four decimal places, returning whole values as ints."""
    scaled = value * 10_000
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    rounded = whole / 10_000
    return int(rounded) if rounded.is_integer() else rounded


def series_stats(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    """Return the level, measured drift, residual sigma, and total read weight."""
    if not points:
        return logit(0.01), 0.0, RESID_FALLBACK, 0.0

    recent = points[-6:]
    level = sum(value for _, value in recent) / len(recent)
    last_time = points[-1][0]
    weights = [0.5 ** (last_time - time) for time, _ in points]
    weight_sum = sum(weights)
    if len(points) < 3 or last_time <= points[0][0]:
        return level, 0.0, RESID_FALLBACK, weight_sum

    time_mean = sum(weight * time for weight, (time, _) in zip(weights, points)) / weight_sum
    value_mean = sum(weight * value for weight, (_, value) in zip(weights, points)) / weight_sum
    denominator = sum(weight * (time - time_mean) ** 2 for weight, (time, _) in zip(weights, points))
    if denominator <= 0:
        return level, 0.0, RESID_FALLBACK, weight_sum

    numerator = sum(
        weight * (time - time_mean) * (value - value_mean)
        for weight, (time, value) in zip(weights, points)
    )
    drift = numerator / denominator
    intercept = value_mean - drift * time_mean
    residual_variance = sum(
        weight * (value - (intercept + drift * time)) ** 2
        for weight, (time, value) in zip(weights, points)
    ) / weight_sum
    residual_sigma = min(RESID_CAP, max(RESID_FLOOR, math.sqrt(residual_variance)))
    return level, drift, residual_sigma, weight_sum


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")

    horizon = case["horizon_minutes"] / 1440.0
    effective_horizon = -2.0 * math.expm1(-horizon / 2.0)
    reads = []
    for read in case["history"]:
        instant = datetime.fromisoformat(read["at"])
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
        reads.append((instant.timestamp() / 86_400, read["rates"]))

    gaps = [
        later - earlier
        for (earlier, _), (later, _) in zip(reads, reads[1:])
        if later > earlier
    ]
    cadence_weight = None
    if gaps:
        cadence = median(gaps)
        reads_per_day = max(1, round(1.0 / cadence))
        # Sum the geometric series in constant time, even for very short cadences.
        log_decay = math.log(0.5) * cadence
        cadence_weight = math.expm1(reads_per_day * log_decay) / math.expm1(log_decay)

    rows = []
    for index, trophy in enumerate(case["trophies"]):
        points = [(time, logit(rates[index])) for time, rates in reads if rates[index] is not None]
        level, measured_drift, residual_sigma, weight_sum = series_stats(points)
        prior_weight = 0.25 * weight_sum if cadence_weight is None else cadence_weight
        total_weight = weight_sum + prior_weight
        drift = PRIOR_DRIFT
        if total_weight:
            drift = (weight_sum * measured_drift + prior_weight * PRIOR_DRIFT) / total_weight

        location = level + min(2.0, max(-1.5, drift * effective_horizon))
        walk_sigma = max(residual_sigma, WALK_FLOOR)
        spread = math.sqrt(walk_sigma**2 * horizon + (DRIFT_SIGMA * effective_horizon) ** 2)
        quantiles = [round4(100 * inv_logit(location + z * spread)) for z in Z]
        rows.append({"id": trophy["id"], "q": quantiles})
    return {"trophies": rows}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        output = json.dumps(forecast, separators=(",", ":")) + "\n"
        (OUTPUT_DIR / f"{path.stem}.out").write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
