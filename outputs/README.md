# Run outputs

Each folder holds the three files one run produces: `report.md` (start here), `report.json` and
`orders.csv`, with one row per affected order and its rule and reasons. All five runs used Gemini mode.
Every number in them is identical to an offline run of the same query.

| Folder | Scenario | What it shows | Affected orders |
|---|---|---|---|
| [`curitiba_strike/`](curitiba_strike/report.md) | Truckers' strike in Curitiba, shipments out of the city stuck for a week | A city-level filter, outbound | 301 |
| [`rio_port_both_ways/`](rio_port_both_ways/report.md) | Port issues around Rio de Janeiro affecting shipments both ways for 3 days | Both directions: sellers or customers in the state | 1,557 |
| [`minas_gerais_electronics/`](minas_gerais_electronics/report.md) | Heavy rains in Minas Gerais are delaying electronics and computer shipments leaving the state for 4 days | A product focus from the query: the priority products are computer accessories | 678 |
| [`2026-10-29_025314_heavy-rains-are-delaying/`](2026-10-29_025314_heavy-rains-are-delaying/report.md) | Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days | Saved from the web app | 7,037 |
| [`2026-10-29_024554_flooding-in-rio-grande/`](2026-10-29_024554_flooding-in-rio-grande/report.md) | Flooding in Rio Grande do Sul is blocking deliveries into the state for 10 days | Saved from the web app | 466 |

The first three were produced with the CLI, one minute apart to stay within the Gemini free tier:

```bash
python cli.py "Truckers' strike in Curitiba, shipments out of the city stuck for a week" --out outputs/curitiba_strike
python cli.py "Port issues around Rio de Janeiro affecting shipments both ways for 3 days" --out outputs/rio_port_both_ways
python cli.py "Heavy rains in Minas Gerais are delaying electronics and computer shipments leaving the state for 4 days" --out outputs/minas_gerais_electronics
```

The main model, `gemini-3.6-flash`, was over its daily free-tier quota at the time, so the fallback model
`gemini-3.5-flash-lite` answered. Each report's run mode and notes say so. The web app saves every run to
this folder under a date and time. The curated samples for the two main scenarios, in both modes, are in
[`samples/`](../samples/README.md).
