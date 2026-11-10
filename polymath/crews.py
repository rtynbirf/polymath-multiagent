"""Готовые экипажи Полимата: демо-команда с уникальными навыками."""

from __future__ import annotations

import asyncio

from .agent import Agent
from .pid1 import ChildSpec


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


def pid1_demo_specs() -> list[ChildSpec]:
    """Демо-экипаж ПИД1: Кузнец бракует первые два удара — ПИД1 учит.

    Скаут и Софист стабильны (one_for_one: их это не трогает), Кузнец
    живёт по systemd-политике рестартов и доковывает со третьего удара.
    """

    hammer: dict[str, int] = {"strikes": 0}

    async def scout(task: str) -> list[str]:
        await asyncio.sleep(0.3)
        return [f"Разведка: «{task}» разведано с воздуха"]

    async def smith(task: str) -> list[str]:
        hammer["strikes"] += 1
        if hammer["strikes"] <= 2:
            raise RuntimeError(f"брак в заготовке (удар №{hammer['strikes']})")
        await asyncio.sleep(0.4)
        return [f"Кузнец: «{task}» доковано со {hammer['strikes']}-го удара"]

    async def critic(task: str) -> list[str]:
        await asyncio.sleep(0.2)
        return [f"Софист: «{task}» выдерживает критику"]

    return [
        ChildSpec(agent=Agent(name="Скаут", skill="research", act=scout)),
        ChildSpec(
            agent=Agent(name="Кузнец", skill="coding", act=smith),
            max_restarts=3,
            backoff_base=0.05,
        ),
        ChildSpec(agent=Agent(name="Софист", skill="critique", act=critic)),
    ]
