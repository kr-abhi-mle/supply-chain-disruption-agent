# Implementation Plan

How we will build the system described in [ARCHITECTURE.md](ARCHITECTURE.md), step by step.
Each phase ends with a "done when" check, so progress is easy to verify.

The "done when" checks are covered by the test suite, which runs with `make test` or `python tasks.py test`.

Two goals shape this plan:

1. **Every output the case study asks for is produced by the system,** not written by hand.
2. **A reviewer can run and test everything without an LLM key** and without downloading the Kaggle data.
   The LLM makes the wording better. It never changes the numbers.

---

## 1. Deliverables and outputs

### 1.1 What the case study asks for, and where it comes from

| Case study asks for | What the reviewer sees | Produced by | Without an LLM |
|---|---|---|---|
| Take a disruption query in plain English | "How the system understood this": type, states or cities, direction, days, interpretation, assumptions | Disruption Parser | Rule-based parser fills the same fields |
| RAG: find the **specific orders** affected | Affected order count, and every order in `orders.csv` | Retrieval Agent, metadata filter | Same. Embeddings run locally |
| RAG: find **heavy or bulky products** such as furniture and home goods | "Priority products" table: SKU, category, weight, volume, why it is listed | Retrieval Agent, semantic search, plus the bulky flag | Same |
| RAG: find the **sellers** affected | Affected seller count and the "most affected sellers" table | Retrieval Agent and Report Writer | Same |
| Logistics Analyst: delayed orders and **severity from weight and SLA** | Severity breakdown, and plain-English reasons for each order | Logistics Analyst, pure Python | Same |
| Mitigation Agent: **cancel, reroute or delay** by product type | Action breakdown with rule IDs, and a rule and reason for each order | Mitigation Agent, rule table | Same |
| Customer Success Agent: **personalized, empathetic email** with a specific resolution | One sample email per action type, labelled "Gemini" or "Template" | Customer Success Agent | Hand-written template with the same facts |
| **Multi-step reasoning** from the disruption to SKUs to a customer action | One order traced end to end, plus the step trace with counts and timings | Pipeline and `render.py` | Same |
| **Impact summary** | Executive summary and headline numbers | Report Writer | Template summary built from the same numbers |
| **Interface** to enter a scenario and see the summary and an email | `cli.py` and the Streamlit app | Phase 7 | `--offline` flag and a toggle in the app |
| **Samples** for 1 to 2 scenarios | `samples/`: two scenarios, each run with Gemini and offline | The CLI | The offline samples can be regenerated exactly |
| Source code, local run steps, **Dockerized** | `Dockerfile`, `docker-compose.yml`, README quick start | Phase 8 | Runs with no `.env` file |
| README: architecture, reasoning, decisions and tradeoffs, assumptions | `README.md`, which links to `ARCHITECTURE.md` | Phase 8 | Not applicable |

### 1.2 What every run produces

The CLI with `--out DIR` and the app's download buttons write three files.

- **`report.md`**, the human-readable report. Its sections are:
  1. The query and the run mode, either Gemini with its model name or offline.
  2. How the system understood the query: the parsed event, the interpretation sentence and every default applied.
  3. The executive summary and the recommended next steps for operations.
  4. Headline numbers: affected orders, items, sellers and customers, percentage late, value at risk and compensation cost.
  5. Orders by severity, and the mitigation plan: per rule, its trigger, the customer offer, the number of
     orders, the average days late without and with the action, and the cost. Then the orders flagged for
     human review, with a note on each.
  6. Priority products: the bulky items and the best semantic matches for the product focus.
  7. The most affected sellers and categories.
  8. Sample customer emails, one per action type, each labelled with how it was written.
  9. One order traced end to end: retrieval match, severity reasons, rule, decision and email.
  10. The step trace, and notes on any LLM step that fell back to code.
- **`report.json`** holds the same content in machine-readable form. It leaves out the full order list,
  because the SP scenario alone has about 7,000 orders.
