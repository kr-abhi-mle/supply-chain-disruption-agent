# Olist disruption response agents

A multi-agent system that takes a supply chain disruption in plain English, finds the exact orders,
sellers and products it affects in the Olist e-commerce data, and decides what to do about each order.
It scores every order's delay with explainable rules, chooses to cancel, reroute or delay, and drafts
empathetic customer emails with a specific resolution. The LLM (Gemini) only reads the query and writes
the prose. Every date, count, severity and decision is computed in plain Python, and the whole system
also runs offline with no API key.

```text
$ python cli.py "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days" --offline
Understood as: A weather disruption delays freight leaving the state of Sao Paulo (SP) by 5 days.
Affected: 7,037 orders, 7,959 items, 922 sellers
Late: 2,268 orders (32.2%), on average 4.2 days
By rule:     R0 MONITOR 4,769, R1 CANCEL 59, R2 DELAY 96, R3 REROUTE 1,389, R4 DELAY 724
```

## Set up and run locally

No API key and no Kaggle download are needed: the processed 10,000-order subset is in `data/processed/`,
and the system runs offline without a key.

### Quick setup

One command does steps 2 to 4 below. It creates `.venv` with Python 3.11, installs the packages, creates
`.env` from the example, builds the index, and says whether Gemini or offline mode will be used. It takes
about 3 minutes the first time, and running it again skips whatever is already done.

**macOS or Linux**

```bash
git clone <repo-url> && cd <repo-folder>
make setup          # then, optionally, paste your Gemini key into .env (step 4) and run: make check-key
make offline        # run the Sao Paulo example offline
make app            # start the web app on http://localhost:8501
```

**Windows (PowerShell)**

```powershell
git clone <repo-url>; cd <repo-folder>
py tasks.py setup   # then, optionally, run: notepad .env, paste your key (step 4), and run: py tasks.py check-key
py tasks.py offline
py tasks.py app
```

Every task lives in [tasks.py](tasks.py), a standard-library Python script that works the same on every
system. The Makefile is a shortcut to it, so `make setup` and `python3 tasks.py setup` do the same thing.
Run `make` or `python3 tasks.py` on its own to list the tasks:

| make (macOS, Linux) | tasks.py (any system) | What it does |
|---|---|---|
| `make setup` | `tasks.py setup` | Install, create `.env`, build the index and check the key |
| `make check-key` | `tasks.py check-key` | Show whether runs will use Gemini or offline mode |
| `make run QUERY="..."` | `tasks.py run "..."` | Run the CLI, with Gemini if a key is set |
| `make offline QUERY="..."` | `tasks.py offline "..."` | Run the CLI offline |
| `make run ARGS="--out results/x"` | `tasks.py run "..." --out results/x` | Also save `report.md`, `report.json` and `orders.csv` |
| `make app` | `tasks.py app` | Start the web app |
| `make test` | `tasks.py test` | Run the tests |
| `make docker` | `tasks.py docker` | Build and start the app in Docker |
| `make clean` | `tasks.py clean` | Remove `.venv` and the index. Keeps `.env`, the data and saved outputs |

