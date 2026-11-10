"""Ритуал CI: воркфлоу проверяются парсером, а не взглядом.

Философия: недоговорёнки прошлого не переписываются — их блокируют
инварианты в будущем. Каждый воркфлоу обязан быть валидным YAML,
иметь ручную дверь ``workflow_dispatch`` (домашний стандарт) и
цельные имена веток. Артефакты вида ``ain]`` невозможны навсегда.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

WORKFLOWS_DIR = Path(__file__).resolve().parent.parent / ".github" / "workflows"

BRANCH_RE = re.compile(r"^[\w./-]+$")


def workflow_files() -> list[Path]:
    return sorted(WORKFLOWS_DIR.glob("*.yml"))


def test_workflows_exist() -> None:
    assert workflow_files(), "хотя бы один воркфлоу должен существовать"


@pytest.mark.parametrize("path", workflow_files(), ids=lambda p: p.name)
def test_workflow_is_valid_yaml(path: Path) -> None:
    """Воркфлоу читается парсером: структура цела, jobs на месте."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path.name}: YAML не словарь"
    assert "jobs" in data, f"{path.name}: нет jobs"


@pytest.mark.parametrize("path", workflow_files(), ids=lambda p: p.name)
def test_workflow_has_manual_door(path: Path) -> None:
    """Домашний стандарт: любая работа должна иметь ручную дверь."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    triggers = data.get("on") or data.get(True, {})  # yaml 1.1: ключ on → True
    assert "workflow_dispatch" in (triggers or {}), f"{path.name}: нет ручной двери"


@pytest.mark.parametrize("path", workflow_files(), ids=lambda p: p.name)
def test_branches_are_clean_tokens(path: Path) -> None:
    """Имена веток — цельные токены без обрывов и лишних символов."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    triggers = data.get("on") or data.get(True, {})
    branches = (triggers.get("push") or {}).get("branches") or []
    for branch in branches:
        assert BRANCH_RE.match(branch), f"{path.name}: кривая ветка {branch!r}"