- **`orders.csv`** has one row for every affected order. The columns are order ID, customer city and
  state, categories, promised date, new ETA, days late, severity, action, rule ID, resolution, final ETA,
  compensation and reasons. A reviewer can open it in a spreadsheet and check any decision.

---

## 2. Running without an LLM

### 2.1 Two run modes, same numbers

| Mode | When it is used | Parser | Emails and summary |
|---|---|---|---|
| **Gemini** | `GEMINI_API_KEY` is set. A free key from Google AI Studio is enough | Gemini structured output. The rule-based parser takes over if Gemini fails | Gemini. A template takes over if Gemini fails |
| **Offline** | No key, or `LLM_MODE=offline`, or the CLI `--offline` flag, or the app toggle | Rule-based parser | Templates |

Everything between parsing and writing is identical in both modes: retrieval with local embeddings,
severity, decisions and every number. The report always says which mode ran and which steps fell back.

### 2.2 What is committed so a reviewer needs no setup

- **`data/processed/order_items.csv`** (5.7 MB, 11,301 rows) is committed. A reviewer does not need a Kaggle
  account. `src/data_prep.py` can still rebuild it from the raw CSVs. The Olist data is CC BY-NC-SA 4.0, and
  the README credits it.
- **`samples/`** holds the reports for both scenarios in both modes. A reviewer with no key can still read
  real Gemini output.
- The vector index is **not** committed. It is binary and about 60 MB. It takes one command to build locally,
  and the Docker image builds it automatically.

### 2.3 Reviewer paths

| Reviewer has | Commands |
|---|---|
| macOS or Linux, no key | `make setup`, then `make offline`, `make app` and `make test` |
| Windows, no key | `py tasks.py setup`, then `py tasks.py offline`, `py tasks.py app` and `py tasks.py test` |
| Python 3.11, setting up by hand | `pip install -r requirements.txt`, `python -m src.build_index`, then `python cli.py "<query>" --offline` and `pytest` |
| Docker, no key | `docker compose up --build` (or `make docker`), then open http://localhost:8501 |
| A Gemini key | Paste `GEMINI_API_KEY` into `.env` (setup creates it), check with `make check-key`, then use any path above without `--offline` |
| The raw Kaggle CSVs | Put them in `raw_data/`, then run `python -m src.data_prep` before building the index |

The first index build needs internet once, to download the 80 MB embedding model. The Docker image
downloads it at build time.

`tasks.py` holds every setup and run task in plain standard-library Python, so the same commands work
on Windows, macOS and Linux. The `Makefile` is only a shortcut to it. Setup uses uv when it is installed,
which also downloads Python 3.11, and the standard venv and pip otherwise. Each step is skipped when it
is already done. Tested on macOS from scratch, with uv and without it.

---

## 3. Tech stack

| Purpose | Library | Version |
|---|---|---|
| Data wrangling | pandas | 2.3.3 |
| Vector store | chromadb | 1.5.9 |
| Local embeddings | built into chromadb (all-MiniLM-L6-v2 on onnxruntime) | with chromadb |
| LLM calls (Gemini REST API) | httpx | 0.28.1 |
| Data contracts | pydantic | 2.13.5 |
| Config from `.env` | python-dotenv | 1.2.1 |
| Web UI | streamlit | 1.50.0 |
| Tests | pytest | 8.4.2 |

- **LLM:** Gemini, with the model set by `GEMINI_MODEL` (default `gemini-3.6-flash`). It was tested with the
  project's key: it returns valid `DisruptionEvent` JSON for the sample queries. The free tier is enough for
  a demo, at about five calls per run, but only a few runs per day (see the limits below).
- **Why plain REST and no SDK:** the code needs two calls, structured JSON and plain text. One visible
  `httpx.post` is easier to read than an SDK, and httpx is already installed with chromadb. Only `llm.py`
  talks to Gemini, so switching to another provider later changes one file.
