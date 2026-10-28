# Design decisions

This is the decision record for the Olist disruption response system. Each entry gives the context,
what was decided, the alternatives considered and what follows from the choice. Several entries were
changed or added while building, after testing showed something the first design missed. Those entries
say what the evidence was.

[ARCHITECTURE.md](ARCHITECTURE.md) describes the system as built. This document explains why it is built
that way.

## Summary

| # | Decision | Chosen | Main alternative |
|---|---|---|---|
| 1 | Orchestration | Fixed pipeline of six agents | LLM planner choosing tools |
| 2 | Division of labour | LLM for language, code for numbers | LLM computes the impact |
| 3 | Retrieval | Metadata filter, then semantic ranking inside it | Vector top-k alone |
| 4 | Index grain | One document per order item | One per order or per product |
| 5 | Embeddings | Local all-MiniLM-L6-v2 | Hosted embeddings API |
| 6 | Parsing | Gemini or rules, then one shared validation | Gemini only |
| 7 | Place names | State by default, cities replace states | Ask the user |
| 8 | Lateness | Whole days past the promised date | Timestamp comparison |
| 9 | Severity | Day bands plus a bulky bump | LLM judgement |
| 10 | Actions | Rule table R0 to R4, first match wins | LLM decides per order |
| 11 | Compensation | Cost per decision, from config | Not estimated |
| 12 | Customer emails | Facts-only prompt, date check, templates | Free generation |
| 13 | Executive summary | Code check that rejects invented numbers | Prompt instruction only |
| 14 | Sample emails | Most severe order per action, on-time orders first | Most severe order only |
| 15 | LLM provider | Gemini over plain REST | Provider SDK, other vendors |
| 16 | No-key operation | Offline mode as a first-class path | Require a key |
| 17 | LLM failures | Backoff on 5xx, switch model on 429 | Retry one model |
| 18 | Working data | 10,000 most recent orders, treated as in transit | Only real in-transit orders |
| 19 | What is committed | Processed CSV and samples, not the index | Commit nothing generated |
| 20 | App results | Kept per session and saved to disk | Cached by query |
| 21 | Mitigation decisions | Rules decide; the LLM explains and recommends | LLM decides each order |
| 22 | Human review | Code flags unusual orders; the LLM explains why | No review step |

---

## Architecture

### 1. A fixed pipeline of six agents, with no framework

**Context.** Every disruption is handled the same way: understand the query, find what it touches,
measure the impact, decide, communicate and report. The case study asks for a decision system, not a
chatbot.

**Decision.** `src/pipeline.py` calls six agents in a fixed order. Each agent is a module with one `run()`
function that takes and returns Pydantic models. There is no agent framework.

**Alternatives.** An LLM planner that chooses tools at run time. LangChain, LangGraph or CrewAI.

**Consequences.** Runs are predictable, cheap and easy to test, and every step appears in the trace with a
count and a timing. The cost is flexibility: a new kind of task needs code, not a prompt. For a fixed
workflow, that cost is worth paying.

### 2. LLM for language, code for numbers

**Context.** The evaluation asks for appropriate use of LLMs versus deterministic logic. Dates, counts,
severity and actions must be correct and repeatable.

**Decision.** The LLM does three language jobs: reading the query, writing the emails and writing the
summary. Everything else is Python. The LLM never computes a date, a count, a severity or an action.

**Alternatives.** Letting the LLM estimate impact or choose actions per order.

**Consequences.** Every number is unit tested and identical across runs and modes. The LLM can make the
wording better but never the numbers worse.

---

## Retrieval

### 3. Hybrid retrieval: a complete filter, then semantic ranking inside it

**Context.** "Which orders ship from Sao Paulo?" has an exact answer. "Which of those are heavy
furniture?" is a question about meaning. Top-k vector search returns the k nearest items, never a
complete set.

**Decision.** Two searches on the same Chroma collection with the same filter. `collection.get(where=...)`
returns every affected item. `collection.query(...)` then ranks those items against the product focus and
marks the top 50.

**Alternatives.** Vector top-k alone. A hand-written list of "heavy" categories.

**Consequences.** Counts are complete. The Sao Paulo filter returns 7,959 items, exactly what pandas counts,
and a test enforces this for three states. Semantic ranking finds furniture without a category list: for
the default focus, all 50 matches in Sao Paulo are furniture categories. Semantic matches only rank items
for the report. They never change severity, which stays rule-based.

### 4. One document per order item

**Context.** One order can contain items from sellers in different states.

