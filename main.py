"""Forecast every market's Yes price in the next four hours using a volatility-scaled, no-drift quantile model normalized across mutually exclusive outcomes."""

import json
import math
import os


QUANTILES = ((0.05, -1.644854), (0.25, -0.539592), (0.5, 0.0), (0.75, 0.539592), (0.95, 1.644854))


def market_sigma(prices, x):
    """Compute clamped short-window absolute-change volatility for one market."""
    if len(prices) < 2:
        mean_abs = 0.0
    else:
        changes = [abs(prices[i + 1] - prices[i]) for i in range(max(0, len(prices) - 61), len(prices) - 1)]
        mean_abs = sum(changes) / len(changes)
    sigma = mean_abs + 0.003 * math.sqrt(x * (1.0 - x))
    return min(0.005, max(0.0002, sigma))


def main():
    input_dir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(output_dir, exist_ok=True)

    for filename in sorted(name for name in os.listdir(input_dir) if name.endswith(".in")):
        input_path = os.path.join(input_dir, filename)
        with open(input_path, "r", encoding="utf-8") as source:
            case = json.load(source)

        markets = case["markets"]
        last_prices = [market["prices"][-1] if market["prices"] else 0.0 for market in markets]
        price_sum = sum(last_prices)
        scale = 1.0 / price_sum if price_sum else 1.0
        horizon = case["horizon_minutes"]
        forecasts = []

        for market, x in zip(markets, last_prices):
            prices = market["prices"]
            sigma = market_sigma(prices, x)
            rows = []
            for h in range(1, horizon + 1):
                spread = sigma * math.sqrt(h)
                row = []
                for _, z in QUANTILES:
                    value = (x + z * spread) * scale
                    value = min(1.0, max(0.0, value))
                    rounded = round(value, 6)
                    row.append(0.0 if rounded == 0 else rounded)
                rows.append(row)
            forecasts.append({"id": market["id"], "q": rows})

        output_path = os.path.join(output_dir, f"{case['case']}.out")
        with open(output_path, "w", encoding="utf-8") as destination:
            json.dump({"forecasts": forecasts}, destination, separators=(",", ":"), allow_nan=False)


if __name__ == "__main__":
    main()