- **Free-tier behaviour seen in testing:**
  - Gemini often answers 503 "high demand", so retries are required.
  - The free tier allows 5 requests per minute per model (`gemini-3.6-flash`). One run with three emails
    uses exactly 5 calls, so a second Gemini run within a minute gets HTTP 429 and falls back to templates.
    Wait a minute between Gemini runs, for example when generating samples.
  - The free tier also allows only 20 requests per day per model, about four full runs. Quotas are per
    model, so `GEMINI_MODEL=gemini-3.5-flash-lite` gives a fresh quota. It was tested and parses the
    phase 3 table correctly.
  - It takes 3 to 11 seconds per call.
  - `gemini-2.5-flash` is retired for new keys.
  - `gemini-3.5-flash` is quietly served by 3.6.
- **Embeddings:** Chroma's built-in `all-MiniLM-L6-v2` runs locally and needs no key.
- **Python:** 3.11, both locally and in Docker.

---

## 4. Project structure

```text
supply-chain-casestudy/
├── raw_data/                     # Olist CSVs (optional, gitignored)
├── data/
│   ├── processed/order_items.csv # committed: the 10k-order subset
│   └── chroma/                   # generated index, gitignored
├── src/
│   ├── config.py                 # paths, LLM mode, thresholds, policies
│   ├── models.py                 # Pydantic data contracts shared by all agents
│   ├── llm.py                    # Gemini helpers: parse(), text(), with retries
│   ├── data_prep.py              # build the 10k-order item table
│   ├── build_index.py            # embed items into Chroma
│   ├── agents/
│   │   ├── disruption_parser.py  # Gemini parser and the shared validation
│   │   ├── rule_parser.py        # rule-based parser, used offline and as the fallback
│   │   ├── retrieval_agent.py
│   │   ├── logistics_analyst.py
│   │   ├── mitigation_agent.py
│   │   ├── customer_success.py   # Gemini email and template email
│   │   └── report_writer.py      # stats, Gemini summary and template summary
│   ├── pipeline.py               # orchestrator
│   └── render.py                 # report.md, report.json, orders.csv
├── cli.py                        # command-line entry point
├── tasks.py                      # setup and run tasks for every OS
├── Makefile                      # macOS and Linux shortcuts to tasks.py
├── app.py                        # Streamlit entry point
├── tests/
├── samples/                      # committed example outputs, both modes
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_CONTRACT.md
│   ├── DESIGN_DECISIONS.md
│   └── IMPLEMENTATION_PLAN.md
└── README.md
```

## 5. Coding conventions (keep it simple)

- Plain functions. Classes only for Pydantic data models.
- Each agent file exposes one `run(...)` function with a typed input and output.
- No agent framework. The orchestrator is a readable sequence of function calls.
- Every number or policy that someone might change lives in `config.py`.
- Short files, short functions, and a docstring at the top of each file saying what it does.
- Agents never call Gemini directly. They go through `llm.py`.
- **The offline path is a first-class path, not an error handler.** The rule-based parser and the templates
  get the same care and the same tests as the LLM path, because some reviewers will only ever see them.

---

## 6. Phases

### Phase 0: Project setup

- [x] `requirements.txt` with pinned versions (the virtual environment `.venv` already exists)
- [x] `.gitignore` for `.env`, `.venv/`, `raw_data/`, `data/`, `__pycache__/`
- [x] `src/config.py`: paths and all thresholds:
  `SUBSET_SIZE=10000`, `BULKY_KG=10`, `BULKY_L=60`, `TIME_SENSITIVE_CATEGORIES`, severity cut-offs,
  `REROUTE_EXTRA_DAYS=2`, `VOUCHER_PCT=10`, `DEFAULT_DELAY_DAYS=3`, `SAMPLE_EMAILS=3`, `FOCUS_TOP_K=50`
- [x] `src/models.py`: `DisruptionEvent`, `AffectedItem`, `OrderImpact`, `Decision`, `EmailDraft`, `ImpactReport`
- [x] `pytest.ini` so tests can import `src`

**Rework: switch to Gemini and add offline mode.** The hosted providers first planned had no API credits available.

- [x] `src/config.py`: replace the earlier provider settings with:
  - `GEMINI_API_KEY`
  - `GEMINI_MODEL="gemini-3.6-flash"`
  - `LLM_MODE`: `gemini` when a key is present, otherwise `offline`
  - `LLM_TIMEOUT_S=30`
  - `LLM_MAX_ATTEMPTS=3`
