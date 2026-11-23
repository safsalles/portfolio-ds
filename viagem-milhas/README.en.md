# Flight Price Tracker

*Leia em: [Português](README.md)*

Tracks the price of an **open-jaw trip: outbound GIG (Rio) → Budapest on 2027-07-10, return Berlin → GIG on 2027-07-22**, 2 adults, economy. The return does **not** leave from Budapest.

It runs by itself every day, keeps the price history, alerts when the price drops and when a cheap miles promotion shows up. Readings from other sites (Kayak, CVC, the airline site, mileage programs) are taken on demand and saved next to it, so everything can be compared in one report.

Documents: design `docs/2026-11-23-verificador-passagens-design.md` · plan `docs/superpowers/plans/2026-11-23-verificador-passagens.md` · SerpApi notes `docs/spike-serpapi.md`. (The design and plan are written in Portuguese.)

## Search rules

- **Layovers of at least 4 hours** on every connection, outbound and return (immigration time). This is the only layover rule.
- A "no layover in Brazil" rule existed at first and was **removed**: it was an assumption, never a requirement. To bring it back, list airports in `brazil_airports` in `config.toml`.
- Baggage: **2 carry-on + 1 checked bag** for the two travelers. "Light" fares do not include a checked bag, so add the bag price when comparing.
- A long stopover (~24h) in a nice city is only worth it if it costs **less than R$ 1,000** more than the best option without it.

## How it works (automatic part)

Every day at 08:00 the Windows Task Scheduler runs `scripts/run_daily.ps1`, which calls `verificador.run_daily`:

1. **Collect** (`collector.py`): queries SerpApi (Google Flights) for the open-jaw trip. The first call returns the **outbound** options; for each of the 3 cheapest outbounds that pass the rules, a second call with `departure_token` returns the **returns** and the **total price for both travelers**. At most **4 queries/day** (~120 of the 250 free queries/month).
2. **Filter** (`rules.py`): drops offers with a layover under 4h (or with unknown duration) and keeps the cheapest.
3. **History** (`history.py`): one row per day in `data/history.csv`. Running twice on the same day does not duplicate it, and a failed run never overwrites a good price from that day.
4. **Alerts** (`alerts.py`): Windows notification + `data/alerts.log` when the price drops **5% or more** since the previous day, **crosses below R$ 18,000** (only on the crossing, not every day), or the collection fails or comes back empty.
5. **Promotions** (`promos.py`): reads the feeds of two miles blogs and alerts only when the quoted price per thousand miles is below the limit (Flying Blue, TAP and Livelo < R$ 35; Smiles < R$ 12). Each post is alerted once.

Limits, target price, trip and feeds live in `config.toml`. The SerpApi key is read **only** from the `SERPAPI_KEY` user environment variable (never stored in a project file).

## On-demand readings (manual part)

Kayak, CVC and mileage programs have bot protection or need a login, so they do not run on their own. When asked to refresh, the assistant opens the site, reads the price and records it:

```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe -m verificador.other_sources --source kayak --price 19152 --note "KLM Light"
.venv\Scripts\python.exe -m verificador.other_sources --source "flying blue" --miles 502000 --taxes 3000
.venv\Scripts\python.exe -m verificador.report
```

The report shows Google Flights (the automatic series), the latest reading of each source, the lowest cash price and the **break-even price per thousand miles** (the price below which miles beat cash).

## Commands

| What | Command |
|---|---|
| Run now | `powershell -File scripts\run_daily.ps1` |
| Register the daily task (08:00) | `powershell -File scripts\register_task.ps1` |
| Remove the task | `Unregister-ScheduledTask -TaskName VerificadorPassagens -Confirm:$false` |
| Combined report | `.venv\Scripts\python.exe -m verificador.report` (with `PYTHONPATH=src`) |
| Cash vs miles calculator | `.venv\Scripts\python.exe -m verificador.calculator --cash 19152 --miles 502000 --milheiro 30 --taxes 3000` |
| Tests | `.venv\Scripts\python.exe -m pytest -q` |

Data files (git-ignored): `data/history.csv`, `data/outras_fontes.csv`, `data/seen_promos.json`, `data/alerts.log`.

## Snapshot on 2026-11-23 (reference)

| Source | Total for 2 | Note |
|---|---|---|
| **KLM Light** | **R$ 19,152** | Outbound 21:55 (7h in Amsterdam), return 06:00 (5h25 in Amsterdam). No checked bag |
| KLM Light + 1 bag per leg | ~R$ 20,350 to 20,650 | **Estimate**: bag ~US$ 100–120 per leg; exact price only shown at the end of booking |
| Lufthansa Economy Light | R$ 20,005 | Return with a 13h30–14h30 layover in Frankfurt |
| Google Flights (automatic series) | R$ 21,440 | Lists fewer options than Kayak; compare it only with its own previous day |
| CVC (Turkish, bag included) | R$ 20,035 | **Rejected**: 3h15 layover in Istanbul on the return |
| ~24h stopovers (London, Lisbon, Madrid) | R$ 22,189 to 24,826 | ≥ R$ 3k above the best option |
| Flying Blue (miles) | 502,000 miles + taxes | Break-even ≈ R$ 32 per thousand miles |
| Smiles (miles) | 3x+ Flying Blue | 330,500 to 360,700 miles per person, outbound only |

Conclusion that day: **paying cash for the KLM Light fare** is the best path; miles only win below ~R$ 30 per thousand.

## Limits and caveats

- Google Flights prices differ from Kayak's (different options and fares listed); alerts apply to the Google Flights series.
- Light fares do not include a checked bag; add the bag price before deciding.
- Miles are not checked automatically (each program needs a login); they come from the calculator, on-demand readings and the promotions watcher.
- If both blog feeds are down at once, only the promotions watcher goes quiet (the ticket price keeps being tracked).
- SerpApi limits and prices change; check their site before any paid plan.