**Decision.** Index at the order-item grain: 11,301 documents. Roll results up to the order for severity,
decisions and emails.

**Alternatives.** One document per order, or per product.

**Consequences.** Only the items that actually pass through the disrupted area count, and the report can
list specific SKUs. An order's severity is the worst of its affected items.

### 5. Local embeddings

**Context.** The first design used a hosted embedding model. During the build, no API credits were
available, and reviewers may not have a key at all.

**Decision.** Chroma's built-in all-MiniLM-L6-v2, running on the CPU. The model name is stored in the
collection, and a mismatch at query time stops with a clear message.

**Alternatives.** OpenAI or Gemini embeddings.

**Consequences.** Retrieval needs no key and costs nothing. The index builds in about two minutes and is
about 60 MB. A hosted model might rank slightly better. Semantic ranking can differ slightly between CPU
types, so the sample comparison test checks counts and decisions but not the ranked product list.

---

## Understanding the query

### 6. Two parsers, one validation

**Context.** Gemini handles free text best, but the system must also run with no key, and both paths must
mean the same thing.

**Decision.** Gemini parses the query into a `DisruptionEvent` when a key is set. A rule-based parser does
the same job offline and whenever Gemini fails. Both results then pass through one validation function.
It checks state codes, normalizes city names, clamps the delay to 1 to 30 days, and lists every default
it applied. It then writes the interpretation sentence from the validated fields.

**Alternatives.** Gemini only. Keeping Gemini's own interpretation sentence.

**Consequences.** Both parsers produce identical events for all seven test queries in the plan, and a test
checks it for the main scenario. The interpretation always describes exactly what retrieval will search,
whichever parser ran. Default notes are checked against the query text, so "No duration given" appears
only when that is true.

### 7. Ambiguous place names mean the state

**Context.** "Sao Paulo" and "Rio de Janeiro" are both a city and a state. Gemini also tends to return a
city's state alongside the city, for example Curitiba with PR.

**Decision.** A name that is both reads as the state unless the query says "city", and the report says
so. When cities are given, the states are dropped, because retrieval filters on the cities.

**Alternatives.** Asking the user to choose. Reading it as the city.

**Consequences.** The blast radius is larger, which is safer: over-notifying beats missing customers. The
state reading of Sao Paulo affects 7,037 orders, and "city of São Paulo" with a 2-day delay affects 2,571.
Dropping states for cities made the two parsers agree.

---

## Impact and decisions

### 8. Lateness is measured in whole days

**Context.** The design's sanity check said about 33% of items would be late after a 5-day delay. The
built system gave 28.2%. The difference came from the profiling: it compared timestamps, and the promised
date is stored as midnight, so an order delivered on its promised day counted as late.

**Decision.** Compare whole dates. Arriving on the promised date is on time. The formula is
`days_late = max(0, baseline_eta + delay - promised_date)`.

**Alternatives.** Timestamp comparison, which gives 33.5%.

**Consequences.** This matches how a customer reads a promise. The sanity anchor was corrected rather than
the code.

### 9. Severity from days late, raised for bulky items

**Context.** The case study asks for severity based on freight weight and the original SLA.

**Decision.** Days late past the promised date set the band: 0 is LOW, 1 to 2 MEDIUM, 3 to 6 HIGH, 7 or more
CRITICAL. A late bulky item, 10 kg or more or 60 L or more, moves up one level. Items already late before
the disruption keep the same formula, with the reason "already N days late before the disruption".

**Alternatives.** A weighted score. LLM judgement.

**Consequences.** Every severity comes with plain-English reasons, such as "Buffer 2 days, delay 5 days, so
3 days late: HIGH" and "Bulky (18.2 kg, 60 L): raised to CRITICAL". The bulky threshold covers about 4.5%
of items. All cut-offs live in `config.py`.

### 10. A rule table decides the action

**Context.** Cancel, reroute or delay is business policy. It must be consistent, auditable and easy to
change.

**Decision.** Five rules, checked in order, first match wins:

| Rule | Condition | Action |
|---|---|---|
| R0 | Severity LOW | MONITOR |
| R1 | Time-sensitive item and HIGH or CRITICAL | CANCEL with a full refund |
| R2 | Bulky item | DELAY with the freight refunded |
| R3 | HIGH or CRITICAL | REROUTE with free expedited shipping |
| R4 | Anything else | DELAY with a 10% voucher |

