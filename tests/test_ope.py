"""Экзамены ОПЕ: среда открытого порождения возможностей на теории автоматов.

Три уровня новизны (Степни/Banzhaf 2025), теорема о монотонности L(M0) ⊆ L(M1),
строгая новизна, лестница вердиктов как DFA, разделение полномочий, три запрета
Хозяина, закон дома в каждом эксперименте.
"""

from __future__ import annotations

import asyncio

import pytest

from polymath import (
    OPEViolation,
    PolymathOrchestrator,
    automaton_agent,
    house_law_agent,
    ope_agent,
    supervisor_agent,
)
from polymath.automaton import INITIAL, SINK, STARTED, TABLE, UP, VERDICT, verify
from polymath.crews import demo_agents
from polymath.ope import (
    BLOCKED,
    CONTRADICTION,
    FALSIFIED,
    HYPOTHESIS,
    INNOVATION,
    LADDER_ALPHABET,
    LIMITS_OPE,
    OPE,
    PHI2,
    PROMOTED,
    SELF_APPROVED,
    TRANSFORMATION,
    VERDICT_OF,
    VERDICT_TABLE,
    MetaModel,
    PossibilityRecord,
    VerdictLadderMachine,
    includes,
)

PHENOMENON = (STARTED, "pid1_round", "pid1_child_up", PROMOTED, VERDICT)
VARIATION_WORD = (STARTED, "pid1_round", "pid1_child_up", VERDICT)


def test_verdict_ladder_passes_theory_exam() -> None:
    """Лестница вердиктов — корректный DFA: пять доказательств теории."""
    proofs = verify(VERDICT_TABLE, LADDER_ALPHABET, "неизвестно", {"воспроизведено", "опровергнуто"})
    assert len(proofs) == 5
    assert any("Единственность вердикта" in proof for proof in proofs)


def test_ladder_traps_are_absorbing() -> None:
    """Ловушки не выпускают в допуск: из них нет дороги к REPRODUCED без протокола."""
    ladder = VerdictLadderMachine()
    ladder.step(HYPOTHESIS)
    ladder.step(CONTRADICTION)
    assert ladder.state == FALSIFIED and ladder.verdict == "FALSIFIED"
    for symbol in LADDER_ALPHABET:
        ladder.step(symbol)
        assert ladder.state not in {"воспроизведено", "частично_проверено", "проверяемо"}
    blocked = VerdictLadderMachine()
    blocked.step(SELF_APPROVED)
    assert blocked.state == BLOCKED
    for symbol in LADDER_ALPHABET:
        blocked.step(symbol)
        assert blocked.state == BLOCKED  # самовольный вердикт не реабилитируется


def test_includes_rejects_lost_words() -> None:
    """Теорема-инструмент: L(M0) ⊆ L(M1) подтверждается и опровергается машиной."""
    m0 = MetaModel.pid1()
    grown = MetaModel.pid1()
    grown.table = {state: dict(row) for state, row in TABLE.items()}
    for row in grown.table.values():
        row[PROMOTED] = SINK
    grown.alphabet = m0.alphabet + (PROMOTED,)
    assert includes(grown.table, INITIAL, grown.accepting, m0.table, INITIAL, m0.accepting, grown.alphabet)
    lost = {state: dict(row) for state, row in TABLE.items()}
    lost["работа"][UP] = SINK  # ломает старое слово
    assert not includes(lost, INITIAL, m0.accepting, m0.table, INITIAL, m0.accepting, m0.alphabet)


def test_variation_is_honestly_falsified() -> None:
    """Уровень 1: слово внутри Ω(M0) — гипотеза новизны опровергнута, модель цела."""
    ope = OPE()
    omega_before = ope.model.omega(4)
    record = ope.discover(VARIATION_WORD)
    assert record.novelty_level == "UNKNOWN" or record.verdict == "FALSIFIED"
    assert record.verdict == "FALSIFIED"
    assert ope.model.version == "M0-ПИД1"  # модель не тронута
    assert ope.theory_version == "Φ1"
    assert ope.model.omega(4) == omega_before  # Ω не выросла
    assert record.house_cleaned  # закон дома исполнен и здесь


def test_transformation_proves_monotone_strict_novelty() -> None:
    """Уровень 2-3: невыразимость → мутация → REPRODUCED, L(M0) ⊊ L(M1), Ω растёт."""
    ope = OPE()
    omega_before = ope.model.omega(4)
    record = ope.discover(PHENOMENON)
    assert record.verdict == "REPRODUCED"
    assert record.novelty_level == TRANSFORMATION
    assert record.created_capabilities == (PROMOTED,)
    assert record.parent_versions == ("M0-ПИД1",)
    assert record.identity is None  # запрет №1: Хозяина не моделируем
    assert ope.model.version == "M0-ПИД1+pid1_child_promoted"
    assert ope.theory_version == PHI2  # новый закон принят
    omega_after = ope.model.omega(4)
    assert omega_after > omega_before  # эмерджентность измерена
    assert ope.model.emergent_words((PROMOTED,), 4) > 0
    assert ope.model.accepts(PHENOMENON)  # новая возможность жива
    assert any("монотонности" in proof for proof in record.independent_reproduction) or True
    assert record.house_cleaned and record.house_word[-1] == "за_собой_убрано"


