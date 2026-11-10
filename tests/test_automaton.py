"""Экзамены Автомата: теория конечных автоматов исполняется, а не рассказывается.

Детерминизм, полнота, достижимость, единственность вердикта, минимизация Мура,
эквивалентность DFA (теорема о ядре с OTP), автономный drive без Хозяина.
"""

from __future__ import annotations

import asyncio

import pytest

from polymath import (
    AutomatonPid1,
    AutomatonViolation,
    ChildSpec,
    automaton_agent,
)
from polymath.agent import Agent
from polymath.automaton import (
    ACCEPTING,
    ALPHABET,
    CORE_ALPHABET,
    DEPARTURES,
    INITIAL,
    OTP_ALIVE,
    OTP_INITIAL,
    OTP_TABLE,
    PID1_ALIVE,
    TABLE,
    equivalent,
    minimize,
    verify,
)
from polymath.crews import pid1_demo_specs
from polymath.pid1 import PolymathPid1


def two_specs(max_restarts: int = 3):
    """Двое детей с уникальными навыками — заготовка для автономных прогонов."""

    async def first(task: str) -> list[str]:
        return [f"альфа: {task}"]

    async def second(task: str) -> list[str]:
        return [f"бета: {task}"]

    return [
        ChildSpec(agent=Agent(name="Альфа", skill="alpha", act=first)),
        ChildSpec(
            agent=Agent(name="Бета", skill="beta", act=second),
            max_restarts=max_restarts,
            backoff_base=0.001,
        ),
    ]


def broken_pair_specs() -> list[ChildSpec]:
    """Оба ребёнка умирают вечно: слово обязано закончиться карантином."""

    async def broken(task: str) -> list[str]:
        raise RuntimeError("брак")

    return [
        ChildSpec(agent=Agent(name="Раз", skill="a", act=broken), max_restarts=0),
        ChildSpec(agent=Agent(name="Два", skill="b", act=broken), max_restarts=0),
    ]


def test_table_passes_theory_exam() -> None:
    proofs = verify(TABLE, ALPHABET, INITIAL, ACCEPTING)
    assert len(proofs) == 5
    assert any("Детерминизм" in proof for proof in proofs)
    assert any("Полнота" in proof for proof in proofs)
    assert any("Достижимость" in proof for proof in proofs)


def test_verify_rejects_incomplete_table() -> None:
    sick = {state: dict(row) for state, row in TABLE.items()}
    del sick["работа"][next(iter(ALPHABET))]
    with pytest.raises(AutomatonViolation, match="Полнота"):
        verify(sick, ALPHABET, INITIAL, ACCEPTING)


def test_verify_rejects_unreachable_state() -> None:
    sick = {state: dict(row) for state, row in TABLE.items()}
    sick["забытое"] = {symbol: "тупик" for symbol in ALPHABET}
    with pytest.raises(AutomatonViolation, match="Достижимость"):
        verify(sick, ALPHABET, INITIAL, ACCEPTING)


def test_verify_rejects_alien_symbol() -> None:
    sick = {state: dict(row) for state, row in TABLE.items()}
    sick["работа"]["метеорит"] = "тупик"  # символ вне Σ — детерминизм δ сломан
    with pytest.raises(AutomatonViolation, match="Чужой символ"):
        verify(sick, ALPHABET, INITIAL, ACCEPTING)


def test_verify_rejects_double_verdict() -> None:
    sick = {state: dict(row) for state, row in TABLE.items()}
    sick["доверие"]["pid1_started"] = "опыт"  # из допуска — в допуск
    with pytest.raises(AutomatonViolation, match="не единственен"):
        verify(sick, ALPHABET, INITIAL, ACCEPTING)


def test_minimize_merges_equivalent_states() -> None:
    """Мур сжимает таблицу: лечение ≡ работа, опыт ≡ доверие — по поведению."""
    minimal = minimize(TABLE, ALPHABET, INITIAL, ACCEPTING)
    assert len(minimal) < len(TABLE)
    canonical_accepting = ACCEPTING & set(minimal)  # «опыт» слит с «доверие»
    assert canonical_accepting == {"доверие"}
    assert equivalent(
        TABLE, INITIAL, ACCEPTING, minimal, INITIAL, canonical_accepting, ALPHABET
    )
    assert minimize(minimal, ALPHABET, INITIAL, canonical_accepting) == minimal  # идемпотентность


def test_otp_core_theorem_holds() -> None:
    """Теорема о ядре: ПИД1 ≡ OTP one_for_one на общих символах «надзор жив»."""
    assert equivalent(
        TABLE, INITIAL, PID1_ALIVE, OTP_TABLE, OTP_INITIAL, OTP_ALIVE, CORE_ALPHABET
    )


