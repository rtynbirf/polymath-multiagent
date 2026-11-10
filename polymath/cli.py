"""CLI Полимата: живая демонстрация параллельной мультиагентности."""

from __future__ import annotations

import argparse
import asyncio
import sys

from .agent import Agent
from .orchestrator import PolymathOrchestrator, Synthesis

MOTTO = "Одно другое не исключает."

BANNER = r"""
 _          _ _                                    _       _
| |__   ___| | | ___ _   _ _ __ ___   ___ _ __   __| |  __| | _____   __
| '_ \ / _ \ | |/ _ \ | | | '_ ` _ \ / _ \ '_ \ / _` | / _` |/ _ \ \ / /
| |_) |  __/ | |  __/ |_| | | | | | |  __/ | | | (_| || (_| |  __/\ V /
|_.__/ \___|_|_|\___|\__,_|_| |_| |_|\___|_| |_|\__,_| \__,_|\___| \_/
              ПОЛИМАТ = МУЛЬТИАГЕНТ  |  v0.1.0
"""


def _demo_agents() -> list[Agent]:
    """Четыре агента с разными навыками и разной «скоростью»."""

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


def run_demo() -> Synthesis:
    """Прогнать демо-оркестрацию и вернуть синтез (удобно для тестов)."""
    orchestrator = PolymathOrchestrator(_demo_agents())
    synthesis = asyncio.run(orchestrator.solve("построить уникальный проект"))
    print(BANNER)
    print(f"Мотто: {MOTTO}")
    print("-" * 60)
    for report in synthesis.reports:
        print(report.to_lines())
    print("-" * 60)
    print(synthesis.summary())
    print(f"\nМотто ещё раз, потому что правда: {MOTTO}")
    return synthesis


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI: ``polymath`` или ``polymath demo``."""
    parser = argparse.ArgumentParser(
        prog="polymath",
        description="Полимат = Мультиагент: параллельная оркестрация уникальных навыков",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="demo",
        choices=["demo"],
        help="команда (по умолчанию — demo)",
    )
    args = parser.parse_args(argv)
    if args.command == "demo":
        run_demo()
    return 0


if __name__ == "__main__":
    sys.exit(main())
