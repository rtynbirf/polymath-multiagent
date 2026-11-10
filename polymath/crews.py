"""Готовые экипажи Полимата: демо-команда с уникальными навыками."""

from __future__ import annotations

import asyncio

from .agent import Agent


def demo_agents() -> list[Agent]:
    """Четыре агента с разными навыками и разной «скоростью».

    Используется в ``polymath demo``, MCP-сервере и живом дашборде:
    один и тот же экипаж — три сцены, одно мотто.
    """

    async def scout(task: str) -> list[str]:
        await asyncio.sleep(0.3)
        return [
            f"Разведка: собран контекст по «{task}»",
            "Разведка: мировые аналоги найдены и проанализированы",
        ]

    async def architect(task: str) -> list[str]:
        await asyncio.sleep(0.5)
        return [f"Архитектура: схема из 3 модулей для «{task}» готова"]

    async def coder(task: str) -> list[str]:
        await asyncio.sleep(0.7)
        return [
            f"Код: каркас «{task}» собран",
            "Код: тесты написаны и зелёные",
        ]

    async def critic(task: str) -> list[str]:
        await asyncio.sleep(0.4)
        return [
            "Критика: риски под контролем",
            f"Критика: «{task}» жизнеспособен",
        ]

    return [
        Agent(name="Скаут", skill="research", act=scout),
        Agent(name="Зодчий", skill="architecture", act=architect),
        Agent(name="Кузнец", skill="coding", act=coder),
        Agent(name="Софист", skill="critique", act=critic),
    ]
