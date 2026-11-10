"""CLI Полимата: демо, MCP-сервер и живой дашборд."""

from __future__ import annotations

import argparse
import asyncio
import sys

from .crews import demo_agents
from .orchestrator import PolymathOrchestrator, Synthesis

MOTTO = "Одно другое не исключает."

BANNER = r"""
 _          _ _                                    _       _
| |__   ___| | | ___ _   _ _ __ ___   ___ _ __   __| |  __| | _____   __
| '_ \ / _ \ | |/ _ \ | | | '_ ` _ \ / _ \ '_ \ / _` | / _` |/ _ \ \ / /
| |_) |  __/ | |  __/ |_| | | | | | |  __/ | | | (_| || (_| |  __/\ V /
|_.__/ \___|_|_|\___|\__,_|_| |_| |_|\___|_| |_|\__,_| \__,_|\___| \_/
              ПОЛИМАТ = МУЛЬТИАГЕНТ  |  v0.2.0
"""


def run_demo() -> Synthesis:
    """Прогнать демо-оркестрацию и вернуть синтез (удобно для тестов)."""
    orchestrator = PolymathOrchestrator(demo_agents())
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


def run_mcp() -> int:
    """Запустить MCP-сервер (stdio). Требует extra: ``[mcp]``."""
    from .mcp_server import mcp

    mcp.run()
    return 0


def run_dashboard(host: str, port: int) -> int:
    """Запустить живой веб-дашборд оркестрации."""
    from .dashboard import serve

    serve(host=host, port=port)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI: ``polymath {demo|mcp|dashboard}``."""
    parser = argparse.ArgumentParser(
        prog="polymath",
        description="Полимат = Мультиагент: параллельная оркестрация уникальных навыков",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="demo",
        choices=["demo", "mcp", "dashboard"],
        help="команда (по умолчанию — demo)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="хост дашборда (по умолчанию 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="порт дашборда (по умолчанию 8765)"
    )
    args = parser.parse_args(argv)
    if args.command == "demo":
        run_demo()
    elif args.command == "mcp":
        return run_mcp()
    elif args.command == "dashboard":
        return run_dashboard(args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
