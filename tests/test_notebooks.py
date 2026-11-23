"""Smoke tests: the template mirrors SKILL.md, and the worked example runs clean."""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "notebooks" / "analysis_template.py"
EXAMPLE = ROOT / "notebooks" / "analysis_example_revenue_change.py"
SECTIONS = [
    "## 1. Data sources and assumptions checked",
    "## 2. Analysis",
    "## 3. Sanity checks",
    "## 4. Summary of findings",
]


def test_template_matches_skill_md() -> None:
    skill = (ROOT / "SKILL.md").read_text()
    block = re.search(r"## Template notebook.*?```python\n(.*?)\n```", skill, re.DOTALL)
    assert block is not None
    assert TEMPLATE.read_text() == block.group(1) + "\n"


@pytest.mark.parametrize("path", [TEMPLATE, EXAMPLE], ids=["template", "example"])
def test_notebook_has_the_four_sections_in_order(path: Path) -> None:
    text = path.read_text()
    positions = [text.index(heading) for heading in SECTIONS]
    assert positions == sorted(positions)


def test_example_has_no_placeholders_left() -> None:
    text = EXAMPLE.read_text()
    assert "TBD" not in text
    assert not re.search(r"<[A-Za-z][^>\n]*>", text)
    assert "NotImplementedError" not in text.replace("raise FileNotFoundError", "")


@pytest.fixture(scope="module")
def example_defs() -> dict:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "seed_example_db.py")], check=True, cwd=ROOT
    )
    spec = importlib.util.spec_from_file_location("example_notebook", EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _outputs, defs = module.app.run()
    return defs


def test_example_runs_top_to_bottom_without_blockers(example_defs: dict) -> None:
    for name in ("source_checks", "sanity_checks"):
        statuses = set(example_defs[name]["status"])
        assert statuses <= {"OK", "FLAG"}, f"{name} has {statuses}"


def test_example_headline_matches_seeded_data(example_defs: dict) -> None:
    headline = example_defs["headline"]
    assert headline.loc[0, "prior"] == pytest.approx(89966.22)
    assert headline.loc[0, "current"] == pytest.approx(74038.21)
