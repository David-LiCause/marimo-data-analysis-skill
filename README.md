# marimo-data-analysis-skill

A [Claude Code](https://claude.com/claude-code) skill that turns a data question into a reproducible,
reviewed analysis. You describe the question and approve the data sources. Claude then builds the
analysis in a [marimo](https://marimo.io) notebook, checks its own work, and hands back a short
summary written for non-technical readers.

## Steps in prescriptive workflow

| Step | What happens | Who |
| ---- | ------------ | --- |
| 1. Scope | Restate the question (metric, population, time window, segments) and confirm it | You and Claude |
| 2. Test connections | Run a trivial read-only query against each candidate data source | Claude |
| 3. Find tables | Review table metadata only (grain, relevance, caveats); no data is pulled | Claude |
| 4. Confirm tables | Claude proposes tables, rejected alternatives, and join keys; you approve | You and Claude |
| 5. Profile | Check row counts, date coverage, nulls, key uniqueness, join fan-out, and reconciliation to a baseline. Each check is rated OK, FLAG (handled and documented), or BLOCKER | Claude, unattended |
| 6. Build | Build the analysis notebook from the template: sources and checks, analysis, sanity checks, findings | Claude, unattended |
| 7. Sanity check | Recompute the key result a second way, compare to the prior period, and check units and totals | Claude, unattended |
| 8. Summary | Build a short summary notebook with only what is needed to understand the answer (skipped if blocked) | Claude, unattended |
| 9. Render | Export the notebooks to PDF with cell outputs | Claude, unattended |
| 10. Report | Reply with status, answer, caveats, checks, and the output folder | Claude, unattended |

Steps 1 to 4 are interactive. After you approve the tables, steps 5 to 10 run without questions, and
decisions are recorded in the notebook. If the data cannot support an answer (a BLOCKER), Claude
reports no headline number and says what is needed to unblock.

## Output

Each analysis produces one folder:

```
analysis_<name>/
├── analysis_<name>.py            full notebook: sources, checks, analysis, findings
├── analysis_<name>_summary.py    short notebook for readers: answer, key results, caveats
├── analysis_<name>.pdf           rendered with cell outputs
└── analysis_<name>_summary.pdf   rendered with cell outputs
```

## Requirements

- Claude Code with the [`marimo-pair`](https://github.com/marimo-team/marimo-pair) plugin. The
  skill uses it to work inside a live notebook. Install it with
  `claude plugin marketplace add marimo-team/marimo-pair` and then
  `claude plugin install marimo-pair@marimo-pair`.
- [`uv`](https://docs.astral.sh/uv/), marimo 0.21.1 or newer, and `jq` and `curl` on your PATH.
- A read-only connection to your data source.
- A browser. marimo pair only works while the notebook is open in one.

## Install

```bash
make install
```

Copies `skill/` to `~/.claude/skills/marimo-data-analysis/`, replacing the previous copy. Start a
new Claude Code session, then run `/marimo-data-analysis` with your question.

## Repository layout

Everything the skill ships is in `skill/`.

| Path | Purpose |
| ---- | ------- |
| `skill/SKILL.md` | The skill: the steps, rules, and output definition |
| `skill/templates/analysis_template.py` | Blank analysis notebook the skill starts from |
| `skill/templates/analysis_summary_template.py` | Blank summary notebook |
| `skill/examples/analysis_example_revenue_change.py` | Finished analysis: how did completed-order revenue change in Q3 2025 vs Q2 2025, and which regions drove it? |
| `skill/examples/analysis_summary_example_revenue_change.py` | The summary of that analysis |
