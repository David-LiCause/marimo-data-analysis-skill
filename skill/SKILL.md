---
name: "marimo-data-analysis"
description: "Run a data analysis or answer a data question in a marimo notebook via marimo pair: scope the question with the user, test connections, find and confirm tables, then analyze, sanity check, and report concisely."
---

# Data Analysis in marimo

Use this skill when the user asks a data question that should end up as a reproducible marimo notebook.

## Rules
- Steps 1-4 are interactive. Steps 5-10 run on their own, without asking questions.
- Read-only. Never modify, delete, or write to source data.
- Never present a number that has not passed the Step 7 checks.
- All notebook work goes through marimo pair (next section).

## Output
Everything for one analysis goes in one folder, `analysis_<name>/` (`<name>` is a short snake_case topic), created in the project's notebooks folder if it has one:

```
analysis_<name>/
├── analysis_<name>.py
├── analysis_<name>_summary.py
├── analysis_<name>.pdf
└── analysis_<name>_summary.pdf
```

Both PDFs are rendered from the notebooks with all cell outputs (tables and charts) included. If the Status is Blocked, the folder holds only the analysis notebook and its PDF.

## marimo pair (required)
Invoke the `marimo-pair:marimo-pair` skill with the Skill tool before touching the notebook, and follow it. Do not build the notebook by writing the `.py` file. In short:
- **Start:** run `discover-servers.sh` first and reuse a server already running. Otherwise copy the template to `analysis_<name>/analysis_<name>.py` (see Output), then run `marimo edit` on that file with `--no-token`. Run it in the background. Do not use `--headless`: marimo opens the browser itself unless that flag is set.
- **Which marimo:** if the project has `pyproject.toml` with marimo as a dependency, use its runner (e.g. `uv run`). If not, use `uvx marimo@latest edit … --sandbox`. Add `--sandbox` whenever the file has a PEP 723 header. marimo must be 0.21.1 or newer, and `jq` and `curl` must be on PATH.
- **Session:** code can only run while the notebook is open in a browser. After starting, confirm a session exists (`discover-servers.sh`, then a trivial `execute-code.sh` call). If there is none within a few seconds, open the server URL yourself (`open <url>` on macOS, `xdg-open` on Linux) and check again. Ask the user to open it only if that still fails. Leave the tab open. If several notebooks are open, pass `--file <notebook path>` to `execute-code.sh`.
- **First command:** run `help(cm)` through `execute-code.sh` and wait for it to succeed before any other `cm` call.
- **Prototype** in the scratchpad (its top-level variables are discarded after each call). **Persist** with `ctx.create_cell`, `ctx.edit_cell`, and `ctx.run_cell` inside `cm.get_context()`; these take cell bodies, not `@app.cell` wrappers. `create_cell` and `edit_cell` only check structure, so after `run_cell` read `ctx.cells[...].status` and `.errors` to confirm the cell actually ran.
- **Never** use Edit, Write, or NotebookEdit on the notebook file while the session is live. Read a cell's current code before replacing it. Add packages with `ctx.packages.add()`, not `uv` or `pip`; install what the connection needs (e.g. `pyarrow`, `db-dtypes`) up front. If polars `to_pandas()` still fails after a mid-session install, see marimo-pair's `reference/gotchas.md` for the pyarrow workaround.
- **Visibility:** `create_cell` hides code by default. Pass `hide_code=False` for every cell except the markdown cells and the Section 3 code cells, matching the template.
- Each public name is defined in one cell only; reuse existing imports. Names starting with `_` are private to their cell, so anything a later cell needs must be public. `marimo._code_mode` is for the scratchpad only, never in notebook cells.

## Step 1: Scope the question (with the user)
Restate the question: metric, population, time window, segments. Ask about anything ambiguous, then get the user to confirm the scope before moving on.

## Step 2: Test connections
Find the data sources available (existing notebook connections, env vars, config). Run a trivial read-only query against each candidate. If none works, tell the user what failed and ask how to connect. Do not continue until one works.

## Step 3: Find tables
Metadata only: use the catalog, schema listing, or `INFORMATION_SCHEMA`, plus any reference files (approved sources, metric definitions). For each candidate note its grain, relevance, and known caveats. Prefer approved sources, the grain the question needs, the most complete date coverage, and the fewest joins.

## Step 4: Confirm tables (with the user)
Present the recommended tables and why, the close alternatives rejected and why, and the join keys. Wait for the user to confirm or change the selection. Do not pull data or start the analysis before this. Once confirmed, start the notebook and get a live session as described under marimo pair, without asking the user to open it, then continue on your own.