**Why this order.** Time-sensitive goods lose their value when late, so a refund comes first, even for a
bulky item. Bulky goods are expensive and slow to reroute, so waiting is cheaper. Small goods move easily
by another carrier, so rerouting recovers most of the delay.

**Alternatives.** Letting the LLM choose per order. Rerouting through a second seller, rejected because
only 3.7% of products have one.

**Consequences.** Every decision carries its rule ID and a one-line reason, and `orders.csv` lets a
reviewer check any order in a spreadsheet. The report's mitigation plan shows what each rule achieves:
in the Sao Paulo scenario, rerouting cuts the average delay of 1,389 orders from 5.5 days to 2.5, at an
estimated R$ 20,033. The rules are deliberately simple, which is a feature for
auditability.

### 11. Compensation is costed per decision

**Context.** The report needs a cost estimate, and the data has no business rules for compensation.

**Decision.** Each decision carries what it costs: the full refund for R1, the freight for R2, the voucher
for R4, and for R3 the expedited freight, estimated as the original freight paid again. Every amount is a
placeholder in `config.py`.

**Alternatives.** Leaving cost out of the report.

**Consequences.** The headline numbers include a cost the business can argue with and change. The reroute
cost is the customer's freight, but it is never presented to the customer as an offer, because it is a
cost to the company.

---

## Generation

### 12. Facts-only emails with a date check

**Context.** An email that states a wrong date or invents an offer is worse than no email.

**Decision.** Code builds the facts: order reference, city, items, dates and the offer. Gemini only writes
the tone, from a prompt that forbids new facts. A check in code confirms that the email contains the final
delivery date, or the word "refund" for a cancellation. If it fails, the email is regenerated once, then
a hand-written template is used. There is one template per resolution, and offline reviewers see only
templates, so they are written as finished emails.

**Alternatives.** Free generation. Templates only.

**Consequences.** Reading every sample email found one problem: for a cancellation, Gemini copied an
instruction from the facts into the email ("the new delivery date is none"). The cancellation facts now
leave out the date line entirely. Every sample email states the right date or refund and the right amount.

### 13. The summary may not invent numbers

**Context.** A prompt saying "use only these numbers" is a request, not a guarantee.

**Decision.** After Gemini writes the summary, code extracts every number in it. If any number is not in
the facts it was given, the template summary is used and the report says why.

**Alternatives.** Trusting the prompt.

**Consequences.** The executive summary can never show a number the system did not compute. A test feeds a
summary with an invented number and checks that it is rejected.

### 14. Sample emails come from representative orders

**Context.** The report shows one sample email per action type, taken from the most severe order. In
testing, the most severe orders were often ones that real Olist data shows were already weeks late before
any disruption. The reroute sample promised a date six weeks after the original promise.

**Decision.** Pick the most severe order per action type, but prefer orders that were on time before the
disruption. Break ties by order ID, so the samples are repeatable.

**Alternatives.** The most severe order regardless of history.

**Consequences.** The samples show what this disruption does to a typical order. Every order still gets
its full analysis in `orders.csv`.

---

## LLM operations

### 15. Gemini over plain REST

**Context.** The provider changed during the build. The hosted providers first planned had no API credits available, and
Gemini's free tier covers a demo.

**Decision.** Gemini (`gemini-3.6-flash` by default), called with one visible `httpx.post` in `src/llm.py`.
Structured output uses `responseJsonSchema` built from the Pydantic model. Thinking is set to `low`, which
roughly halved latency in testing.

**Alternatives.** The Gemini SDK. OpenAI or another hosted model.

**Consequences.** The code needs only two calls, structured JSON and plain text, and both are easy to
read. Only `llm.py` knows the provider, so switching vendors means rewriting one file.

### 16. Offline mode is a first-class path

**Context.** Reviewers may not have a key, and the brief asks for something they can run.

**Decision.** Without a key, or with `--offline` or the app toggle, the rule-based parser and the templates
do the three language jobs. Everything else is unchanged.

**Alternatives.** Requiring a key.

**Consequences.** Anyone can run and test the whole system. Both modes give identical numbers for the same
query, which is checked by comparing the Gemini and offline samples. No test needs a key. The tradeoff is
that the rule-based parser understands fewer phrasings, so the README lists the ones it supports.

### 17. Backoff for busy models, a new model for rate limits

**Context.** Testing found that the free tier allows 5 requests per minute and 20 per day per model, and
that it often answers 503 "high demand". A run makes 5 calls. The first version retried the same model
after 2 and 4 seconds, which cannot help when a quota is spent.

**Decision.**