- [x] `src/llm.py`: rewrite it for the Gemini REST API with httpx.
  - `parse(system, user, schema)` sends `responseMimeType: application/json` and `responseJsonSchema` built
    from the Pydantic model, then validates the reply with `schema.model_validate_json`.
  - `text(system, user)` returns plain text.
  - Retry 5xx and timeouts on the same model, waiting 2 seconds and then 4. On a 429 the model's quota is
    spent, so switch at once to the next model in `GEMINI_FALLBACK_MODELS` and skip the limited model for
    the rest of the run. Only when every model fails, raise `LLMError`. Callers catch only `LLMError`.
    The report names the model that answered and notes the switch.
  - Count calls and tokens in `USAGE` for the trace. Never log the key.
- [x] `requirements.txt`: drop the earlier provider's SDK and pin `httpx==0.28.1`.
- [x] `.env.example`: add `GEMINI_API_KEY`, `GEMINI_MODEL` and `LLM_MODE`, with a comment that the file is
  optional and the system runs offline without it.
- [x] `src/models.py`: `ImpactReport` gains `llm_mode: str` and `llm_notes: List[str]`. The notes record
  which steps fell back and why.
- [x] `tests/test_llm.py` uses a mocked httpx transport, so no network is needed. It covers four cases:
  - A 503 and then a success returns the parsed model.
  - Repeated 503s raise `LLMError`.
  - Invalid JSON raises `LLMError`.
  - In offline mode the transport is never called.

**Done when:**
- `python -c "import src.config, src.models, src.llm"` runs with and without a `.env` file.
- `pytest tests/test_llm.py` passes with no key.
- One live `llm.parse` call returns a valid `DisruptionEvent` when the key is set.

### Phase 1: Data preparation (`src/data_prep.py`)

- [x] Load the six CSVs. Read the translation file with `encoding="utf-8-sig"`.
- [x] Drop `canceled` and `unavailable` orders and orders without items. Keep the 10,000 most recent by purchase date.
- [x] Join items with orders, products, sellers, customers and translations.
- [x] Fill gaps: missing category becomes `unknown`, missing English name falls back to Portuguese,
      missing weight or size means not bulky.
- [x] Add derived fields: `weight_kg`, `volume_l`, `is_bulky`, `is_time_sensitive`, `promised_date`, `baseline_eta`.
- [x] Build the `document` text for each row (see ARCHITECTURE.md section 3.5).
- [x] Save to `data/processed/order_items.csv` and print a short validation summary.
- [ ] Commit the processed subset, so reviewers skip the Kaggle download. Change `.gitignore` to ignore
      `data/chroma/` instead of all of `data/`.

**Done when:** the file has 11,301 rows and 10,000 unique orders, the key fields have no nulls, and the
file is not gitignored.

### Phase 2: Vector index (`src/build_index.py`)

- [x] Confirm Chroma's built-in embedding model loads. It downloads once, about 80 MB.
- [x] `build_index.py` deletes and recreates the `order_items` collection, so rebuilding is safe.
- [x] Add `id = order_id-order_item_id`, the document and the metadata. Chroma embeds the documents itself.
- [x] Store the embedding model name in the collection metadata.
- [x] A missing index gives a clear message, "Index not found. Run: python -m src.build_index", and no stack trace.
- [x] Record the build time for the README. Measured: 122 seconds on an Apple silicon laptop, and the index is 62 MB.

**Done when:**
- The collection count is 11,301.
- A test query for "office chair" returns furniture items.
- The filter `seller_state = SP` returns 7,959 items, the same as pandas.

### Phase 3: Disruption Parser (`src/agents/disruption_parser.py`)

The parser has two paths that produce the same `DisruptionEvent`.

- [x] **Gemini path:** `llm.parse(SYSTEM_PROMPT, query, DisruptionEvent)`. The prompt states the rules: state
      codes, direction, default delay, the city-or-state rule and the default product focus.