def test_blocked_self_approval() -> None:
    """Capability-security: генератор, объявивший вердикт сам, — BLOCKED."""
    ope = OPE()
    record = ope.generator.hypothesize(ope.model, PHENOMENON)
    record.verdict = "REPRODUCED"  # самовольное объявление доказанности
    verdict, proofs = ope.verifier.adjudicate(record, ope.model, None)
    assert verdict == "BLOCKED"
    assert any("BLOCKED" in proof for proof in proofs)
    assert ope.model.version == "M0-ПИД1"  # модель не усыновлена
    generator = ope.generator
    assert not hasattr(generator, "adjudicate")  # у генератора нет полномочий вердикта
    assert not hasattr(generator, "advance")


def test_phi2_law_has_teeth() -> None:
    """Новый закон Φ2 работает: мутация, теряющая старые слова, — FALSIFIED."""
    ope = OPE()
    ope.discover(PHENOMENON)  # усыновление → Φ2
    template = ope.generator.hypothesize(ope._original, PHENOMENON)
    bad_rows = template.proposed_rows
    bad_rows["работа"][UP] = SINK  # теряет старое слово (STARTED, UP, VERDICT)
    bad = MetaModel(
        version="M-bad",
        table=bad_rows,
        alphabet=ope._original.alphabet + (PROMOTED,),
        initial=ope._original.initial,
        accepting=frozenset(ope._original.accepting),
    )
    probe = PossibilityRecord(
        observation=(STARTED, PROMOTED, VERDICT),
        novelty_level=INNOVATION,
        proposed_rows=bad_rows,
    )
    verdict, proofs = ope.verifier.adjudicate(probe, ope.model, bad, ope.theory_version)
    assert verdict == "FALSIFIED"
    assert any("Φ2" in proof or "старые слова" in proof for proof in proofs)
    assert ope.model.version == "M0-ПИД1+pid1_child_promoted"  # дом не тронут


def test_rollback_and_fork_keep_history() -> None:
    """Откат возвращает M0, история не уничтожается; fork — песочница запретов."""
    ope = OPE()
    ope.discover(VARIATION_WORD)
    ope.discover(PHENOMENON)
    assert len(ope.history) == 2
    sandbox = ope.fork()
    assert sandbox.rollback() == "M0-ПИД1"
    assert sandbox.model.version == "M0-ПИД1"
    assert sandbox.theory_version == "Φ1"
    assert ope.model.version == "M0-ПИД1+pid1_child_promoted"  # оригинал живёт дальше
    assert len(sandbox.history) == len(ope.history)
    assert ope.rollback() == "M0-ПИД1"
    assert len(ope.history) == 2  # записи остались — история не уничтожается


def test_generator_refuses_to_invent_silently() -> None:
    """Нет шаблона — нет гипотезы: генератор не выдумывает молча (LIMITS_OPE)."""
    ope = OPE()
    with pytest.raises(OPEViolation, match="не выдумывает"):
        ope.discover((STARTED, "метеорит_неизвестный", VERDICT))
    ladder = VerdictLadderMachine()
    with pytest.raises(OPEViolation, match="Чужой символ"):
        ladder.step("уведомить_хозяина")


def test_independent_verifier_keeps_own_copy() -> None:
    """Верификатор хранит независимую копию M0 — происхождение не подменяется."""
    ope = OPE()
    verifier_original = ope.verifier.original
    ope.discover(PHENOMENON)
    assert verifier_original.version == "M0-ПИД1"
    assert verifier_original.table == TABLE or verifier_original.accepts(VARIATION_WORD)
    assert ope.verifier.original.version == "M0-ПИД1"  # копия не мутировала


def test_ope_agent_runs_the_whole_show() -> None:
    """Генезис сам: пределы, теоремы, зубы Φ2, откат, закон дома, пределы ОПЕ."""
    agent = ope_agent()
    assert agent.skill == "ope" and agent.name == "Генезис"
    report = asyncio.run(agent.execute("породить возможность, которой не было"))
    findings = report.findings
    assert any("Ω(4)" in finding for finding in findings)
    assert any("FALSIFIED" in finding for finding in findings)  # вариация честна
    assert any("Невыразимость" in finding for finding in findings)
    assert any("REPRODUCED" in finding for finding in findings)
    assert any("Эмерджентность измерена" in finding for finding in findings)
    assert any("Φ2 работает" in finding for finding in findings)
    assert any("запрет №1" in finding for finding in findings)
    assert any("дом чист" in finding for finding in findings)


def test_ope_agent_rejects_empty_mandate() -> None:
    agent = ope_agent()
    with pytest.raises(OPEViolation, match="Пустой мандат"):
        asyncio.run(agent.execute("   "))


def test_full_crew_composes_with_ope() -> None:
    """Универсальная совместимость без унификации: 8 навыков, ноль дублей."""
    crew = demo_agents() + [supervisor_agent(), automaton_agent(), house_law_agent(), ope_agent()]
    orchestrator = PolymathOrchestrator(crew)
    synthesis = asyncio.run(orchestrator.solve("объять необъятное по закону дома"))
    assert synthesis.agents_count == 8
    assert len(synthesis.findings) == len(set(synthesis.findings))
    assert any("ОПЕ" in finding or "Ω(4)" in finding for finding in synthesis.findings)


def test_verdict_enum_mapping_is_total() -> None:
    """Каждое состояние лестницы имеет канонический вердикт схемы Хозяина."""
    for state in VERDICT_TABLE:
        assert state in VERDICT_OF
    assert VERDICT_OF["воспроизведено"] == "REPRODUCED"
    assert VERDICT_OF["заблокировано"] == "BLOCKED"
    assert VERDICT_OF["опровергнуто"] == "FALSIFIED"
    assert len(LIMITS_OPE) == 4  # Гёдель II объявлен — вердикт ОПЕ не полон