- A 503 or a timeout is retried on the same model after 2 and then 4 seconds.
- A 429 switches at once to the next model in `GEMINI_FALLBACK_MODELS`, because quotas are counted per model.
  The rate-limited model is skipped for the rest of the run.
- A bad key or a bad request stops at once, because it would fail on every model.
- Only when every model fails does the step fall back to code. Later steps in that run then skip Gemini,
  so an outage costs one retry cycle, not five.

**Alternatives.** One model with longer waits. Honouring the server's retry delay, which can be 12 hours
for a daily quota.

**Consequences.** When the default model ran out of quota, the next model answered all five calls and
the report named it. Every switch and fallback is written to the report, and a run always finishes.

---

## Data and delivery

### 18. The 10,000 most recent orders are treated as in transit

**Context.** 97% of Olist orders are already delivered, so there are too few real in-flight orders to
simulate on.

**Decision.** Take the 10,000 most recent orders that have items and were not cancelled. Treat them as in
transit, and use the real delivery date as the "no disruption" arrival.

**Alternatives.** Only orders still marked as shipped.

**Consequences.** The simulation uses real routes and real delivery performance. About 5% of items were
delivered late in real life, so they start with a negative buffer, and their reasons say so.

### 19. Commit the processed data, build the index

**Context.** Reviewers should not need a Kaggle account, and binary files do not belong in a repository.

**Decision.** Commit the 5.5 MB processed CSV and the samples. Leave out the 60 MB index: it takes one
command to build locally, and the Docker image builds it at build time.

**Alternatives.** Committing the index. Asking reviewers to download the raw data.

**Consequences.** A fresh copy with no key and no raw data runs end to end. This was tested with the
README's commands. The Olist data is CC BY-NC-SA 4.0, and the README credits it.

### 20. App results are kept per session and saved to disk

**Context.** The first app cached reports by query. A run that had fallen back to templates stayed cached,
so asking the same query again showed the same fallback.

**Decision.** Keep the last report in the session, so a download click does not rerun the analysis or
spend quota. Each "Assess impact" click runs fresh, and every run is saved to `outputs/` as
`report.md`, `report.json` and `orders.csv`.

**Alternatives.** Caching by query.

**Consequences.** No stale results, and no run is lost.

---

## Extending the LLM's role

### 21. Rules decide the mitigation; the LLM recommends and explains

**Context.** A natural question is whether the mitigation plan should be decided by the LLM, since the
mitigation agent is an "agent".

**Decision.** No. Rules R0 to R4 decide every order, because the decision moves money and must be
consistent, auditable and testable. With 7,037 orders in one scenario, one LLM call per order would also
take hours and exceed the free tier many times over. The LLM instead adds two things the rules cannot:
next steps for the operations team, such as which sellers to contact first, and plain-English notes on
the orders flagged for review.

**Alternatives.** An LLM choosing the action per order. An LLM classifying product types once at data
preparation time, which remains good future work.

**Consequences.** Gemini writes the summary, the next steps and the review notes in one structured call,
so a run still makes five calls. Each part has its own number check and its own template. In testing, the
first prompt produced next steps that only restated the plan, so the prompt now forbids that and asks for
actions the rules do not cover.

### 22. Code flags orders for human review; the LLM explains why

**Context.** Some orders deserve a person's attention before the customer email goes out, but deciding
which ones must be consistent.

**Decision.** Code flags actioned orders that are already 3 or more days late before the disruption,
still 3 or more days late after a reroute, worth R$ 500 or more, split across sellers, or both bulky and
time-sensitive. The report shows the total and five examples chosen so that each kind of flag appears.
The LLM writes one note per example, connecting its flags and saying what to check. It may not question
the decision.

**Alternatives.** Flagging every late reroute. Letting the LLM choose which orders to review.

**Consequences.** The first version flagged any reroute still late by a day or two, which is the normal
outcome of R3, and listed five near-identical orders. The thresholds cut the queue from 1,080 to 429 orders
in the Sao Paulo scenario, and 19 in Rio Grande do Sul, and the examples now show different risks. In
testing, Gemini wrote the reference as "order f92d5a62", so notes are matched by looking for the reference
inside that field.

## Deliberately left out

- **An email for every affected order.** The report shows samples. Production would send every
  non-MONITOR order through a queue, with human approval before a cancellation goes out.
- **Route-level disruptions**, such as freight from one state into another.
- **Real carrier ETAs and distances.** The data has none, so the real delivery date stands in.
- **Rerouting through a second seller.** Only 3.7% of products have one.
