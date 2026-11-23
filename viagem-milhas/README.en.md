# Flight Price Tracker

*Leia em: [Português](README.md)*

Tracks **every day** the price of a trip that **you choose** (destinations, dates, passengers, baggage and minimum layover), keeps the price history, **alerts you when the price drops** and when a **cheap miles promotion** shows up. It also compares cash vs miles and puts readings from other sites (Kayak, CVC, the airline, mileage programs) into one report.

It works for round trips and for **open-jaw trips** (e.g. arrive in Budapest, fly home from Berlin). A real case is in [docs/caso-de-uso-exemplo.md](docs/caso-de-uso-exemplo.md) (Portuguese).

## Getting started (Windows)

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
powershell -File scripts\setup.ps1          # wizard: asks about the trip and creates config.toml
```

1. **Create a free [SerpApi](https://serpapi.com) account** (250 queries/month) and store the key **only** in the user environment variable (never in a project file):
   `setx SERPAPI_KEY "YOUR_KEY"`, then reopen the terminal.
2. Run once: `powershell -File scripts\run_daily.ps1`
3. Schedule the daily run (08:00): `powershell -File scripts\register_task.ps1`

## What you choose

The wizard (`scripts\setup.ps1`) asks, and everything is saved in `config.toml` (commented template in [config.example.toml](config.example.toml)):

| Question | Key in `config.toml` |
|---|---|
| Origin, destination and outbound date | `[trip] outbound` |
| Where the return leaves from, where it lands and its date | `[trip] inbound` (can be another city) |
| Adult passengers and cabin | `[trip] adults`, `cabin` |
| Carry-on bags (per person) and checked bags per leg (and the price of one bag) | `[baggage] carry_on`, `checked`, `checked_bag_fee_brl` |
| Minimum layover (hours) | `[rules] min_layover_minutes` |
| Maximum layover you accept (hours; 0 = no limit) | `[rules] max_layover_minutes` |
| Airports where you won't accept a layover (optional) | `[rules] avoid_airports` |
| How much the price must drop, or a target price, to alert | `[alerts] drop_pct`, `target_brl` |

You can edit the file by hand at any time (UTF-8 with or without BOM is accepted, as Notepad saves it).

## Browser interface

Prefer clicking to typing? Install the extra and open the interface:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-app.txt
powershell -File scripts\app.ps1
```

On Windows you can simply **double-click `Abrir Verificador.bat`** (you can pin a shortcut to it on the desktop). The page opens by itself in the browser; to quit, close the black window that stays open.

| Tab | What it does |
|---|---|
| **Minha viagem** (My trip) | A form with every field (destinations, dates, passengers, baggage, minimum and maximum layover, alerts), with validation. It opens pre-filled with your current configuration |
| **Consultar agora** (Search now) | Runs the search right away, shows the best price, the difference from the previous consultation and every offer, and **saves the consultation** |
| **Consultas salvas** (Saved consultations) | Reopens any earlier consultation (the daily one or manual ones) and compares it with the previous one |
| **Histórico** (History) | Chart of the lowest price per day, the report (with the estimated bag cost) and the latest alerts |

The interface only touches local files (`config.toml` and `data/`); the daily routine keeps working without it.

## How it works (automatic part)

Every day the Windows Task Scheduler runs `scripts/run_daily.ps1`, which calls `verificador.run_daily`:

1. **Collect** (`collector.py`): queries SerpApi (Google Flights). The first call returns the **outbound** options; for each of the 3 cheapest outbounds that pass the rules, a second call with `departure_token` returns the **returns** and the **total price** for the group. At most **4 queries/day**. Carry-on bags are only sent with the search if you turn on `send_to_api` (off by default: Google's filter hides valid offers).
2. **Filter** (`rules.py`): drops offers with a layover below the minimum (or with unknown duration) or at airports you avoid, and keeps the cheapest.
3. **History** (`history.py`): one row per day in `data/history.csv`. Running twice on the same day does not duplicate it, and a failed run never overwrites a good price from that day. Each consultation is also **saved in full** in `data/snapshots/` (every offer, with layovers and whether it passes the rules), so you can review and compare it the next day.
4. **Alerts** (`alerts.py`): Windows notification + `data/alerts.log` when the price drops enough, **crosses below the target price** (only on the crossing, not every day), or the collection fails or comes back empty.
5. **Promotions** (`promos.py`): reads miles-blog feeds and alerts only when the quoted price per thousand miles is below the limit (Flying Blue, TAP, Livelo and Smiles, adjustable). Each post is alerted once.

## On-demand readings (manual part)

Kayak, CVC and mileage programs have bot protection or need a login, so they do not run on their own. When you (or an assistant) read a price there, record it:

```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe -m verificador.other_sources --source kayak --price 19152 --note "Light"
.venv\Scripts\python.exe -m verificador.other_sources --source "flying blue" --miles 502000 --taxes 3000
.venv\Scripts\python.exe -m verificador.report
```

The report shows Google Flights (the automatic series), the latest reading of each source, the lowest cash price, the **total with the estimated checked-bag cost** and the **break-even price per thousand miles** (the price below which miles beat cash).

## Commands

| What | Command |
|---|---|
| Configure the trip | `powershell -File scripts\setup.ps1` |
| Open the browser interface | `powershell -File scripts\app.ps1` |
| Run now | `powershell -File scripts\run_daily.ps1` |
| Register the daily task (08:00) | `powershell -File scripts\register_task.ps1` |
| Remove the task | `Unregister-ScheduledTask -TaskName VerificadorPassagens -Confirm:$false` |
| Combined report | `.venv\Scripts\python.exe -m verificador.report` (with `PYTHONPATH=src`) |
| Cash vs miles calculator | `.venv\Scripts\python.exe -m verificador.calculator --cash 19152 --miles 502000 --milheiro 30 --taxes 3000` |
| Tests | `.venv\Scripts\python.exe -m pytest -q` |

Data files (git-ignored): `config.toml`, `data/history.csv`, `data/snapshots/`, `data/outras_fontes.csv`, `data/seen_promos.json`, `data/alerts.log`.

## Limits and caveats

- Google Flights prices differ from other sites (different options and fares listed). Alerts apply to the Google Flights series.
- "Light" fares do not include a checked bag; the report adds an **estimate** (you provide the price of one bag).
- Miles are not checked automatically (each program needs a login); they come from the calculator, manual readings and the promotions watcher.
- If the blog feeds are down, only the promotions watcher goes quiet (the ticket price keeps being tracked).
- SerpApi limits and prices change; check their site. The key must never go into the repository.

Documents: design `docs/2026-11-23-verificador-passagens-design.md` · plan `docs/superpowers/plans/` · SerpApi notes `docs/spike-serpapi.md` (written in Portuguese for the original use case).
