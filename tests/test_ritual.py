"""Экзамены Закона Дома: поработал → сделал → убрал за собой — исполнимый закон.

Принимаются только слова, кончающиеся уборкой; «сделал и не убрал» — грязь
навсегда; в алфавите нет символа уведомлений; Автомат закрывает дом при любом
исходе; обучение — только через экзамены теории.
"""

from __future__ import annotations

import asyncio

import pytest

from polymath import (
    AutomatonPid1,
    HouseRitual,
    RitualViolation,
    house_law_agent,
)
from polymath.automaton import (
    ACCEPTING,
    ALPHABET,
    INITIAL,
    TABLE,
    minimize,
    verify,
)
from polymath.crews import pid1_demo_specs
from polymath.ritual import (
    CLEAN,
    CLEANED_UP,
    DIRT,
    HOUSE_ACCEPTING,
    HOUSE_ALPHABET,
    HOUSE_TABLE,
    MADE,
    REST,
    WORK_BEGUN,
    WORK_DONE,
    house_exam,
)


def run_word(word: tuple[str, ...]) -> str:
    """Прогнать слово по таблице закона без создания живого ритуала."""
    state = REST
    for symbol in word:
        state = HOUSE_TABLE[state][symbol]
    return state


def test_house_table_passes_theory_exam() -> None:
    """Закон Дома — корректный DFA: пять доказательств теории."""
    proofs = verify(HOUSE_TABLE, HOUSE_ALPHABET, REST, HOUSE_ACCEPTING)
    assert len(proofs) == 5
    assert any("Детерминизм" in proof for proof in proofs)
    assert any("Полнота" in proof for proof in proofs)
    assert any("Достижимость" in proof for proof in proofs)


def test_alphabet_is_notification_free() -> None:
    """НИКАКИХ нотификаций: в Σ нет символа «уведомить хозяина» — закон структурный."""
    forbidden = ("уведом", "хозя", "notify", "ждать", "вопрос", "спрос", "аппрув")
    for symbol in HOUSE_ALPHABET:
        for token in forbidden:
            assert token not in symbol.lower()
    assert set(HOUSE_ALPHABET) == {WORK_BEGUN, WORK_DONE, CLEANED_UP}


def test_accepted_words_always_end_with_cleanup() -> None:
    """Исполняемый закон: принимаются ТОЛЬКО слова, кончающиеся уборкой."""
    exam = house_exam(max_len=4)
    assert exam.accepted > 0 and exam.rejected > 0
    assert exam.accepted_all_end_cleaned


def test_made_without_cleanup_is_dirt_forever() -> None:
    """Поработал, сделал, НЕ убрал — грязь навсегда: никакой допуск."""
    assert run_word((WORK_BEGUN, WORK_DONE)) == MADE
    assert MADE not in HOUSE_ACCEPTING
    assert run_word((WORK_BEGUN, WORK_DONE, CLEANED_UP)) == CLEAN
    exam = house_exam(max_len=4)
    assert not exam.made_without_cleanup_accepted


def test_cleaned_without_work_is_not_progress() -> None:
    """Уборка без работы не двигает дом в работу: покой остаётся покоем."""
    assert run_word((CLEANED_UP,)) == REST  # чисто было — нечего убирать
    assert REST not in HOUSE_ACCEPTING  # покой — не вердикт, дом ждёт работы


def test_house_cycle_repeats_every_day() -> None:
    """Ритуал повторяем: дом чист → новый день → снова дом чист."""
    day = (WORK_BEGUN, WORK_DONE, CLEANED_UP)
    assert run_word(day) == CLEAN
    assert run_word(day * 2) == CLEAN
    assert run_word(day * 3) == CLEAN


def test_beginning_without_finishing_is_dirt() -> None:
    """Начал два раза без конца — грязь: закон против роя незакрытых дел."""
    assert run_word((WORK_BEGUN, WORK_BEGUN)) == DIRT
    assert run_word((WORK_BEGUN, WORK_DONE, WORK_DONE)) == DIRT


def test_foreign_symbol_is_violation() -> None:
    """Символ «уведомить хозяина» вне Σ: нарушение закона, а не «странность в логах»."""
    ritual = HouseRitual()
    with pytest.raises(RitualViolation, match="Чужой символ"):
        ritual.step("уведомить_хозяина")
    assert ritual.word == [] and ritual.state == REST


def test_ritual_close_is_idempotent() -> None:
    """Убрал за собой — и второй вызов не пачкает: чистый дом не трогаем."""
    ritual = HouseRitual()
    ritual.step(WORK_BEGUN)
    ritual.step(WORK_DONE)
    first = ritual.close()
    assert first["state"] == CLEAN
    assert ritual.cleaned
    assert ritual.close() is None  # идемпотентно
    assert ritual.word == [WORK_BEGUN, WORK_DONE, CLEANED_UP]


