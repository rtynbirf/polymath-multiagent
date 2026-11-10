"""CLI Полимата: демо, аудит, ПИД1, автомат, MCP-сервер и живой дашборд."""

from __future__ import annotations

import argparse
import asyncio
import sys

from .crews import demo_agents, pid1_demo_specs
from .orchestrator import PolymathOrchestrator, Synthesis

MOTTO = "Одно другое не исключает."

BANNER = r"""
 _          _ _                                    _       _
| |__   ___| | | ___ _   _ _ __ ___   ___ _ __   __| |  __| | _____   __
| '_ \ / _ \ | |/ _ \ | | | '_ ` _ \ / _ \ '_ \ / _` | / _` |/ _ \ \ / /
| |_) |  __/ | |  __/ |_| | | | | | |  __/ | | | (_| || (_| |  __/\ V /
|_.__/ \___|_|_|\___|\__,_|_| |_| |_|\___|_| |_|\__,_| \__,_|\___| \_/
              ПОЛИМАТ = МУЛЬТИАГЕНТ  |  v0.3.0
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


def run_audit() -> int:
    """Демо-прогон + вердикт Надзирателя по инвариантам оркестратора."""
    from .supervisor import LIMITS, audit

    orchestrator = PolymathOrchestrator(demo_agents())
    synthesis = asyncio.run(orchestrator.solve("построить уникальный проект"))
    verdicts = audit(synthesis)
    print("-" * 60)
    print("[Надзиратель] (supervision)")
    for verdict in verdicts:
        print(f"  + {verdict}")
    print("-" * 60)
    print("ВЕРДИКТ: инварианты соблюдены. Одно другое не исключает.")
    print("ПРЕДЕЛЫ НАДЗОРА (вердикт не полон — Гёдель II):")
    for limit in LIMITS:
        print(f"  ! {limit}")
    return 0


def run_pid1() -> int:
    """Живая самозаживающая оркестрация под началом ПИД1."""
    from .pid1 import PolymathPid1

    def echo(event: dict) -> None:
        kind = event["type"]
        if kind == "pid1_round":
            print(f"[раунд {event['round']}] живых детей: {event['alive']}")
        elif kind == "pid1_child_down":
            print(f"  ⚠ {event['agent']} упал (попытка {event['attempt']}): {event['reason']}")
        elif kind == "pid1_child_up":
            print(f"  ✓ {event['agent']} жив: сердце бьётся №{event['heartbeat']} ({event['seconds']}s)")
        elif kind == "pid1_quarantined":
            print(f"  ✗ {event['agent']} в карантине (падений: {event['failures']}) — экипаж продолжается")

    pid1 = PolymathPid1(pid1_demo_specs(), on_event=echo)
    print(f"ПИД1: {PolymathPid1.motto}")
    print("-" * 60)
    synthesis = asyncio.run(pid1.run("выковать флагман из чистого stdlib"))
    print("-" * 60)
    print(synthesis.summary())
    print(
        f"Реестр попыток: {pid1.attempts} | успехи (зомби переполучены): "
        f"{pid1.completions} | рестарты: {pid1.restarts}"
    )
    print("Пределы надзора не отменены (Гёдель II) — см. polymath audit.")
    return 0


def run_automaton() -> int:
    """Автомат сам ведёт экипаж: теория КА, ПИД1, надзор — ноль Хозяина в контуре."""
    from .automaton import AutomatonPid1

    def echo(event: dict) -> None:
        kind = event["type"]
        if kind == "automaton_step":
            print(f"  δ: {event['symbol']} → {event['state']} (шаг {event['step']})")
        elif kind == "pid1_round":
            print(f"[раунд {event['round']}] живых детей: {event['alive']}")
        elif kind == "pid1_child_down":
            print(f"  ⚠ {event['agent']} упал (попытка {event['attempt']}): {event['reason']}")
        elif kind == "pid1_child_up":
            print(f"  ✓ {event['agent']} жив (сердце №{event['heartbeat']}, {event['seconds']}s)")
        elif kind == "pid1_quarantined":
            print(f"  ✗ {event['agent']} → КАРАНТИН (падений: {event['failures']})")

    pid1 = AutomatonPid1(pid1_demo_specs(), on_event=echo)
    print("АВТОМАТ ПИД1: таблица переходов, теория конечных автоматов, автономия")
    print("-" * 60)
    for proof in pid1.proofs():
        print(f"  + {proof}")
    print("-" * 60)
    report = asyncio.run(pid1.drive("выковать флагман из чистого stdlib"))
    print("-" * 60)
    print(report.summary)
    print(
        f"Реестр попыток: {report.attempts} = {report.completions} успехов "
        f"+ {report.restarts} рестартов (зомби невозможны)"
    )
    for verdict in report.verdicts:
        print(f"  + {verdict}")
    print("Отступления от OTP-гуру сознательны: карантин, вердикт, деградация (docs/OTP.md)")
    print("Пределы надзора не отменены (Гёдель II) — см. polymath audit.")
    return 0


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
    """Точка входа CLI: ``polymath {demo|audit|pid1|mcp|dashboard}``."""
    parser = argparse.ArgumentParser(
        prog="polymath",
        description="Полимат = Мультиагент: параллельная оркестрация уникальных навыков",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="demo",
        choices=["demo", "audit", "pid1", "automat", "mcp", "dashboard"],
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
    elif args.command == "audit":
        return run_audit()
    elif args.command == "pid1":
        return run_pid1()
    elif args.command == "automat":
        return run_automaton()
    elif args.command == "mcp":
        return run_mcp()
    elif args.command == "dashboard":
        return run_dashboard(args.host, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
