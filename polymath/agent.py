"""Агент Полимата: один агент — один уникальный навык."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentReport:
    """Отчёт одного агента о выполненной задаче."""

    agent: str
    skill: str
    findings: tuple[str, ...]
    seconds: float

    def to_lines(self) -> str:
        """Человекочитаемый блок отчёта."""
        head = f"[{self.agent}] ({self.skill}, {self.seconds:.2f}s)"
        body = "\n".join(f"  + {finding}" for finding in self.findings)
        return f"{head}\n{body}" if body else head


Act = Callable[[str], Awaitable[Sequence[str]]]


@dataclass
class Agent:
    """Агент с ровно одним навыком.

    :param name: имя агента (например, «Скаут»).
    :param skill: уникальный навык (например, ``research``). Дубликаты
        запрещены на уровне оркестратора — это контракт «одно другое
        не исключает».
    :param act: асинхронная функция, принимающая строку задачи и
        возвращающая последовательность находок (строк).
    """

    name: str
    skill: str
    act: Act

    async def execute(self, task: str) -> AgentReport:
        """Выполнить задачу и вернуть отчёт с замером времени."""
        started = time.perf_counter()
        findings = tuple(await self.act(task))
        return AgentReport(
            agent=self.name,
            skill=self.skill,
            findings=findings,
            seconds=time.perf_counter() - started,
        )
