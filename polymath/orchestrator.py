"""Оркестратор Полимата: параллельность по умолчанию, навыки без дублей."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterable
from dataclasses import dataclass

from .agent import Agent, AgentReport


class DuplicateSkillError(RuntimeError):
    """Два агента с одним навыком = один исключает другого. Так нельзя."""


@dataclass(frozen=True)
class Synthesis:
    """Синтез: находки всех агентов, слитые в единый результат."""

    task: str
    findings: tuple[str, ...]
    reports: tuple[AgentReport, ...]
    seconds: float

    @property
    def agents_count(self) -> int:
        return len(self.reports)

    def summary(self) -> str:
        """Итоговая сводка с экономией времени от параллельности."""
        sequential_time = sum(report.seconds for report in self.reports)
        saved = sequential_time - self.seconds
        lines = [
            f"Задача: {self.task}",
            f"Агентов: {self.agents_count} | Уникальных навыков: {self.agents_count}",
            (
                f"Время (параллельно): {self.seconds:.2f}s "
                f"вместо {sequential_time:.2f}s (экономия {saved:.2f}s)"
            ),
            "Находки:",
        ]
        lines.extend(f"  • {finding}" for finding in self.findings)
        return "\n".join(lines)


class PolymathOrchestrator:
    """Мотто: «Одно другое не исключает».

    Гарантии оркестратора:

    1. **Контракт уникальных навыков** — при попытке собрать оркестратор
       из агентов с одинаковым навыком поднимается :class:`DuplicateSkillError`.
       Навыки могут только дополнять друг друга.
    2. **Параллельность по умолчанию** — все агенты запускаются строго
       одновременно через ``asyncio.gather``; общее время ≈ времени
       самого медленного агента, а не сумме времён.
    3. **Синтез с дедупликацией** — повторяющиеся находки разных агентов
       склеиваются, порядок первых вхождений сохраняется.
    """

    motto: str = "Одно другое не исключает."

    def __init__(self, agents: Iterable[Agent]) -> None:
        self._agents: tuple[Agent, ...] = tuple(agents)
        skills = [agent.skill for agent in self._agents]
        duplicates = sorted({skill for skill in skills if skills.count(skill) > 1})
        if duplicates:
            raise DuplicateSkillError(
                "Навыки должны дополнять друг друга, а не дублироваться. "
                f"Повторяются: {', '.join(duplicates)}"
            )

    @property
    def agents(self) -> tuple[Agent, ...]:
        return self._agents

    async def solve(self, task: str) -> Synthesis:
        """Запустить всех агентов параллельно и синтезировать результат."""
        started = time.perf_counter()
        reports = await asyncio.gather(*(agent.execute(task) for agent in self._agents))
        elapsed = time.perf_counter() - started
        return self._synthesize(task, tuple(reports), elapsed)

    def _synthesize(
        self,
        task: str,
        reports: tuple[AgentReport, ...],
        seconds: float,
    ) -> Synthesis:
        seen: set[str] = set()
        unique: list[str] = []
        for report in reports:
            for finding in report.findings:
                if finding not in seen:
                    seen.add(finding)
                    unique.append(finding)
        return Synthesis(task=task, findings=tuple(unique), reports=reports, seconds=seconds)
