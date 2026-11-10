"""Тесты Надзирателя: инварианты оркестратора под постоянным надзором.

Добро проходит, каждое из четырёх нарушений ловится. Плюс живой прогон:
Надзиратель в экипаже не исключает себя из надзора.
"""

from __future__ import annotations

import asyncio

import pytest

from polymath import (
    AuditViolation,
    PolymathOrchestrator,
    Synthesis,
    audit,
    supervisor_agent,
)
from polymath.agent import AgentReport
from polymath.crews import demo_agents


def two_reports() -> tuple[AgentReport, ...]:
    return (
        AgentReport(agent="Скаут", skill="research", findings=("a", "b"), seconds=0.3),
        AgentReport(agent="Зодчий", skill="architecture", findings=("c",), seconds=0.5),
    )


def clean_synthesis() -> Synthesis:
    return Synthesis(task="т", findings=("a", "b", "c"), reports=two_reports(), seconds=0.5)


def test_audit_passes_on_clean_synthesis() -> None:
    verdicts = audit(clean_synthesis())
    assert len(verdicts) == 3
    assert verdicts[0].startswith("Контракт:")
    assert verdicts[1].startswith("Параллельность:")
    assert verdicts[2].startswith("Синтез:")


def test_audit_catches_duplicate_skill() -> None:
    reports = (
        AgentReport(agent="Альфа", skill="research", findings=("a",), seconds=0.1),
        AgentReport(agent="Бета", skill="research", findings=("b",), seconds=0.1),
    )
    synthesis = Synthesis(task="т", findings=("a", "b"), reports=reports, seconds=0.1)
    with pytest.raises(AuditViolation, match="дублируются навыки research"):
        audit(synthesis)


def test_audit_catches_sequential_run() -> None:
    reports = (
        AgentReport(agent="Альфа", skill="research", findings=("a",), seconds=0.4),
        AgentReport(agent="Бета", skill="coding", findings=("b",), seconds=0.4),
    )
    # 0.90s общего при 0.80s суммы времён — параллельности не было.
    synthesis = Synthesis(task="т", findings=("a", "b"), reports=reports, seconds=0.9)
    with pytest.raises(AuditViolation, match="Параллельность нарушена"):
        audit(synthesis)


def test_audit_catches_dirty_findings() -> None:
    synthesis = Synthesis(
        task="т", findings=("a", "b", "a"), reports=two_reports(), seconds=0.5
    )
    with pytest.raises(AuditViolation, match="дубликаты в находках"):
        audit(synthesis)


def test_audit_catches_broken_order() -> None:
    synthesis = Synthesis(
        task="т", findings=("b", "a", "c"), reports=two_reports(), seconds=0.5
    )
    with pytest.raises(AuditViolation, match="порядок первых вхождений нарушен"):
        audit(synthesis)


def test_supervisor_joins_the_crew() -> None:
    crew = demo_agents() + [supervisor_agent()]
    orchestrator = PolymathOrchestrator(crew)  # 5 уникальных навыков — контракт доволен
    synthesis = asyncio.run(
        orchestrator.solve("проверить, что одно другое не исключает")
    )
    assert synthesis.agents_count == 5
    assert len(audit(synthesis)) == 3  # Надзиратель не исключает себя из надзора


def test_supervisor_rejects_empty_mandate() -> None:
    agent = supervisor_agent()
    with pytest.raises(AuditViolation, match="Пустой мандат"):
        asyncio.run(agent.act("   "))


def test_live_demo_audit() -> None:
    synthesis = asyncio.run(
        PolymathOrchestrator(demo_agents()).solve("построить уникальный проект")
    )
    assert len(audit(synthesis)) == 3


def test_verdict_declares_godelian_limits() -> None:
    """Гёделева поправка: вердикт обязан декларировать собственную неполноту."""
    from polymath import LIMITS

    assert LIMITS, "пределы надзора объявлены"
    assert any("Гёдель" in limit for limit in LIMITS)
    assert any("вне системы" in limit for limit in LIMITS)
