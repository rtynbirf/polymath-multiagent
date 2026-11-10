"""Тесты ПИД1: one_for_one, карантин, зомби-репинг, гёделев вердикт."""

from __future__ import annotations

import asyncio

import pytest

from polymath import (
    ChildSpec,
    DuplicateSkillError,
    PolymathPid1,
    QuarantinedError,
)
from polymath.agent import Agent
from polymath.crews import pid1_demo_specs


def two_specs(max_restarts: int = 3):
    """Двое детей с уникальными навыками и крошечным backoff."""

    async def first(task: str) -> list[str]:
        await asyncio.sleep(0.02)
        return [f"альфа: {task}"]

    async def second(task: str) -> list[str]:
        await asyncio.sleep(0.03)
        return [f"бета: {task}"]

    return [
        ChildSpec(agent=Agent(name="Альфа", skill="alpha", act=first)),
        ChildSpec(
            agent=Agent(name="Бета", skill="beta", act=second),
            max_restarts=max_restarts,
            backoff_base=0.001,
        ),
    ]


def test_pid1_rejects_duplicate_skills() -> None:
    async def same(task: str) -> list[str]:
        return ["x"]

    specs = [
        ChildSpec(agent=Agent(name="Раз", skill="research", act=same)),
        ChildSpec(agent=Agent(name="Два", skill="research", act=same)),
    ]
    with pytest.raises(DuplicateSkillError, match="research"):
        PolymathPid1(specs)


def test_stable_crew_clean_round() -> None:
    events: list[dict] = []
    pid1 = PolymathPid1(two_specs(), on_event=events.append)
    synthesis = asyncio.run(pid1.run("задача"))
    assert synthesis.agents_count == 2
    assert pid1.attempts == pid1.completions == 2  # зомби нет
    assert pid1.restarts == 0
    assert events[0]["type"] == "pid1_started"
    assert events[-1]["type"] == "pid1_verdict"
    assert any(event["type"] == "pid1_child_up" for event in events)


def test_flaky_child_restarts_one_for_one() -> None:
    strikes = {"n": 0}

    async def flaky(task: str) -> list[str]:
        strikes["n"] += 1
        if strikes["n"] == 1:
            raise RuntimeError("брак в заготовке")
        await asyncio.sleep(0.02)
        return ["готово"]

    async def stable(task: str) -> list[str]:
        await asyncio.sleep(0.01)
        return ["стабильно"]

    events: list[dict] = []
    pid1 = PolymathPid1(
        [
            ChildSpec(
                agent=Agent(name="Кузнец", skill="coding", act=flaky),
                max_restarts=3,
                backoff_base=0.001,
            ),
            ChildSpec(agent=Agent(name="Скаут", skill="research", act=stable)),
        ],
        on_event=events.append,
    )
    synthesis = asyncio.run(pid1.run("задача", max_rounds=4))
    assert synthesis.agents_count == 2  # один упал — другой не пострадал
    assert pid1.restarts == 1
    assert pid1.attempts == pid1.completions + pid1.restarts == 4
    assert [e["agent"] for e in events if e["type"] == "pid1_child_down"] == ["Кузнец"]
    down_event = next(e for e in events if e["type"] == "pid1_child_down")
    assert down_event["attempt"] == 1 and down_event["skill"] == "coding"


def test_quarantine_isolates_persistent_failure() -> None:
    async def broken(task: str) -> list[str]:
        raise RuntimeError("вечный брак")

    async def ok(task: str) -> list[str]:
        await asyncio.sleep(0.02)
        return ["ок"]

    pid1 = PolymathPid1(
        [
            ChildSpec(
                agent=Agent(name="Брак", skill="broken", act=broken),
                max_restarts=1,
                backoff_base=0.001,
            ),
            ChildSpec(agent=Agent(name="Мастер", skill="coding", act=ok)),
        ]
    )
    synthesis = asyncio.run(pid1.run("задача", max_rounds=6))
    assert pid1.quarantined == ("Брак",)  # своё: изоляция, а не смерть надзора
    assert synthesis.agents_count == 1  # экипаж продолжается без бракодела
    assert "ок" in synthesis.findings


def test_all_children_die_pid1_survives() -> None:
    async def broken(task: str) -> list[str]:
        raise RuntimeError("брак")
    pid1 = PolymathPid1(
        [
            ChildSpec(
                agent=Agent(name="Раз", skill="a", act=broken),
                max_restarts=0,
                backoff_base=0.001,
            ),
            ChildSpec(
                agent=Agent(name="Два", skill="b", act=broken),
                max_restarts=0,
                backoff_base=0.001,
            ),
        ]
    )
    with pytest.raises(QuarantinedError, match="экипаж пуст"):
        asyncio.run(pid1.run("задача", max_rounds=5))
    assert pid1.quarantined == ("Раз", "Два")  # ПИД1 жив, хотя детей нет


def test_verdict_carries_godel_limits() -> None:
    events: list[dict] = []
    pid1 = PolymathPid1(two_specs(), on_event=events.append)
    asyncio.run(pid1.run("задача"))
    verdict = events[-1]
    assert verdict["type"] == "pid1_verdict"
    assert len(verdict["verdicts"]) == 3
    assert verdict["limits"]
    assert any("Гёдель" in limit for limit in verdict["limits"])


def test_demo_crew_heals_itself() -> None:
    pid1 = PolymathPid1(pid1_demo_specs())
    synthesis = asyncio.run(pid1.run("выковать флагман из чистого stdlib", max_rounds=6))
    assert synthesis.agents_count == 3
    assert pid1.restarts == 2  # Кузнец бракует два первых удара
    assert pid1.quarantined == ()
    assert pid1.attempts == pid1.completions + pid1.restarts
    assert any("Кузнец" in finding for finding in synthesis.findings)