Without a query, `run` and `offline` use the Sao Paulo example. The script itself runs under any Python
3.8 or newer. For the project it needs Python 3.11: if [uv](https://docs.astral.sh/uv/) is installed, it
uses uv, which installs packages faster and downloads Python 3.11 when it is missing. Otherwise it looks
for `python3.11`, or `py -3.11` on Windows, and uses pip.

The steps below are what `setup` does, for doing it by hand.

### Before you start

- **Python 3.11, or uv.** Check with `python3.11 --version`. On a Mac, install it with
  `brew install python@3.11`, or download it from [python.org](https://www.python.org/downloads/). With
  the quick setup and uv installed, you can skip this.
- **Disk space.** About 1 GB: 800 MB for the Python packages, 170 MB for the embedding model and 60 MB
  for the vector index.
- **Internet, once.** The first index build downloads the embedding model.

### Step 1: Get the code

```bash
git clone <repo-url>
cd <repo-folder>
```

Run every command below from this folder.

### Step 2: Create a virtual environment and install the packages

```bash
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Step 3: Build the vector index

```bash
.venv/bin/python -m src.build_index
```

This takes about 2 minutes and ends with a line like `Indexed 11,301 items into 'order_items' in 122 s`.
You only need to run it once.

### Step 4 (optional): Add your Gemini API key

Skip this step to run offline. Every number is the same either way. Gemini only writes the prose: the
query reading, the emails, the summary, the next steps and the review notes.

1. Get a free key from [Google AI Studio](https://aistudio.google.com/apikey). Sign in with a Google
   account and click **Create API key**.
2. Create your `.env` file from the example:

   ```bash
   cp .env.example .env
   ```

3. Open `.env` in a text editor and replace `your-key-here` with your key. The line must look exactly
   like this, with your key in place of the example:

   ```text
   GEMINI_API_KEY=AIzaSyExampleKey123
   ```

   Keep it on one line, with no space at the start, no spaces around `=` and nothing after the key.
   Leave the other lines as they are.
4. Check that the key is read:

   ```bash
   .venv/bin/python -c "from src import config; print(config.LLM_MODE)"
   ```

   It should print `gemini`. If it prints `offline`, the key was not read. A warning such as
   `python-dotenv could not parse statement starting at line 5` points to the line to fix.

`.env` is listed in `.gitignore`, so your key is never committed.

### Step 5: Run it

**Command line.** Without a key, add `--offline`. With a key, the first line of output says
`Run mode: gemini (...)` and names the model that answered.

```bash
.venv/bin/python cli.py "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days" --offline
.venv/bin/python cli.py "Flooding in Rio Grande do Sul is blocking deliveries into the state for 10 days"
```

**Web app.**

```bash
.venv/bin/streamlit run app.py
```

Open http://localhost:8501, click an example scenario or type your own, then click **Assess impact**.
The **Use Gemini** toggle is on when a key is set, and off and disabled when it is not.

**Tests.** No test needs a key. The two live Gemini tests run only when a key is set.

```bash
.venv/bin/pytest
```

### Gemini free-tier limits

- The free tier allows 5 requests per minute and 20 per day for each model. One run makes 5 requests, so
  wait about a minute between Gemini runs.
- When the main model answers "quota exceeded" (HTTP 429), the system switches to the next model in
  `GEMINI_FALLBACK_MODELS`, which has its own quota. The report names the model that answered.
- If every model fails, the run still finishes using templates, and the report says which steps fell back.

### Setting up on Windows

Windows has no `make`, but `py tasks.py` runs every task. Use one of these three routes.

**Docker Desktop. This is the simplest.** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/),
which sets up WSL 2 for you. Then, in PowerShell:

```powershell
git clone <repo-url>
cd <repo-folder>
docker compose up --build
```

Open http://localhost:8501. To use Gemini, first run `Copy-Item .env.example .env`, then add your key as
in step 4.

**WSL 2.** In an Ubuntu terminal under WSL, the macOS and Linux instructions work unchanged, including
`make setup`.

**Native Python in PowerShell.** Install Python 3.11 from [python.org](https://www.python.org/downloads/),
which also installs the `py` launcher, or install [uv](https://docs.astral.sh/uv/). Then run the quick
setup above with `py tasks.py setup`. If you prefer to run each step yourself:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m src.build_index
Copy-Item .env.example .env        # optional: then run notepad .env and add your key as in step 4
.venv\Scripts\python -c "from src import config; print(config.LLM_MODE)"
.venv\Scripts\python cli.py "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days" --offline
.venv\Scripts\python -m streamlit run app.py
.venv\Scripts\python -m pytest
```

### Other ways to run

**With Docker, no key.**

```bash
docker compose up --build                # or: make docker. Then open http://localhost:8501
```

The image builds the index at build time, so it needs no `.env` file. If `.env` exists, Docker passes the
key to the app. See [Running with Docker](#running-with-docker) for setup on a Mac and more commands.

**From the raw Kaggle data.** Put the Olist CSVs in `raw_data/`, then run `.venv/bin/python -m src.data_prep`
before step 3.

### CLI options

```bash
python cli.py "<query>" [--offline] [--emails 3] [--out DIR]
```

`--out DIR` writes `report.md`, `report.json` and `orders.csv`. The app offers the same three files as
downloads, and also saves every run to `outputs/<date_time>_<first words of the query>/`. With Docker,
that folder is mounted, so the files appear in `./outputs` on your machine.

### Running with Docker

**Get Docker.** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), or on a Mac
use Colima, a free command-line alternative:

```bash
brew install colima docker docker-compose
colima start --cpu 4 --memory 6          # starts a small Linux VM; colima stop frees it again
```

**Build and run.**

```bash
docker compose up --build                # open http://localhost:8501; Ctrl+C to stop
docker compose down                      # remove the container when you are done
```

- **The first build takes several minutes.** It installs the packages, downloads the 80 MB embedding model
  and builds the vector index into the image, so it needs internet once. Later starts take seconds.
- **No key means offline mode.** If a `.env` file with `GEMINI_API_KEY` exists, Compose passes it to the
  container and the app uses Gemini. Editing `.env` needs a restart, not a rebuild.
- **Saved runs** appear in `./outputs` on your machine, because Compose mounts that folder.

**Use the CLI or the tests inside the container.**

```bash
docker compose run --rm app python cli.py "Heavy rains are delaying all freight leaving Sao Paulo for the next 5 days" --offline
docker compose run --rm app pytest
```

**If you see `unknown flag: --build`,** Docker cannot find its Compose plugin. Either use the standalone
command `docker-compose up --build`, or tell Docker where Homebrew put the plugin by adding this to
`~/.docker/config.json`, next to the settings already there:

```json
"cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"]
```

## Running without an LLM

Offline mode is a full path, not an error handler. It is used when there is no key, with `LLM_MODE=offline`,
with `--offline`, or with the app toggle off.

| Step | Gemini mode | Offline mode |
|---|---|---|
| Parse the query | Gemini structured output | Rule-based parser |
| Retrieval, severity, decisions, every number | Code and local embeddings | The same code |
| Emails, summary, next steps, review notes | Gemini, checked by code | Hand-written templates with the same facts |

Both modes give identical numbers for the same query. In Gemini mode, if a step fails (the free tier often
answers 503 or 429), that step falls back to its offline counterpart, later steps skip Gemini, and the
report says so.

The rule-based parser understands:

- **Places:** state names with or without accents ("São Paulo", "Rio Grande do Sul"), uppercase codes ("SP"),
  and any city in the order data ("Curitiba", "Belo Horizonte"). "City of Sao Paulo" means the city.
- **Direction:** "leaving", "out of", "from" mean outbound. "Into", "arriving", "deliveries to" mean inbound.
  "Both ways", "in and out" mean both.
- **Duration:** "5 days", "five days", "a week", "two weeks", "48 hours".
- **Type:** rain, flood or storm; strike; port; road or bridge.

Anything it has to assume, such as a default duration, is listed in the report.

## How it works

```text
query ─▶ 1 Parser ─▶ 2 Retrieval ─▶ 3 Logistics ─▶ 4 Mitigation ─▶ 5 Customer emails ─▶ 6 Report
         Gemini or    Chroma filter   ETA, days      rules R0-R4     Gemini or            stats, tables,
         rules        + semantic      late,          (code)          templates            summary
                      ranking         severity
```

1. **Disruption Parser** turns the query into a `DisruptionEvent`: states or cities, direction, days, product
   focus. Gemini or the rule-based parser reads it, then the same code validates it and lists every assumption.
2. **Retrieval Agent** runs two searches on one Chroma collection: a metadata filter that returns every
   affected order item, then semantic search inside that filter to rank items against the product focus.
3. **Logistics Analyst** computes each item's buffer, new ETA, days late and severity, raises bulky items
   one level, and writes the reasons.
4. **Mitigation Agent** applies a fixed rule table, first match wins, and records the rule and a reason.
5. **Customer Success Agent** writes one email per action type from verified facts. A code check confirms
   the email states the final date or the refund.
6. **Report Writer** computes the statistics, tables and mitigation plan, and flags unusual orders for
   human review in code. One Gemini call then writes the executive summary, next steps for operations and
   a note per flagged order. Every part may only use the numbers it is given.

`src/pipeline.py` calls the six steps in order and records a trace with counts and timings. There is no
agent framework. Full design: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Why it is built this way:
[docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md). Column names and types: [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md).
Build plan: [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

### LLM versus deterministic logic

| Task | Approach | Why |
|---|---|---|
| Understand the disruption text | Gemini, or rules offline | Free text with many phrasings |
| Find affected orders | Metadata filter | Must be exact and complete |
| Match product types to the query | Local embeddings | Meaning-based, no hand-written category lists |
| Dates, days late, severity | Python | Must be correct, repeatable and tested |
| Cancel, reroute or delay | Python rule table | Business policy must be auditable |
| Customer email | Gemini with a date check, or a template | Tone and personalization |
| Executive summary and next steps | Gemini with a number check, or a template | Readability, with no new numbers |
| Which orders need human review | Python flags | Consistent; a flag never changes a decision |
| Why a flagged order matters | Gemini with a number check, or a template | Plain-English explanation of the risk |

### The rules

| Rule | Condition | Action | Customer resolution |
|---|---|---|---|
| R0 | Severity LOW, the buffer absorbs the delay | MONITOR | None |
| R1 | Time-sensitive item and severity HIGH or CRITICAL | CANCEL | Free cancellation, full refund |
| R2 | Bulky item | DELAY | Freight refunded |
| R3 | Severity HIGH or CRITICAL | REROUTE | Free expedited shipping, arrives 2 days late instead of the full delay |
| R4 | Anything else (MEDIUM) | DELAY | 10% voucher |

Severity comes from days late past the promised date: 0 is LOW, 1 to 2 MEDIUM, 3 to 6 HIGH, 7 or more
CRITICAL. A late bulky item (10 kg or more, or 60 L or more) moves up one level. Every threshold lives in
`src/config.py`.

## Key decisions and tradeoffs

The full record, with the alternatives and the evidence behind each choice, is in
[docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md).

- **A fixed pipeline, not an LLM planner.** The steps are always the same, so a fixed order is predictable,
  testable and cheap.
- **Hybrid retrieval.** Top-k vector search cannot give complete counts, so a metadata filter finds every
  affected item and semantic search only ranks them.
- **Rules decide, not the LLM.** Cancel, reroute and delay are business policy, so they must be consistent
  and auditable. Each order carries the rule ID and the reasons.
- **Gemini over REST, with offline mode.** The free tier covers a demo. Only `src/llm.py` knows the
  provider, so switching to another LLM changes one file. Offline mode means anyone can run and test everything.
- **Local embeddings.** Chroma's built-in `all-MiniLM-L6-v2` needs no key and no cost. A hosted model might
  rank slightly better.
- **Order-item grain.** An order can hold items from sellers in different states, so only the items shipped
  through the disrupted area count.
- **Sample emails, not every email.** One email per action type keeps runs fast and within the free tier.
  Production would send every non-MONITOR order through a queue.

## Assumptions

- The 10,000 most recent orders are treated as in transit, because 97% of Olist orders are already delivered.
- The real delivery date is the "no disruption" ETA, and every affected item is delayed by the full duration.
- Freight leaves from the seller's location. Outbound filters on sellers, inbound on customers.
- "Sao Paulo" and "Rio de Janeiro" mean the state unless the query says "city".
- Bulky means 10 kg or more, or 60 L or more. Time-sensitive means six categories such as food and flowers.
- Rerouting adds 2 days, and compensation amounts are policy placeholders in `src/config.py`.
- Customers have no names in the data, so emails open with "Hello".

The reasoning behind each assumption is in [docs/ARCHITECTURE.md, section 7](docs/ARCHITECTURE.md#7-assumptions-due-to-dataset-limits).

## Sample outputs

[`samples/`](samples/README.md) holds two scenarios, each run with Gemini and offline:

- Rain in Sao Paulo, outbound for 5 days: [Gemini](samples/sp_rain/report.md) and [offline](samples/sp_rain_offline/report.md).
- Flooding in Rio Grande do Sul, inbound for 10 days: [Gemini](samples/rs_flood/report.md) and [offline](samples/rs_flood_offline/report.md).

## Tests

```bash
.venv/bin/pytest
```

No test needs a key. They cover the LLM layer with a mocked transport, the rule-based parser, the retrieval
filter, every severity band and rule, the templates, index completeness against pandas, and both scenarios
end to end. Live Gemini tests run only when `GEMINI_API_KEY` is set.

## Limitations and future work

- The rule-based parser handles the phrasings above. Unusual wording works better in Gemini mode.
- City names repeat across states, so a city query matches every city with that name.
- The Gemini free tier allows 5 requests per minute and 20 per day per model, about four full runs.
  When the main model answers 429, the system switches to the next model in `GEMINI_FALLBACK_MODELS`,
  which has its own quota, and the report names the model that answered.
- Reroute times, compensation and the time-sensitive list are placeholders until the business sets them.
- Future work: route-level disruptions (from one state into another), an email for every affected order
  through a queue, real carrier ETAs instead of historical delivery dates, and a second seller as a
  reroute option where one exists.

## Data credit

[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce),
licensed CC BY-NC-SA 4.0. `data/processed/order_items.csv` is a derived subset under the same license.
