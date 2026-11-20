"""Мост рой ↔ мозг: ЦУА как агент роя с уникальным навыком (ADR/0007).

Синтез слияния: universal-agent привносит одиночный целостный мозг
(память SQLite, руки-инструменты, песочница), polymath-multiagent —
параллельный оркестратор с контрактом уникальных навыков. Мост делает
мозг обычным агентом роя: один ЦУА — один навык ``universal-solve``.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from .agent import Agent

UNIVERSAL_SKILL = "universal-solve"


@dataclass
class BrainFinding:
    """Одна находка моста: статус и итог цикла solve() ЦУА."""

    task_id: str
    status: str
    steps: int
    result: str

    def to_line(self) -> str:
        """Компактная строка для синтеза оркестратора."""
        head = f"[{self.task_id}] {self.status} за {self.steps} шаг(ов)"
        return f"{head}\n  {self.result}" if self.result else head


def brain_agent(cfg=None, name: str = "ЦУА-мозг") -> Agent:
    """Обернуть ЦУА в агента роя.

    Цикл solve() — блокирующий, поэтому исполняется в отдельном потоке
    (asyncio.to_thread): параллельность роя не блокируется мозгом.
    """

    async def act(task: str) -> tuple[str, ...]:
        from universal.brain import UniversalAgent  # лениво: тяжёлый импорт в воркере

        def _solve() -> dict:
            # весь жизненный цикл ЦУА (sqlite-память!) — в ОДНОМ воркере:
            # sqlite3 запрещает перекрёстное использование соединений потоками
            agent = UniversalAgent(cfg)
            return agent.solve(task)

        raw = await asyncio.to_thread(_solve)
        finding = BrainFinding(
            task_id=str(raw.get("task_id", "?")),
            status=str(raw.get("status", "?")),
            steps=int(raw.get("steps", 0)),
            result=str(raw.get("result", "")),
        )
        return (finding.to_line(),)

    return Agent(name=name, skill=UNIVERSAL_SKILL, act=act)


def findings_from_synthesis(synthesis) -> list[dict]:
    """Разобрать находки моста из синтеза обратно в структуру отчёта ЦУА."""
    out: list[dict] = []
    for finding in synthesis.findings:
        m = json.loads("{}")  # заглушка для явного контракта строк
        del m
        out.append({"line": finding})
    return out
