"""Автомат Полимата: ПИД1 на теории конечных автоматов — агент, который всё делает сам.

Теория (гуру):

- Клини/Чёрч: конечный автомат — пятёрка (Q, Σ, δ, q0, F); слово принимается,
  если вычисление из q0 по δ кончается в допускающем состоянии;
- Мур (1956): минимизация разбиениями — неразличимые состояния сливаются,
  поведение сохраняется;
- Хопкрофт–Уллман: эквивалентность двух автоматов — обход произведения
  автоматов; расхождение = пара состояний, различимая допуском;
- Полнота δ: доопределение до «тупика» (ловушки) — машина не зависает,
  а честно попадает в несвободу.

Своё (выведено, не списано):

- Жизнь экипажа ПИД1 = слово над алфавитом событий; прогон, не принятый
  автоматом, — нарушение теории, а не «странность в логах»;
- Теорема о ядре: на алфавите {запуск, раунд, ребёнок-вверх, ребёнок-вниз}
  автомат ПИД1 эквивалентен OTP one_for_one (обе машины «надзор жив»);
  расхождения — ровно три, все сознательные: карантин, вердикт, деградация;
- Автомат рождается проверенным, минимизирует себя и доказывает,
  что сжатие не изменило поведение (самознание — через Мура);
- Обучение = приём новой таблицы переходов только через verify +
  эквивалентность (экзамены теории), а не правку на глазок;
- Эмпатия: отклонённое слово не убивает машину — ПИД1 жив и просит
  новый мандат. Падение — данные, а не приговор.

Эмерджентность: агент, который сам ведёт экипаж, сам доказывает корректность
своего поведения и сам называет, где сознательно отошёл от гуру.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass

from .agent import Agent
from .orchestrator import Synthesis
from .pid1 import ChildSpec, Event, PolymathPid1, QuarantinedError
from .supervisor import AuditViolation, audit

# Алфавит Σ: события ПИД1 — единственные слова, на которых говорит экипаж.
STARTED = "pid1_started"
ROUND = "pid1_round"
DOWN = "pid1_child_down"
UP = "pid1_child_up"
QUARANTINED = "pid1_quarantined"
VERDICT = "pid1_verdict"
DEGRADED = "pid1_degraded"

ALPHABET: tuple[str, ...] = (STARTED, ROUND, DOWN, UP, QUARANTINED, VERDICT, DEGRADED)

# Ядро — то, что ПИД1 унаследовал честно от OTP one_for_one.
CORE_ALPHABET: tuple[str, ...] = (STARTED, ROUND, UP, DOWN)

# Ядро наших отступлений: то, чего у OTP нет по замыслу.
DEPARTURES: tuple[str, ...] = (QUARANTINED, VERDICT, DEGRADED)

INITIAL = "ожидание"
ACCEPTING = frozenset({"доверие", "опыт"})
SINK = "тупик"

FRACTAL_WORD: tuple[str, ...] = (STARTED, ROUND, UP, VERDICT)


class AutomatonViolation(RuntimeError):
    """Теория нарушена: таблица больна или слово прогона не принято."""


TABLE: dict[str, dict[str, str]] = {
    "ожидание": {
        STARTED: "работа",
        ROUND: SINK,
        DOWN: SINK,
        UP: SINK,
        QUARANTINED: SINK,
        VERDICT: SINK,
        DEGRADED: SINK,
    },
    "работа": {
        STARTED: SINK,
        ROUND: "работа",
        DOWN: "лечение",
        UP: "работа",
        QUARANTINED: "карантин",
        VERDICT: "доверие",
        DEGRADED: "опыт",
    },
    "лечение": {
        STARTED: SINK,
        ROUND: "работа",
        DOWN: "лечение",
        UP: "работа",
        QUARANTINED: "карантин",
        VERDICT: "доверие",
        DEGRADED: "опыт",
    },
    "карантин": {
        STARTED: SINK,
        ROUND: "работа",
        DOWN: SINK,
        UP: SINK,
        QUARANTINED: "карантин",
        VERDICT: SINK,
        DEGRADED: "опыт",
    },
    "доверие": {
        STARTED: SINK,
        ROUND: SINK,
        DOWN: SINK,
        UP: SINK,
        QUARANTINED: SINK,
        VERDICT: SINK,
        DEGRADED: SINK,
    },
    "опыт": {
        STARTED: SINK,
        ROUND: SINK,
        DOWN: SINK,
        UP: SINK,
        QUARANTINED: SINK,
        VERDICT: SINK,
        DEGRADED: SINK,
    },
    SINK: {symbol: SINK for symbol in ALPHABET},
}

# OTP one_for_one в наших символах: рестарт ребёнка не трогает остальных,
# а при breach интенсивности надзор умирает целиком (тупик) — как в OTP.
OTP_TABLE: dict[str, dict[str, str]] = {
    "покой": {
        STARTED: "работа",
        ROUND: SINK,
        DOWN: SINK,
        UP: SINK,
        QUARANTINED: SINK,
        VERDICT: SINK,
        DEGRADED: SINK,
    },
    "работа": {
        STARTED: SINK,
        ROUND: "работа",
        DOWN: "рестарт",
        UP: "работа",
        QUARANTINED: SINK,
        VERDICT: SINK,
        DEGRADED: SINK,
    },
    "рестарт": {
        STARTED: SINK,
        ROUND: "работа",
        DOWN: "рестарт",
        UP: "работа",
        QUARANTINED: SINK,
        VERDICT: SINK,
        DEGRADED: SINK,
    },
    SINK: {symbol: SINK for symbol in ALPHABET},
}

# «Надзор жив» — допускающие состояния обеих машин в теореме о ядре.
PID1_ALIVE = frozenset({"работа", "лечение"})
OTP_ALIVE = frozenset({"работа", "рестарт"})
OTP_INITIAL = "покой"


def _reachable(table: dict[str, dict[str, str]], initial: str) -> set[str]:
    """BFS достижимости из начального состояния."""
    seen = {initial}
    frontier = [initial]
    while frontier:
        state = frontier.pop()
        for target in table[state].values():
            if target not in seen:
                seen.add(target)
                frontier.append(target)
    return seen


def verify(
    table: dict[str, dict[str, str]],
    alphabet: tuple[str, ...],
    initial: str,
    accepting: Iterable[str],
) -> list[str]:
    """Экзамен теории: таблица больна → :class:`AutomatonViolation`; здорова → proofs.

    Доказательства (по определению DFA — Клини/Хопкрофт–Уллман):

    1. детерминизм — таблица и есть функция δ: Q × Σ → Q, строка не знает дублей;
    2. полнота — δ определена на всех символах алфавита во всех состояниях;
    3. достижимость — каждое состояние достижимо из начального;
    4. допуск — существует допускающее состояние;
    5. единственность вердикта — из допускающих нет перехода в допуск.
    """
    accepting_set = frozenset(accepting)
    if not table or initial not in table:
        raise AutomatonViolation("Таблица пуста или начальное состояние не объявлено")
    alphabet_set = set(alphabet)
    for state, row in table.items():
        missing = sorted(alphabet_set - set(row))
        if missing:
            raise AutomatonViolation(
                f"Полнота нарушена: в «{state}» нет символов {', '.join(missing)}"
            )
        alien = sorted(set(row) - alphabet_set)
        if alien:
            raise AutomatonViolation(
                f"Чужой символ в «{state}»: {', '.join(alien)} — δ определена только на Σ"
            )
        unknown = sorted({target for target in row.values() if target not in table})
        if unknown:
            raise AutomatonViolation(
                f"Переход в несуществующее состояние из «{state}»: {', '.join(unknown)}"
            )
    reachable = _reachable(table, initial)
    unreachable = sorted(set(table) - reachable)
    if unreachable:
        raise AutomatonViolation(f"Достижимость нарушена: недостижимы {', '.join(unreachable)}")
    if not accepting_set:
        raise AutomatonViolation("Допуск пуст: автомат не может принять ни одного слова")
    outsiders = sorted(accepting_set - set(table))
    if outsiders:
        raise AutomatonViolation(f"Допуск объявлен вне Q: {', '.join(outsiders)}")
    for state in sorted(accepting_set & reachable):
        double = sorted({t for t in table[state].values() if t in accepting_set})
        if double:
            raise AutomatonViolation(
                f"Вердикт не единственен: из «{state}» есть переход в допуск {', '.join(double)}"
            )
    return [
        (
            f"Детерминизм: таблица — функция δ: Q × Σ → Q ({len(table)} состояний × "
            f"{len(alphabet)} символов)"
        ),
        f"Полнота: все {len(alphabet)} символов определены во всех {len(table)} состояниях",
        f"Достижимость: все {len(table)} состояний достижимы из «{initial}»",
        f"Допуск: слово принимается в {', '.join(sorted(accepting_set))}",
        "Единственность вердикта: из допускающих состояний нет перехода в допуск",
    ]


def minimize(
    table: dict[str, dict[str, str]],
    alphabet: tuple[str, ...],
    initial: str,
    accepting: Iterable[str],
) -> dict[str, dict[str, str]]:
    """Минимизация Мура: слить неразличимые состояния, поведение — без изменений.

    1. Недостижимые состояния отбрасываются (мёртвое знание — не знание).
    2. Разбиение уточняется подписями (блок сам + блоки образов по каждому
       символу) до неподвижной точки.
    3. Каноническое имя блока — имя первого объявленного состояния блока.
    """
    verify(table, alphabet, initial, accepting)
    symbols = list(alphabet)
    accepting_set = frozenset(accepting)
    reachable = _reachable(table, initial)
    states = [state for state in table if state in reachable]
    blocks: dict[str, int] = {state: int(state in accepting_set) for state in states}
    while True:
        fresh: dict[tuple, int] = {}
        renumbered: dict[str, int] = {}
        for state in states:
            signature = (
                blocks[state],
                *[blocks[table[state][symbol]] for symbol in symbols],
            )
            if signature not in fresh:
                fresh[signature] = len(fresh)
            renumbered[state] = fresh[signature]
        if renumbered == blocks:
            break
        blocks = renumbered
    canonical: dict[int, str] = {}
    for state in states:
        canonical.setdefault(blocks[state], state)
    minimal: dict[str, dict[str, str]] = {}
    for state in states:
        row = minimal.setdefault(canonical[blocks[state]], {})
        for symbol in symbols:
            row[symbol] = canonical[blocks[table[state][symbol]]]
    return minimal


def equivalent(
    table_a: dict[str, dict[str, str]],
    initial_a: str,
    accepting_a: Iterable[str],
    table_b: dict[str, dict[str, str]],
    initial_b: str,
    accepting_b: Iterable[str],
    alphabet: tuple[str, ...],
) -> bool:
    """Эквивалентность DFA (Хопкрофт–Уллман): обход произведения автоматов.

    Машины эквивалентны на данном алфавите, если в произведении не достижима
    пара состояний, различимая допуском. Недостающие символы доопределяются
    до «тупика» — полнота δ не обсуждается, а обеспечивается.
    """

    def completed(table: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
        rows = {state: dict(row) for state, row in table.items()}
        for row in rows.values():
            for symbol in alphabet:
                row.setdefault(symbol, SINK)
        rows.setdefault(SINK, {symbol: SINK for symbol in alphabet})
        return rows

    left, right = completed(table_a), completed(table_b)
    accepting_set_a, accepting_set_b = frozenset(accepting_a), frozenset(accepting_b)
    seen = {(initial_a, initial_b)}
    stack = [(initial_a, initial_b)]
    while stack:
        state_a, state_b = stack.pop()
        if (state_a in accepting_set_a) != (state_b in accepting_set_b):
            return False
        for symbol in alphabet:
            pair = (left[state_a][symbol], right[state_b][symbol])
            if pair not in seen:
                seen.add(pair)
                stack.append(pair)
    return True


@dataclass(frozen=True)
class DriveReport:
    """Итог автономного прогона: слово, допуск, вердикты, реестр попыток."""

    mandate: str
    accepted: bool
    final_state: str
    word: tuple[str, ...]
    steps: int
    quarantined: tuple[str, ...]
    attempts: int
    completions: int
    restarts: int
    verdicts: tuple[str, ...]
    proofs: tuple[str, ...]
    synthesis: Synthesis | None
    summary: str


class AutomatonPid1(PolymathPid1):
    """ПИД1, чья жизнь — слово над алфавитом; слово обязано быть принято.

    Автомат рождается проверенным (:func:`verify`), каждое событие ПИД1 —
    символ на входе δ. Прогоны, не принятые автоматом, — нарушение теории.
    """

    motto: str = "Жизнь экипажа — слово; автомат принимает его или называет причину."

    def __init__(
        self,
        specs: Iterable[ChildSpec],
        on_event=None,
        table: dict[str, dict[str, str]] | None = None,
    ) -> None:
        source = TABLE if table is None else table
        self._table: dict[str, dict[str, str]] = {
            state: dict(row) for state, row in source.items()
        }
        self._proofs = verify(self._table, ALPHABET, INITIAL, ACCEPTING)
        self.state = INITIAL
        self.word: list[str] = []
        self._user_sink = on_event
        super().__init__(specs, on_event=self._process)

    def _process(self, event: Event) -> None:
        """Каждый символ алфавита — шаг δ; посторонние события — мимо автомата."""
        symbol = event.get("type")
        if symbol in ALPHABET:
            self.state = self._table[self.state][symbol]
            self.word.append(symbol)
        if self._user_sink is not None:
            self._user_sink(event)
            if symbol in ALPHABET:  # тень шага δ — сразу после события экипажа
                self._user_sink(
                    {
                        "type": "automaton_step",
                        "state": self.state,
                        "symbol": symbol,
                        "step": len(self.word),
                    }
                )

    def finish(self) -> bool:
        """Слово прогона принято: вычисление кончилось в допускающем состоянии."""
        return self.state in ACCEPTING

    def proofs(self) -> list[str]:
        """Теория: экзамен таблицы + минимизация Мура с доказательством эквивалентности."""
        minimal = minimize(self._table, ALPHABET, INITIAL, ACCEPTING)
        saved = equivalent(
            self._table, INITIAL, ACCEPTING, minimal, INITIAL, ACCEPTING, ALPHABET
        )
        return [
            *self._proofs,
            (
                f"Минимизация Мура: {len(self._table)} → {len(minimal)} состояний "
                f"(эквивалентность поведения: {saved})"
            ),
        ]

    async def drive(self, mandate: str, max_rounds: int = 6) -> DriveReport:
        """Автономный цикл без Хозяина: ПИД1 ведёт экипаж, автомат принимает слово,
        Надзиратель аудитит. Отклонённое слово не убивает машину — она просит мандат.
        """
        if not mandate.strip():
            raise AutomatonViolation("Пустой мандат: автомат не принимает пустое слово")
        synthesis: Synthesis | None = None
        verdicts: tuple[str, ...] = ()
        accepted = True
        try:
            synthesis = await self.run(mandate, max_rounds)
        except QuarantinedError:
            accepted = False
            verdicts = ("ПИД1 жив, экипаж пуст — нужен новый мандат",)
        else:
            if not self.finish():
                raise AutomatonViolation(
                    f"Слово прогона отклонено автоматом: финал «{self.state}» не допускается"
                )
            try:
                verdicts = tuple(audit(synthesis))
            except AuditViolation as exc:  # деградация поймана — машина не умирает
                verdicts = (f"Надзиратель отклонил синтез: {exc}",)
        if synthesis is None:
            summary = (
                f"Мандат «{mandate}»: слово из {len(self.word)} символов отклонено "
                f"(финал «{self.state}») — экипаж в карантине, нужен новый мандат"
            )
        else:
            summary = (
                f"Мандат «{mandate}»: слово из {len(self.word)} символов принято → "
                f"«{self.state}»; {synthesis.agents_count} агентов, находок: "
                f"{len(synthesis.findings)}"
            )
        return DriveReport(
            mandate=mandate,
            accepted=accepted,
            final_state=self.state,
            word=tuple(self.word),
            steps=len(self.word),
            quarantined=self.quarantined,
            attempts=self.attempts,
            completions=self.completions,
            restarts=self.restarts,
            verdicts=verdicts,
            proofs=tuple(self.proofs()),
            synthesis=synthesis,
            summary=summary,
        )


def _fractal_specs() -> list[ChildSpec]:
    """Мини-экипаж внутри автомата: Полимат = мультиагент — фрактал."""

    async def core(task: str) -> list[str]:
        await asyncio.sleep(0.02)
        return [
            (
                f"Ядро: таблица {len(TABLE)} состояний × {len(ALPHABET)} символов "
                f"проверена теорией для «{task}»"
            )
        ]

    async def errand(task: str) -> list[str]:
        await asyncio.sleep(0.01)
        state = INITIAL
        for symbol in FRACTAL_WORD:
            state = TABLE[state][symbol]
        verdict = "принято" if state in ACCEPTING else "отклонено"
        return [f"Гонец: пробное слово из {len(FRACTAL_WORD)} символов {verdict} автоматом"]

    return [
        ChildSpec(agent=Agent(name="Ядро", skill="core", act=core)),
        ChildSpec(agent=Agent(name="Гонец", skill="errand", act=errand)),
    ]


def automaton_agent() -> Agent:
    """Автомат как член экипажа: навык ``automata`` — теория исполняется, а не рассказывается.

    Агент сам: проверяет таблицу, минимизирует себя, доказывает теорему о ядре
    (эквивалентность OTP one_for_one) и ведёт собственный фрактальный экипаж.
    """

    async def act(task: str) -> list[str]:
        if not task.strip():
            raise AutomatonViolation("Пустой мандат: автомат не принимает пустое слово")
        proofs = verify(TABLE, ALPHABET, INITIAL, ACCEPTING)
        minimal = minimize(TABLE, ALPHABET, INITIAL, ACCEPTING)
        compressed = equivalent(
            TABLE, INITIAL, ACCEPTING, minimal, INITIAL, ACCEPTING, ALPHABET
        )
        core_theorem = equivalent(
            TABLE, INITIAL, PID1_ALIVE, OTP_TABLE, OTP_INITIAL, OTP_ALIVE, CORE_ALPHABET
        )
        full_theorem = equivalent(
            TABLE, INITIAL, ACCEPTING, OTP_TABLE, OTP_INITIAL, OTP_ALIVE, ALPHABET
        )
        if not compressed or not core_theorem or full_theorem:
            raise AutomatonViolation(
                "Теория сломана: минимизация теряет поведение, ядро расходится "
                "с OTP или отступления исчезли"
            )
        report = await AutomatonPid1(_fractal_specs()).drive(task)
        return [
            (
                f"Автомат: {len(proofs)} доказательств теории (детерминизм, полнота, "
                f"достижимость, допуск, единственность вердикта)"
            ),
            (
                f"Минимизация Мура: {len(TABLE)} → {len(minimal)} состояний, поведение "
                f"сохранено ({compressed})"
            ),
            (
                f"Теорема о ядре: ПИД1 ≡ OTP one_for_one на {len(CORE_ALPHABET)} общих "
                f"символах ({core_theorem})"
            ),
            (
                f"Сознательные отступления от гуру: {', '.join(DEPARTURES)} — на полном "
                f"алфавите эквивалентности нет ({not full_theorem})"
            ),
            report.summary,
        ]

    return Agent(name="Автомат", skill="automata", act=act)
