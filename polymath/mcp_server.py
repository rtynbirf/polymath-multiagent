"""MCP-сервер Полимата: оркестрация как инструменты для любых LLM-хостов.

Запуск: ``polymath mcp`` (транспорт stdio) после
``pip install "polymath-multiagent[mcp]"``.

Хосты с поддержкой MCP (Claude Desktop, IDE-агенты, любые MCP-клиенты)
получают инструменты Полимата и могут оркестрировать экипаж агентов,
не устанавливая ничего сверх протокола.
"""

from __future__ import annotations

from fastmcp import FastMCP

from . import __version__
from .crews import demo_agents
from .orchestrator import PolymathOrchestrator

mcp = FastMCP(
    "polymath-multiagent",
    instructions=(
        "Полимат = Мультиагент: параллельная оркестрация агентов с контрактом "
        "уникальных навыков. Одно другое не исключает. Вызывайте polymath_info(), "
        "чтобы узнать паспорт системы, и orchestrate(task), чтобы прогнать "
        "демо-экипаж из 4 агентов параллельно."
    ),
    version=__version__,
)


@mcp.tool
def polymath_info() -> dict:
    """Паспорт Полимата: версия, мотто, философия и состав демо-экипажа."""
    return {
        "name": "polymath-multiagent",
        "version": __version__,
        "motto": PolymathOrchestrator.motto,
        "philosophy": "Навыки агентов дополняют друг друга и никогда не дублируются.",
        "crew": [{"name": agent.name, "skill": agent.skill} for agent in demo_agents()],
        "orchestration": "asyncio.gather — все агенты стартуют одновременно",
    }


@mcp.tool
async def orchestrate(task: str) -> dict:
    """Прогнать демо-экипаж из 4 агентов параллельно по задаче.

    Агенты: research, architecture, coding, critique. Возвращает находки
    и измеренный выигрыш от параллельности.
    """
    orchestrator = PolymathOrchestrator(demo_agents())
    synthesis = await orchestrator.solve(task)
    return {
        "task": synthesis.task,
        "agents": synthesis.agents_count,
        "parallel_seconds": round(synthesis.seconds, 3),
        "sequential_seconds": round(sum(r.seconds for r in synthesis.reports), 3),
        "findings": list(synthesis.findings),
        "motto": PolymathOrchestrator.motto,
    }


@mcp.resource("polymath://motto")
def motto() -> str:
    """Мотто Полимата — одна строка, ради которой всё затевалось."""
    return PolymathOrchestrator.motto


@mcp.resource("polymath://skills")
def skills() -> dict:
    """Навыки демо-экипажа: каждый уникален, один другое не исключает."""
    return {"skills": [agent.skill for agent in demo_agents()]}