- [x] **Rule-based path:** `rule_parser.parse_with_rules(query)`, in its own file to keep both files short. It is used in offline mode and whenever Gemini fails. It
      is a real parser, not a stub.
  - **States:** full names with accents removed, plus two-letter codes only as uppercase whole words, so
    the words "to" or "es" are not read as states.
  - **Cities:** city names from the dataset, matched as whole words after the state names are removed. Then
    "Rio Grande do Sul" does not also match the city `rio grande`, and "Bahia" stays the state. "City of Sao
    Paulo" or "Sao Paulo city" picks the city.
  - **Direction:**
    - "both ways", "in and out" and "to and from" mean both.
    - "leaving", "out of", "from" and "departing" mean outbound.
    - "into", "arriving" and "deliveries to" mean inbound.
    - If none of these appear, the default is outbound.
  - **Duration:** "5 days", "five days", "a week", "two weeks" and "48 hours". The default is 3 days.
  - **Type:**
    - Rain, flood and storm mean weather.
    - Strike means strike.
    - Port means port_closure.
    - Road and bridge mean infrastructure.
    - Anything else is other.
  - **Output:** the same `interpretation` sentence as the Gemini path, plus a list of every default it applied.
- [x] **Shared post-validation for both paths:** keep only valid state codes, normalize city names and clamp
      days to 1 to 30.
- [x] `run(query, use_llm)` tries Gemini when `use_llm` is true and falls back to the rules on `LLMError`.
      It reports which path produced the event.

**Done when** these queries parse as expected with the rule-based parser (a unit test) and with Gemini (a live test):

| Query | Expected |
|---|---|
| Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days | SP, outbound, 5 |
| Flooding in Rio Grande do Sul is blocking deliveries into the state for 10 days | RS, inbound, 10 |
| Truckers' strike in Curitiba, shipments out of the city stuck for a week | city curitiba, outbound, 7 |
| Port issues around Rio de Janeiro affecting shipments both ways for 3 days | RJ, both, 3 |
| Storm in Belo Horizonte, deliveries arriving in the city delayed 48 hours | city belo horizonte, inbound, 2 |
| A road collapse in Bahia is holding up freight | BA, outbound, 3, with the defaults listed |
| Something bad happened | no location, so the pipeline stops politely |

Both paths must give the same event for the two sample scenarios, the first two rows.

### Phase 4: Retrieval Agent (`src/agents/retrieval_agent.py`)

This phase needs no LLM, because the embeddings run locally.

- [x] `build_where(event)` turns the event into a Chroma filter (seller or customer fields, states or cities).
- [x] Step A: `collection.get(where=...)` returns all affected items.
- [x] Step B: `collection.query(query_texts=[product_focus], where=..., n_results=50)` sets `focus_match`.
- [x] Return `AffectedItem` objects in a fixed order, sorted by ID, so runs are repeatable.

**Done when:** the SP scenario returns 7,959 items, the RS inbound scenario returns items, and the focus
hits for "heavy furniture" are mostly furniture and home goods.

### Phase 5: Logistics Analyst and Mitigation Agent

- [x] `logistics_analyst.run(items, delay_days)` calculates the buffer, new ETA, days late, item severity,
      the bulky bump and order severity, with reasons.
- [x] `mitigation_agent.run(order_impacts, delay_days)` applies rules R0 to R4 in order, sets the action,
      resolution, final ETA, rule ID and reason.
- [x] Unit tests for every severity band, the bulky bump, every rule and the rule order. For example, a
      time-sensitive bulky item hits R1 before R2.

**Done when:** `pytest` passes with no API key set.

### Phase 6: Customer Success Agent, Report Writer, Pipeline

- [x] `customer_success.run(order, decision, use_llm)` returns an `EmailDraft`.
  - **Gemini path:** a facts-only prompt, then a check that the email contains the final ETA (or "refund"
    for a cancellation). One retry if the check fails.
  - **Template path:** used offline, and when Gemini fails twice. There is one hand-written template per
    resolution: cancel with a refund, reroute, delay with a freight refund, and delay with a voucher.
  - The templates use the same facts as the prompt: city, categories, purchase date, promised date, final
    ETA and offer amount. They must read as finished, empathetic emails, because offline reviewers see
    only these.
