# makefun-gta6-trophy-rarity-forecast-01

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/dockiemhiep/makefun-gta6-trophy-rarity-forecast-01/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/dockiemhiep/makefun-gta6-trophy-rarity-forecast-01/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

This entry forecasts GTA VI trophy earn rates from timestamped reads. Each output reports the 5th, 25th, 50th, 75th, and 95th percentiles for every trophy in input order.

The model skips null rates for each trophy. It runs deterministically on Python 3.13 with only the standard library.

- **Level.** Clamp rates to `0.01..99.99` percent, transform to logits, and take the mean of the last six available reads or all available reads if there are fewer. An empty series starts at the clamped-zero logit.
- **Measured drift.** Fit a weighted least-squares slope on each trophy's logit history using a one-day half-life. Use zero measured drift when the series cannot support a fit.
- **Launch-phase prior.** Blend the measured slope with a prior of `+0.35` logit per day. The prior carries the weight of one day of reads at the case's median positive cadence, or one quarter of the series weight if cadence is unknown. Measured drift gets most of the weight on long, regularly observed histories. The positive prior supports launch-week growth on short or flat histories.
- **Median.** Dampen the forecast horizon `H` in days with `H_eff = 2(1 - exp(-H/2))` and clamp the resulting median shift to `[-1.5, +2.0]` logits.
- **Spread.** Floor the weighted residual standard deviation at `0.25` and cap it at `0.9`, with `0.35` as the fallback when a fit is unavailable. Apply a walk floor of `0.30`, scale by the square root of `H`, and combine in quadrature with `0.30 * H_eff` for drift uncertainty.
- **Quantiles.** Apply the standard-normal z values `[-1.645, -0.674, 0, 0.674, 1.645]` on the logit scale, convert back to percentages, and round half-up to four decimals.

## Run it

```sh
MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---
<sub>Entered on [make.fun](https://make.fun/?ref=r027wqk6&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
