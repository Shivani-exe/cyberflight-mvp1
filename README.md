# CyberFlight

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://cyberflight-mvp1.streamlit.app/)
[![Tests](https://github.com/Shivani-exe/cyberflight-mvp1/actions/workflows/tests.yml/badge.svg)](https://github.com/Shivani-exe/cyberflight-mvp1/actions/workflows/tests.yml)

**[Live app](https://cyberflight-mvp1.streamlit.app/) · [Source repository](https://github.com/Shivani-exe/cyberflight-mvp1)**

A Streamlit research demo for retaining authentication-log evidence at lower storage cost, with a guarded Gemini assistant for alert triage.

CyberFlight keeps a seeded baseline sample. When a computer reaches suspicious destination fanout, it escalates that computer to full retention and includes a pre-alert flight-recorder buffer. The app compares **rows stored** with **labeled attack rows retained**. It never changes a real collection system.

## Reproduced results

| Policy | Rows stored | Attack rows kept |
|---|---:|---:|
| Full collection | 100% | 168 / 168 |
| Static computer sample, seed 42 | 21.4% | 1 / 168 |
| Adaptive: 480-minute escalation, 90-minute buffer | 25.6% | 164 / 168 |

Source: [`results/policy_pooled.csv`](results/policy_pooled.csv). Across clusters 0, 14, 21, and 28, alerted-computer counts are respectively **5, 1,252, 45, and 385**. The pipeline reproduces all six reference checks from supplied exports.

**These are four selected, clean-baseline attack windows, not a production trial.** The fixed policy was tuned on these windows. Row retention is not byte cost or measured dollar savings. The seed 42 result is a single computer sample; the app also shows a 40-seed mean and spread, plus separate row-level sampling. Fanout misses repetition on an existing edge, including the documented cluster 21 attack. See [`results/LIMITATIONS.md`](results/LIMITATIONS.md).

## Explore the app

| Page | What it shows |
|---|---|
| Story | Problem, detector, headline result, and adjacent caveats |
| Policy comparison | Full/static/adaptive tradeoffs, static variants, categorical heatmap, two held-out rules |
| Computer timeline | Cumulative total and attack rows, first alert, escalation, and buffer |
| Alert triage | Structured alert, Gemini or fallback proposal, deterministic verdict, simulated retention |
| Ask the results | Grounded table-cell retrieval with unsupported-question refusal |
| Limitations | Scope, missed patterns, retrospective evaluation, and operational assumptions |

## Quick start

Use **Python 3.13**, the version tested for this project.

```sh
git clone https://github.com/Shivani-exe/cyberflight-mvp1.git
cd cyberflight-mvp1
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```sh
# macOS / Linux
source .venv/bin/activate
```

Install and run:

```sh
python -m pip install -r requirements-dev.txt
python -m streamlit run app/streamlit_app.py
```

Or use `make setup` and `make run`. The included `app_data/` and `results/` are enough to run the demo; no raw billion-row log or pipeline execution is required. The app loads small cached tables and one selected computer's aggregate timeline at a time.

## Gemini configuration

Copy `.env.example` to `.env` locally, then set:

```dotenv
GEMINI_API_KEY=your-local-key
GEMINI_MODEL=gemini-3.8-flash
```

The key is read from the environment, ignored local `.env`, or Streamlit secrets. If `GEMINI_MODEL` is absent, the official Google Gen AI SDK lists models and chooses the newest numbered Flash text model supporting `generateContent`. The sidebar allows an override. Model availability depends on the account.

With a key configured, turn **Demo mode (cached LLM)** off and click **Review plan**. A successful request displays **Source: live Gemini**. Missing cached responses, API errors, quota limits, or deadlines produce an explicit fixed-policy fallback. Requests allow sixty seconds per attempt and one retry. Provider-facing schemas omit unsupported `additionalProperties`; local Pydantic validation still rejects unexpected fields and invalid types.

A live planner request and the actual triage button were tested successfully with strict response validation. Temporary provider overload can still cause fallbacks. **Live grounded Q&A and the full batch LLM evaluation remain untested.** No improvement over the fixed rule is demonstrated; the LLM is an explanation and triage assistant.

For offline evaluation, run locally with your key:

```sh
python scripts/build_llm_cache.py
```

This calls Gemini for all attacker alerts plus up to forty seeded apparent false alarms, writes genuine response caches under `app_data/llm_cache/`, and produces `results/llm_vs_fixed.csv` and `results/LLM_EVALUATION.md`. No fabricated model cache is bundled. This selected alert cohort is not an all-computer policy trial. The offline evaluation notice is independent of the live Review plan button.

## Architecture and guardrails

```text
Supplied exports
  -> deterministic fanout alerts and retention simulation
  -> results/*.csv and per-computer aggregate timelines
  -> Streamlit pages

Seven-field alert summary
  -> Gemini JSON proposal
  -> strict Pydantic validation
  -> independent duration bounds and cluster budget
  -> simulation only, or explicit fixed-policy fallback

Result tables + limitations
  -> Gemini selects evidence cells
  -> validate table / row / columns
  -> render source values, or refuse
```

The detector requires at least five unique destinations and either an add-one-smoothed fanout ratio `(window + 1) / (baseline + 1) >= 5` or six more destinations than baseline. The first alert starts the retention window; the static sample remains active.

The planner receives only `cluster`, `computer`, `baseline_fanout`, `fanout_at_alert`, `minutes_since_window_start`, `rows_so_far`, and `in_static_sample`. It receives no raw log rows or attack labels. Escalation bounds are 15–720 minutes and buffer bounds are 0–120 minutes. Proposal budgets are an explicit simulation assumption: extra rows above static may consume at most 10% of a cluster's rows. A single UI review assumes no prior reservations; the batch evaluator tracks cumulative reservations. Rejected proposals fall back to the fixed baseline, even if that baseline exceeds the proposal cap; this is reported and never authorizes collection.

Q&A is extractive. The model selects cells from published result tables; the app verifies those references and renders source values. It does not allow generated numeric prose or new model calculations. Offline mode retrieves the baseline policy table or limitations and refuses unsupported questions.

## Held-out evaluation

Both rules select parameters on three clusters and evaluate only the named held-out fourth cluster. Both tables include pooled totals computed by summing counts before deriving percentages.

| Rule | Training selection | Pooled held-out attack rows kept |
|---|---|---:|
| Original | Cheapest policy meeting 95% pooled training evidence; otherwise maximize pooled evidence, preserving original tie-breaking | 157 / 168 |
| Equal cluster weights | Maximize mean per-cluster evidence, then minimize mean per-cluster row cost; ties prefer shorter escalation and smaller buffer | 69 / 168 |

The equal-cluster rule is not presented as an improvement. Candidate escalation durations are 30, 120, 480, and 720 minutes, with buffers 0, 30, 90, and 120. The comparison heatmap separately displays 30, 120, 480, and “until end”; 100000 remains the underlying sentinel in the original grid.

**C17693 is an attacker in every cluster, so the folds do not hold out attacker identity.** Cluster 21 also contains C19932. This small retrospective split does not establish prospective performance. Source tables: [`held_out.csv`](results/held_out.csv) and [`held_out_equal_cluster.csv`](results/held_out_equal_cluster.csv).

## Reproduce the outputs

Place the supplied exports in ignored `data/`:

```text
data/
  window_rows.parquet
  baseline_fanout.parquet
  clusters.csv
  redteam.csv
```

```sh
python scripts/run_pipeline.py
# Rebuild only the additional equal-cluster evaluation:
python scripts/build_equal_held_out.py
```

The pipeline stops if reference counts do not reproduce. The original auth log is never required. Raw exports are intentionally excluded from Git and the deployment image; obtain them from the project owner to rebuild. The repository includes derived result tables and compact timelines sufficient for the app and tests.

## Tests and validation

```sh
python -m pytest -q
```

**34 tests passed locally**, covering detector edges, streaming/batch agreement, inclusive windows, reference outputs, planner schemas and mocked retries, validator bounds and budgets, source-cell refusal, and AppTest checks for all six pages. UI regressions cover triage default/filter/n/a behavior, heatmap category order, static variants, cumulative timeline layout, pooled totals, and unsupported Q&A refusal. Original outputs and Story/Limitations pages are protected by SHA-256 regression tests.

GitHub Actions is configured to run the offline test suite on pushes and pull requests using Python 3.13. A local pass does not establish that CI or deployment has run. See [`VALIDATION.json`](VALIDATION.json) and [`TESTED_VERSIONS.json`](TESTED_VERSIONS.json).

Measured Story execution under Windows AppTest was 7.02 seconds initially and 0.069 seconds warm after lazy imports. The requested cold-start target below three seconds was not met in that environment. These timings include the test harness and are not browser paint measurements. A Docker build remains untested. Hosted browser verification is recorded in `VALIDATION.json`.

## Deploy

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for Streamlit Community Cloud and Docker instructions. For Community Cloud use repository `Shivani-exe/cyberflight-mvp1`, branch `main`, entrypoint `app/streamlit_app.py`, and Python 3.13. No secrets are needed for a cached/fixed public demo. Put any hosting key in the platform's secrets settings, never in the repository.

The app is deployed on [Streamlit Community Cloud](https://cyberflight-mvp1.streamlit.app/) from this repository. The hosted runtime uses Python 3.13. The page sources live under `app/views/` so Streamlit does not treat them as legacy auto-discovered pages before entrypoint initialization on a fresh deep link. PyArrow is pinned to 24.0.0 to match the hosting platform’s compatibility replacement of version 26.

## Project structure

```text
app/                    Streamlit entrypoint, shared loaders, six views in app/views/
src/cyberflight/         Detector, simulation, held-out selection, guarded LLM layer
scripts/                Pipeline, additional held-out evaluation, real LLM-cache builder
app_data/               Precomputed alerts, indexes, per-computer aggregates
results/                Reproduced tables, checks, documented limitations
tests/                  Unit tests, AppTest regressions, reference hashes
.github/workflows/      Offline test automation
.streamlit/             Runtime configuration and secrets template
Dockerfile              Optional container deployment
```

## Contributing and credentials

Read [`CONTRIBUTING.md`](CONTRIBUTING.md). Never commit keys, local `.env`, `.streamlit/secrets.toml`, or raw exports. The example configuration files contain placeholders only. Derived authentication data retains the provenance and applicable rights of the supplied source material; no new license for that underlying data is asserted here.
