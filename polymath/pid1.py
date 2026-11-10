"""ПИД1 Полимата: родоначальник экипажа — init(8) × OTP-надзор × LFS-дух.

Практики гуру, из которых выведено своё:

- Unix init(8) и systemd: ПИД1 не умирает, переполучает зомби, рестартует
  с экспоненциальной паузой (RestartSec/RestartSteps/RestartMaxDelaySec);
- Erlang/OTP: стратегия one_for_one — падение ребёнка не трогает остальных;
- «Let it crash»: не предсказывать сбои, а структурировать систему вокруг них;
- Linux From Scratch: всё из исходников — ноль рантайм-зависимостей.

Своё (выведено, не списано):

- Карантин: исчерпавший бюджет падений ребёнок замораживается, экипаж
  продолжается без него (OTP при breach интенсивности валит весь надзор);
- Реестр попыток: каждая попытка учтена — зомби невозможны
  (инвариант: attempts == completions + restarts);
- Контракт уникальных навыков + вердикт с гёделевыми пределами;
- Эмпатия: падение — данные, а не приговор.

Эмерджентность: экипаж, который не может умереть и не может дублировать навыки.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .agent import Agent, AgentReport
from .orchestrator import DuplicateSkillError, Synthesis
from .supervisor import LIMITS, audit


class QuarantinedError(RuntimeError):
    """Все дети в карантине: ПИД1 жив, но экипаж пуст."""


@dataclass(frozen=True)
class ChildSpec:
    """Спецификация ребёнка ПИД1: агент + политика рестарта (systemd-стиль).

    :param agent: агент с уникальным навыком (контракт Полимата).
    :param max_restarts: бюджет падений за жизнь ребёнка; исчерпан — карантин.
    :param backoff_base: базовая пауза перед рестартом (systemd ``RestartSec``).
    :param backoff_cap: потолок паузы (systemd ``RestartMaxDelaySec``).
    """

    agent: Agent
    max_restarts: int = 3
    backoff_base: float = 0.05
    backoff_cap: float = 1.0


@dataclass
class ChildState:
    """Живое состояние ребёнка: падения, сердцебиение, карантин."""

    spec: ChildSpec
    failures: int = 0
    heartbeats: int = 0
    quarantined: bool = False

    def next_backoff(self) -> float:
        """Экспоненциальная пауза systemd: base · 2^failures, не выше cap."""
        return min(self.spec.backoff_base * (2**self.failures), self.spec.backoff_cap)


Event = dict
EventSink = Callable[[Event], None]


class PolymathPid1:
    """ПИД1: первый из первых, родитель всех агентов. Сам не умирает."""

    motto: str = "ПИД1 не умирает: падение ребёнка — данные, а не приговор."

    def __init__(
        self, specs: Iterable[ChildSpec], on_event: EventSink | None = None
    ) -> None:
        spec_list = list(specs)
        skills = [spec.agent.skill for spec in spec_list]
        duplicates = sorted({skill for skill in skills if skills.count(skill) > 1})
        if duplicates:
            raise DuplicateSkillError(
                "Навыки должны дополнять друг друга, а не дублироваться. "
                f"Повторяются: {', '.join(duplicates)}"
            )
        self._states: list[ChildState] = [ChildState(spec) for spec in spec_list]
        self._on_event = on_event
        self.attempts: int = 0  # реестр попыток — зомби невозможны
        self.completions: int = 0  # переполученные успехи
        self.restarts: int = 0  # падения, ушедшие в рестарт/карантин

    @property
    def children(self) -> tuple[str, ...]:
        return tuple(state.spec.agent.name for state in self._states)

    @property
    def quarantined(self) -> tuple[str, ...]:
        return tuple(
            state.spec.agent.name for state in self._states if state.quarantined
        )

    def _emit(self, event: Event) -> None:
        if self._on_event is not None:
            self._on_event(event)

    async def _run_child(self, state: ChildState, task: str) -> AgentReport | None:
        """Let it crash: ребёнку разрешено падать — ПИД1 всё учтёт."""
        self.attempts += 1
        try:
            report = await state.spec.agent.execute(task)
        except Exception as exc:  # noqa: BLE001 — падение — данные, а не приговор
            state.failures += 1
            self._emit(
                {
                    "type": "pid1_child_down",
                    "agent": state.spec.agent.name,
                    "skill": state.spec.agent.skill,
                    "attempt": state.failures,
                    "reason": repr(exc),
                }
            )
            return None
        state.heartbeats += 1
        self._emit(
            {
                "type": "pid1_child_up",
                "agent": state.spec.agent.name,
                "skill": state.spec.agent.skill,
                "heartbeat": state.heartbeats,
                "seconds": round(report.seconds, 3),
            }
        )
        return report

    def _reap(
        self, task: str, reports: list[AgentReport], seconds: float
    ) -> Synthesis:
        """Переполучить находки: дедупликация с сохранением первых вхождений."""
        seen: set[str] = set()
        findings: list[str] = []
        for report in reports:
            for finding in report.findings:
                if finding not in seen:
                    seen.add(finding)
                    findings.append(finding)
        return Synthesis(
            task=task, findings=tuple(findings), reports=tuple(reports), seconds=seconds
        )

    async def run(self, task: str, max_rounds: int = 6) -> Synthesis:
        """Крутить раунды до чистого прохода; сам не умирает — изолирует брак."""
        self._emit(
            {
                "type": "pid1_started",
                "children": list(self.children),
                "motto": self.motto,
            }
        )
        harvest: list[AgentReport] = []  # успехи нечистых раундов не пропадают
        for round_no in range(1, max_rounds + 1):
            alive = [state for state in self._states if not state.quarantined]
            if not alive:
                raise QuarantinedError(
                    "Все дети в карантине: ПИД1 жив, экипаж пуст — нужен новый мандат"
                )
            self._emit({"type": "pid1_round", "round": round_no, "alive": len(alive)})
            started = time.perf_counter()
            results = await asyncio.gather(
                *(self._run_child(state, task) for state in alive)
            )
            seconds = time.perf_counter() - started
            pairs = list(zip(alive, results))
            down = [state for state, result in pairs if result is None]
            up = [result for result in results if result is not None]
            self.completions += len(up)
            self.restarts += len(down)
            harvest.extend(up)
            for state, result in pairs:
                if result is None and state.failures > state.spec.max_restarts:
                    state.quarantined = True
                    self._emit(
                        {
                            "type": "pid1_quarantined",
                            "agent": state.spec.agent.name,
                            "skill": state.spec.agent.skill,
                            "failures": state.failures,
                        }
                    )
            if not down:
                synthesis = self._reap(task, up, seconds)
                self._emit(
                    {
                        "type": "pid1_verdict",
                        "rounds": round_no,
                        "verdicts": audit(synthesis),
                        "limits": list(LIMITS),
                        "attempts": self.attempts,
                    }
                )
                return synthesis
            for state in down:  # systemd RestartSec: пауза перед новым подъёмом
                await asyncio.sleep(state.next_backoff())
        if harvest:  # чистого прохода не случилось — отдаём собранное честно
            synthesis = self._reap(task, harvest, 0.0)
            self._emit(
                {
                    "type": "pid1_degraded",
                    "attempts": self.attempts,
                    "quarantined": list(self.quarantined),
                }
            )
            return synthesis
        raise QuarantinedError("Раунды исчерпаны без единого успеха — экипаж не взлетел")