- [x] `report_writer.run(...)` builds everything except the summary in code:
  - the statistics, top categories and sellers, priority products and compensation cost
  - a Gemini executive summary that may only use the numbers it is given, or a template summary built
    from the same numbers.
- [x] `pipeline.run(query, n_emails=3, use_llm=None)`. `None` means the default from `LLM_MODE`.
  - It calls the six steps in order.
  - It picks the sample orders: the most severe order per action type, with ties broken by order ID.
    Orders that were on time before the disruption come first, because an order already weeks late in
    the real data is not a fair example of this disruption.
  - It records a trace with counts and timings, and stops early when needed.
  - **Once any LLM step falls back, later steps skip Gemini for the rest of the run.** A Gemini outage then
    costs one retry cycle, not five. The reason goes into `llm_notes`.
  - It fills in `llm_mode`, for example `gemini (gemini-3.6-flash)` or `offline`.
- [x] `render.py` writes `report.md`, `report.json` and `orders.csv` as described in section 1.2.

**Done when:**
- An SP run in offline mode finishes end to end in under about 15 seconds, and the report reads well.
- An SP run in Gemini mode finishes, usually in under a minute. If Gemini is down, the run still finishes
  with templates and the report says so.
- Both modes produce identical numbers for the same query.

### Phase 7: Interfaces

- [x] `cli.py "<query>" [--offline] [--emails 3] [--out DIR]` prints the understanding, the headline
      numbers and the first email. With `--out` it saves the three files.
- [x] `app.py` (Streamlit, one page):
  - a text box and two example scenario buttons
  - a mode badge, and a "Use Gemini" toggle that is off and disabled when there is no key
  - a "How the system understood this" panel showing the parsed event and its assumptions
  - metric cards: affected orders, sellers, % late, value at risk, compensation cost
  - tables: by severity, by action, top categories, top sellers, priority products
  - email cards, each labelled "Gemini" or "Template"
  - one order traced end to end, the expandable step trace, and per-order reasons
  - download buttons for the three report files

**Done when:** both interfaces produce the same numbers for the same query and mode, and the app works
with no `.env` file.

### Phase 8: Docker, samples, README

- [x] Install Docker (Docker Desktop or Colima) on the development machine. It is not installed now, and
      the Docker path must be tested before submission.
- [x] `Dockerfile` (python:3.11-slim):
  - installs the requirements
  - copies the code and `data/processed/order_items.csv`
  - runs `python -m src.build_index` at build time, so the image contains the embedding model and index
  - starts Streamlit by default.
- [x] `docker-compose.yml`: one service on port 8501 with `env_file` marked `required: false`, so it starts
      with no `.env` file. No data volumes are needed.
- [x] Generate samples for two contrasting scenarios, each in both modes:

  | Folder | Scenario | Mode |
  |---|---|---|
  | `samples/sp_rain/` | *Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days* (large outbound region, short delay) | Gemini |
  | `samples/sp_rain_offline/` | Same | Offline |
  | `samples/rs_flood/` | *Flooding in Rio Grande do Sul is blocking deliveries into the state for 10 days* (inbound, long delay) | Gemini |
  | `samples/rs_flood_offline/` | Same | Offline |

- [x] One-command setup for every OS: `tasks.py` (standard library only) and a `Makefile` that calls it.
      The README gives the macOS, Linux and Windows commands, and the manual steps.
- [x] `samples/README.md`: the exact command that produced each folder, and what to look at first.
- [x] Read every sample email before committing. Check the dates, offers and tone, and that the numbers
      match the sanity anchors.
- [x] `README.md`:
  - Quick start first, with the reviewer paths from section 2.3. The no-key path comes first.
  - A "Running without an LLM" section.
  - The architecture summary with a link to ARCHITECTURE.md.
  - The reasoning approach, decisions and tradeoffs, and assumptions.
  - Links to the sample outputs.
  - Limitations, and credit for the Olist data.

