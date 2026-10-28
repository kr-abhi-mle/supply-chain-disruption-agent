# Sample outputs

Two contrasting scenarios, each run once with Gemini and once offline. Every folder holds the three
files a run produces: `report.md` (start here), `report.json` and `orders.csv` (one row per affected order).

| Folder | Scenario | Mode |
|---|---|---|
| [`sp_rain/`](sp_rain/report.md) | Large outbound region, short delay | Gemini |
| [`sp_rain_offline/`](sp_rain_offline/report.md) | Same | Offline |
| [`rs_flood/`](rs_flood/report.md) | Inbound into a state, long delay | Gemini |
| [`rs_flood_offline/`](rs_flood_offline/report.md) | Same | Offline |

The Gemini and offline reports for the same scenario have identical numbers. Only the wording of the
emails and the executive summary differs. `tests/test_pipeline_offline.py` checks that a fresh offline
run still reproduces the offline numbers here.

## What to look at first

1. **"How the system understood this"** at the top of each report: the parsed event and every assumption.
2. **Orders by action**, with the rule IDs R0 to R4.
3. **Sample customer emails**: compare `sp_rain` (Gemini) with `sp_rain_offline` (templates).
4. **One order traced end to end**: retrieval, severity reasons, rule, decision and email for one order.
5. **`orders.csv`**: open it in a spreadsheet and check any decision against its reasons.

## Commands that produced them

```bash
python cli.py "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days" --offline --out samples/sp_rain_offline
python cli.py "Flooding in Rio Grande do Sul is blocking deliveries into the state for 10 days" --offline --out samples/rs_flood_offline

GEMINI_MODEL=gemini-3.5-flash-lite python cli.py "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days" --out samples/sp_rain
GEMINI_MODEL=gemini-3.5-flash-lite python cli.py "Flooding in Rio Grande do Sul is blocking deliveries into the state for 10 days" --out samples/rs_flood
```

The Gemini samples used `gemini-3.5-flash-lite` because the free-tier daily quota for the default
`gemini-3.6-flash` was used up during development. The free tier allows 5 requests per minute, and a run
makes 5 calls, so wait a minute between Gemini runs.