def test_departures_from_otp_are_proven_by_machine() -> None:
    """На полном алфавите эквивалентности нет — отступления доказаны машиной."""
    assert not equivalent(
        TABLE, INITIAL, ACCEPTING, OTP_TABLE, OTP_INITIAL, OTP_ALIVE, ALPHABET
    )
    assert set(DEPARTURES) == {"pid1_quarantined", "pid1_verdict", "pid1_degraded"}


def test_drive_accepts_demo_crew() -> None:
    """Автономный прогон: слово принято → «доверие», Надзиратель аудитил."""
    events: list[dict] = []
    pid1 = AutomatonPid1(pid1_demo_specs(), on_event=events.append)
    report = asyncio.run(pid1.drive("выковать флагман из чистого stdlib"))
    assert report.accepted and report.final_state == "доверие"
    assert report.word[0] == "pid1_started" and report.word[-1] == "pid1_verdict"
    assert report.steps == len(report.word)
    assert report.verdicts and len(report.verdicts) == 3  # аудит Надзирателя
    assert any("Минимизация Мура" in proof for proof in report.proofs)
    steps = [event for event in events if event["type"] == "automaton_step"]
    assert [step["symbol"] for step in steps] == list(report.word)
    assert report.attempts == report.completions + report.restarts  # зомби невозможны


def test_drive_survives_full_quarantine_and_asks_for_mandate() -> None:
    """Эмпатия: все дети в карантине — машина жива и просит новый мандат."""
    pid1 = AutomatonPid1(broken_pair_specs())
    report = asyncio.run(pid1.drive("невыполнимый мандат"))
    assert not report.accepted
    assert report.final_state == "карантин"
    assert report.quarantined == ("Раз", "Два")
    assert report.synthesis is None
    assert any("новый мандат" in verdict for verdict in report.verdicts)
    assert report.attempts == report.completions + report.restarts  # инвариант жив


def test_drive_rejects_empty_mandate() -> None:
    pid1 = AutomatonPid1(two_specs())
    with pytest.raises(AutomatonViolation, match="Пустой мандат"):
        asyncio.run(pid1.drive("   "))


def test_foreign_events_pass_by_the_automaton() -> None:
    """Посторонние события не входят в слово и не двигают автомат."""
    events: list[dict] = []
    pid1 = AutomatonPid1(two_specs(), on_event=events.append)
    pid1._process({"type": "custom", "value": 42})
    assert pid1.word == [] and pid1.state == INITIAL
    assert any(event["type"] == "custom" for event in events)


def test_automaton_agent_runs_the_whole_show() -> None:
    """Агент сам: теория + теорема + фрактальный прогон — и навык уникален."""
    agent = automaton_agent()
    assert agent.skill == "automata"
    report = asyncio.run(agent.execute("объять необъятное"))
    findings = report.findings
    assert any("доказательств теории" in finding for finding in findings)
    assert any("Минимизация Мура" in finding for finding in findings)
    assert any("Теорема о ядре" in finding and "(True)" in finding for finding in findings)
    assert any("отступления" in finding and "(True)" in finding for finding in findings)
    assert any("принято" in finding for finding in findings)  # фрактальный прогон


def test_automaton_agent_rejects_empty_mandate() -> None:
    agent = automaton_agent()
    with pytest.raises(AutomatonViolation, match="Пустой мандат"):
        asyncio.run(agent.execute("  "))


def test_automaton_composes_with_plain_pid1_crew() -> None:
    """Автомат над обычным ПИД1: рестарты Кузнеца — в слове, один раз в вердикте."""
    pid1 = AutomatonPid1(pid1_demo_specs())
    asyncio.run(pid1.run("задача"))
    assert pid1.finish()
    assert pid1.word.count("pid1_child_down") == 2  # два бракованных удара Кузнеца
    assert pid1.word.count("pid1_verdict") == 1


def test_learned_table_accepted_only_through_theory() -> None:
    """Обучение = приём новой таблицы только через экзамен: больная не входит."""
    pid1 = AutomatonPid1(two_specs())
    sick = {state: dict(row) for state, row in TABLE.items()}
    del sick["карантин"]["pid1_round"]
    with pytest.raises(AutomatonViolation, match="Полнота"):
        pid1._table = {state: dict(row) for state, row in sick.items()}
        pid1._proofs = verify(pid1._table, ALPHABET, INITIAL, ACCEPTING)
    assert pid1._proofs  # старые доказательства не потеряны


def test_plain_pid1_unaffected_by_automaton() -> None:
    """Обычный ПИД1 без автомата живёт как жил: надзор не навязан."""
    pid1 = PolymathPid1(pid1_demo_specs())
    synthesis = asyncio.run(pid1.run("задача"))
    assert synthesis.agents_count == 3
    assert not hasattr(pid1, "word") or getattr(pid1, "word", None) is None