## Step 5: Profile the confirmed tables
For each table, in the marimo pair scratchpad: row count, date range vs. the requested window, null rates of used columns, key uniqueness at the stated grain, join match rates and fan-out, and reconciliation to a known baseline if one exists. Classify each check as OK, FLAG, or BLOCKER and record it in the Section 1 check table.

**FLAG (handle and continue):** the result can still be trusted if the problem is handled in a documented way. Apply the least aggressive fix, state it, and measure its impact. Examples: duplicate keys (dedupe with an explicit rule), moderate nulls in a non-key column, join fan-out, a reconciliation gap within tolerance (default 1%).

**BLOCKER (result cannot be trusted):** no viable table, key columns mostly null or the join key unusable, date coverage misses the window, unexplained reconciliation gap beyond tolerance, or a fix that changes the answer by more than the effect being measured. On a BLOCKER, report no headline number. Finish the notebook with Section 1 filled in, Status "Blocked", and a Summary of what was found, why it blocks, and what is needed to unblock.

Decisions from here on are made without asking: pick the most defensible option, record it in the notebook, and list anything the user should decide under "Caveats and open questions".

## Step 6: Build the notebook
The notebook starts as a copy of `templates/analysis_template.py` (in this skill's directory). Through marimo pair, edit its cells to replace every `<placeholder>`, wire up `run_query`, and fill the check tables, and add the analysis cells. Prototype in the scratchpad and commit only validated cells. Four sections, in order:
1. **Data sources and assumptions checked:** paragraph, flags list, check table.
2. **Analysis:** cells, each with a short description above it.
3. **Sanity checks:** paragraph, flags list, check table.
4. **Summary of findings:** paragraph with the answer, then key points and caveats.

Style:
- Each text section is one paragraph of 2-5 sentences plus a bullet list when needed. Write "None" for an empty list.
- Put a 1-3 sentence markdown description above each significant step.
- Comment SQL for QA: purpose of each CTE, grain, join logic, reason for each filter. Comment Python only where non-obvious.
- Use descriptive names. Keep expensive loads in their own cells. Parameters live in one cell.
- The notebook must run top to bottom with no manual steps. Record assumptions in the notebook, not only in chat.
- Replace every `<placeholder>`; none may remain.
- Before moving on, run `marimo check` on the file (read-only) and confirm through marimo pair that no cell has errors.

## Step 7: Sanity check
Record every check in the Section 3 table:
- Cross-check the key result with a second, independent method.
- Compare against the prior period or a benchmark; FLAG changes beyond 20% and look for a cause.
- Confirm units, sign, magnitude, and time window are plausible.
- Confirm joins did not change row counts and totals still reconcile.

If a check fails, investigate and fix once. If it still fails, mark it FLAG (usable with the caveat stated) or BLOCKER, and handle as in Step 5.

## Step 8: Summary notebook
Skip this if the Status is Blocked. Otherwise build a short, readable version of the analysis as `analysis_<name>/analysis_<name>_summary.py`. Start from a copy of `templates/analysis_summary_template.py` (in this skill's directory), start it and build it through marimo pair as in the marimo pair section.

Go through the analysis notebook and keep only what a reader needs to understand and trust the answer:
- **Keep:** the title and answer, the metric definition, time window and population, the cells that produce the final tables and charts (with the connection, parameters and queries they depend on, so it still runs top to bottom), and any flag that materially changes how the answer should be read.
- **Drop:** profiling, check tables, intermediate steps, alternative definitions that did not change the answer, and anything that only supports QA.
- **Order:** a title that states the answer (no paragraph under it), then the key results (a chart or small table each), then key points, then caveats. Add one line saying which checks passed, and link to the full analysis notebook for the detail.
- **Style:** hide the code of every cell (`hide_code=True`) so it reads as a report, format numbers for reading (thousands separators, percentages, units), and use plain language. Every number must match the analysis notebook; do not introduce new ones.
- Check it as in Step 6: `marimo check`, and no cell errors.

## Step 9: Render to PDF
Render each notebook you built (the analysis notebook, and the summary notebook if one exists) to a PDF in the same folder, with cell outputs included:

```bash
uv run marimo export pdf <notebook>.py -o <notebook>.pdf -f
```

## Step 10: Report
Set the notebook Status to Complete, Complete with flags, or Blocked. Reply briefly with:
1. **Status** and **answer**: key number(s) in 1-3 sentences (or why no answer is given).
2. **Flags and caveats** that materially affect the answer.
3. **Checks**: what was verified, and anything not verified.
4. **Output**: the `analysis_<name>/` folder path.
5. **Decisions made on your behalf** and **open questions**, if any.