**Done when:**
- A fresh clone with no `.env` and no `raw_data/` works both ways:

  ```bash
  # Without Docker
  python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt
  .venv/bin/python -m src.build_index
  .venv/bin/python cli.py "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days" --offline
  .venv/bin/pytest

  # With Docker
  docker compose up --build     # open http://localhost:8501
  ```

- The Gemini and offline samples for each scenario show identical numbers.
- A fresh offline run reproduces the numbers in the committed offline samples (see `test_pipeline_offline.py`).

---

## 7. Testing plan

No test needs an LLM key. Tests that need the index skip with the message "run python -m src.build_index".

| Test | Needs | What it checks |
|---|---|---|
| `test_llm.py` | Nothing (mocked transport) | Retries, `LLMError` on repeated failure or bad JSON, no network in offline mode |
| `test_rule_parser.py` | Nothing | The phase 3 table, plus accents, codes, "a week" and the state-before-city rule |
| `test_retrieval_filter.py` | Nothing | Filter built for outbound, inbound, both, states and cities |
| `test_logistics.py` | Nothing | Severity bands, bulky bump, order severity is the worst of its items |
| `test_mitigation.py` | Nothing | Each rule R0 to R4, rule order, final ETA per action |
| `test_templates.py` | Nothing | Every template email contains its final ETA or "refund" and its resolution. The template summary uses only the report's numbers |
| `test_index_completeness.py` | Index | Chroma filter count equals the pandas count for SP, MG and RS |
| `test_pipeline_offline.py` | Index | Both scenarios run end to end offline. Counts match the sanity anchors, every email has its ETA, and `stats`, `by_severity` and `by_action` equal the committed `samples/*_offline/report.json` |
| `test_gemini_live.py` | `GEMINI_API_KEY`, skipped otherwise | The SP query parses as SP, outbound, 5, and one email passes the date check |

The sample comparison leaves out priority products, because semantic ranking can differ slightly between
CPU types, for example Apple silicon and Docker on x86. Counts, severities and actions do not depend on
embeddings.

---

## 8. Risks and how we handle them

| Risk | Handling |
|---|---|
| The reviewer has no LLM key | Offline mode is a first-class path with its own tests. The samples include real Gemini output to read |
| The reviewer has no Kaggle data | The processed subset is committed |
| The Gemini free tier answers 503 or 429 | Backoff on 503s, then the next fallback model. A 429 switches model at once, because free-tier quotas are per model. Only when every model fails does the run switch to templates, and it says so |
| A Gemini model is retired or renamed | The model name is set in `.env`. `gemini-2.5-flash` is already retired for new keys |
| The rule-based parser misreads unusual wording | The interpretation sentence and the defaults are always shown. The README lists the supported phrasings. Gemini mode handles free text better, and that is the tradeoff |
| Gemini and the rule-based parser disagree | Both are tested on the same table, and the sample scenarios must parse identically |
| The LLM invents facts in an email | Facts-only prompt, date check, one retry, then a template |
| "Sao Paulo" can mean the city or the state | State by default. The interpretation is shown, and the user can say "city" |
| SP affects 70% of orders, so the output is huge | Aggregated tables and sample emails in the report. The full list goes to `orders.csv` |
| The embedding model download needs internet | It downloads once, and the Docker image downloads it at build time |
| Docker is not installed on the development machine | Install it before phase 8. The Docker path is tested, not assumed |
| The index was built with a different embedding model | The model name is stored in the collection and checked at query time |
| The rules look too simple | They are documented, explained per order and easy to change in `config.py`. That is a feature for auditability |

---

## 9. Timeline

| Day | Phases | Outcome |
|---|---|---|
| 1 | 0 rework, 1 commit, 2 | Gemini and offline LLM layer, and a verified vector index |
| 2 | 3, 4, 5 | Both parsers, retrieval, severity and rules, with unit tests |
| 3 | 6, 7 | Pipeline, templates, report files, CLI and Streamlit app |
| 4 | 8 | Docker, samples in both modes, README and a fresh-clone test |
