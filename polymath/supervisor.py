"""Надзиратель: инварианты оркестратора проверяются на каждом прогоне.

Философия не лозунг, а исполняемый код. Надзиратель — агент с уникальным
навыком ``supervision``: после каждого прогона он проверяет три гарантии
Полимата (контракт навыков, параллельность, чистоту синтеза). Нарушение
поднимает :class:`AuditViolation` — как :class:`DuplicateSkillError`,
только после прогона, а не до.

Мораль алгоритма «чтоб впредь не было»: факт о нарушении поднимается
воспроизводимой проверкой, а не взглядом.

Гёделева поправка (вторая теорема Гёделя): непротиворечивая система не
доказывает свою полноту изнутри. Вердикт декларирует собственную неполноту
— см. :data:`LIMITS`; финальный надзор остаётся вне системы.
"""

from __future__ import annotations

from .agent import Agent
from .orchestrator import Synthesis


class AuditViolation(RuntimeError):
    """Инвариант нарушен: «одно другое не исключает» не выполнилось."""


LIMITS: tuple[str, ...] = (
    "Гёдель II: система не доказывает свою полноту изнутри — вердикт не полон",
    "Надзиратель делит инструмент с поднадзорным (perf_counter): сговор часов возможен",
    "Надзиратель не надзирает за собой: его собственный код вне вердикта",
    "Финальный надзор — вне системы: Хозяин, внешние тесты, независимая реализация",
)


def audit(synthesis: Synthesis) -> list[str]:
    """Проверить три гарантии оркестратора над синтезом прогона.

    Вердикт не полон: проверены только выразимые инварианты, тем же
    инструментом, что и поднадзорный код (:data:`LIMITS`).

    :returns: находки-вердикты (по одной на каждую гарантию).
    :raises AuditViolation: при нарушении любого инварианта.
    """

    # 1. Контракт уникальных навыков — перепроверка после прогона.
    skills = [report.skill for report in synthesis.reports]
    duplicates = sorted({skill for skill in skills if skills.count(skill) > 1})
    if duplicates:
        raise AuditViolation(
            "Контракт нарушен: дублируются навыки " + ", ".join(duplicates)
        )
    findings: list[str] = [f"Контракт: {len(skills)} навыков уникальны"]

    # 2. Параллельность: общее время меньше суммы времён агентов.
    sequential = sum(report.seconds for report in synthesis.reports)
    if len(synthesis.reports) > 1 and synthesis.seconds >= sequential:
        raise AuditViolation(
            f"Параллельность нарушена: {synthesis.seconds:.2f}s >= {sequential:.2f}s"
        )
    findings.append(
        f"Параллельность: {synthesis.seconds:.2f}s < {sequential:.2f}s (суммы времён)"
    )

    # 3. Синтез: без дублей, порядок первых вхождений сохранён.
    merged = list(synthesis.findings)
    if len(merged) != len(set(merged)):
        raise AuditViolation("Синтез загрязнён: дубликаты в находках")
    expected: list[str] = []
    seen: set[str] = set()
    for report in synthesis.reports:
        for finding in report.findings:
            if finding not in seen:
                seen.add(finding)
                expected.append(finding)
    if merged != expected:
        raise AuditViolation("Синтез искажён: порядок первых вхождений нарушен")
    findings.append(
        f"Синтез: {len(merged)} находок без дублей, порядок сохранён"
    )

    return findings


def supervisor_agent() -> Agent:
    """Надзиратель как член экипажа: навык ``supervision`` уникален по контракту.

    Внутри экипажа работает параллельно с остальными и проверяет то,
    что доступно ему самому: мандат (задачу) и собственные находки.
    Надзор над чужими отчётами — после прогона, через :func:`audit`.
    """

    async def act(task: str) -> list[str]:
        if not task.strip():
            raise AuditViolation(
                "Пустой мандат: задача без слов не подлежит исполнению"
            )
        verdicts = [
            f"Мандат непуст: «{task}» принят к надзору",
            "Ритуал проверки воспроизводим: находки дедуплицированы, порядок сохранён",
        ]
        if len(verdicts) != len(set(verdicts)):
            raise AuditViolation("Надзиратель сам загрязнил находки")
        return verdicts

    return Agent(name="Надзиратель", skill="supervision", act=act)