def test_ritual_closes_from_unfinished_work() -> None:
    """Работа не завершена — дом всё равно закрывается: закон при любом исходе."""
    ritual = HouseRitual()
    ritual.step(WORK_BEGUN)  # поработал, не сделал
    closed = ritual.close()
    assert closed["state"] == CLEAN  # WORK + уборка → дом чист
    assert closed["word"] == [WORK_BEGUN, CLEANED_UP]


def test_drive_closes_house_on_success() -> None:
    """Автономный прогон: слово принято, дом закрыт по закону."""
    events: list[dict] = []
    pid1 = AutomatonPid1(pid1_demo_specs(), on_event=events.append)
    report = asyncio.run(pid1.drive("выковать флагман из чистого stdlib"))
    assert report.accepted and report.house_cleaned
    assert report.house_word == (WORK_BEGUN, WORK_DONE, CLEANED_UP)
    cleaned = [event for event in events if event["type"] == "house_cleaned"]
    assert cleaned and cleaned[0]["state"] == CLEAN
    steps = [event for event in events if event["type"] == "ritual_step"]
    assert [step["symbol"] for step in steps] == list(report.house_word)


def test_drive_closes_house_even_on_quarantine() -> None:
    """Эмпатия × закон: все дети в карантине — машина жива, дом всё равно чист."""
    async def broken(task: str) -> list[str]:
        raise RuntimeError("брак")

    from polymath import ChildSpec
    from polymath.agent import Agent

    specs = [
        ChildSpec(agent=Agent(name="Раз", skill="a", act=broken), max_restarts=0),
        ChildSpec(agent=Agent(name="Два", skill="b", act=broken), max_restarts=0),
    ]
    events: list[dict] = []
    pid1 = AutomatonPid1(specs, on_event=events.append)
    report = asyncio.run(pid1.drive("невыполнимый мандат"))
    assert not report.accepted
    assert report.final_state == "карантин"
    assert report.house_cleaned  # закон дома исполнен даже при карантине
    assert report.house_word == (WORK_BEGUN, CLEANED_UP)
    assert any(event["type"] == "house_cleaned" for event in events)


def test_empty_mandate_touches_no_house() -> None:
    """Пустой мандат: в доме не работали — ритуал не притворяется убранным."""
    events: list[dict] = []
    pid1 = AutomatonPid1(pid1_demo_specs(), on_event=events.append)
    with pytest.raises(Exception, match="Пустой мандат"):
        asyncio.run(pid1.drive("   "))
    assert not any(event["type"] == "house_cleaned" for event in events)


def test_learn_accepts_equivalent_table() -> None:
    """Обучение: минимизированная таблица входит — поведение доказано неизменным."""
    pid1 = AutomatonPid1(pid1_demo_specs())
    fresh = AutomatonPid1(pid1_demo_specs())
    minimal = minimize(fresh._table, ALPHABET, INITIAL, ACCEPTING)
    canonical_accepting = ACCEPTING & set(minimal)  # «опыт» слит с «доверие»
    proofs = pid1.learn(minimal, accepting=canonical_accepting)
    assert proofs and any("Полнота" in proof for proof in proofs)
    assert pid1._table == minimal  # новая реализация внутри
    report = asyncio.run(pid1.drive("задача после обучения"))
    assert report.accepted and report.house_cleaned  # машина жива и чиста


def test_learn_rejects_behavior_change() -> None:
    """Смена поведения под видом обучения — отвергнута: это другая машина."""
    pid1 = AutomatonPid1(pid1_demo_specs())
    before = {state: dict(row) for state, row in pid1._table.items()}
    stranger = {state: dict(row) for state, row in TABLE.items()}
    stranger["работа"]["pid1_child_up"] = "тупик"  # поведение изменилось
    with pytest.raises(Exception, match="другая машина"):
        pid1.learn(stranger)
    assert pid1._table == before  # старая машина не тронута


def test_learn_rejects_sick_table() -> None:
    """Больная таблица не входит: полнота δ не обсуждается."""
    pid1 = AutomatonPid1(pid1_demo_specs())
    sick = {state: dict(row) for state, row in TABLE.items()}
    del sick["работа"][next(iter(ALPHABET))]
    with pytest.raises(Exception, match="Полнота"):
        pid1.learn(sick)


def test_house_law_agent_runs_the_law() -> None:
    """Домовой: закон исполняется на деле, навык ritual уникален."""
    agent = house_law_agent()
    assert agent.skill == "ritual" and agent.name == "Домовой"
    report = asyncio.run(agent.execute("осмотреть дом после работы"))
    findings = report.findings
    assert any("закон дома" in finding.lower() for finding in findings)
    assert any("уборкой" in finding for finding in findings)
    assert any("не допускается" in finding for finding in findings)
    assert any("ноль нотификаций" in finding for finding in findings)
    assert any("дом чист" in finding for finding in findings)


def test_house_law_agent_rejects_empty_mandate() -> None:
    agent = house_law_agent()
    with pytest.raises(RitualViolation, match="пустого мандата"):
        asyncio.run(agent.execute("   "))
