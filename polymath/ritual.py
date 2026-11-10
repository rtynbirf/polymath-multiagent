"""Закон Дома Полимата: поработал → сделал → убрал за собой.

Гуру, из которых выведено своё:

- Boy Scout Rule (Р. Мартин, «Чистый код»): оставь лагерь чище, чем нашёл;
- 5S/кайдзен: рабочее место после работы возвращается в исходное состояние;
- systemd shutdown и Python ``finally``: завершение — часть работы, а не
  пожелание; дом закрывается при любом исходе прогона;
- Клини/Хопкрофт–Уллман: конечный автомат — пятёрка (Q, Σ, δ, q0, F);
  слово принимается, если вычисление кончилось в допускающем состоянии.

Закон Дома (своё, обязательный алгоритм действий):

- Σ = {работа_начата, работа_сделана, за_собой_убрано}. В алфавите **нет**
  символа «уведомить хозяина»: дом закрывает и решает всё сам, ноль
  нотификаций — это структура алфавита, а не обещание;
- принять можно только слово, кончающееся уборкой: «сделано» без «за_собой_
  убрано» не допускается — закон структурный, а не заповедь на стене;
- δ доопределена до тупика «грязь»: машина не зависает, а честно попадает
  в несвободу — поработал и не убрал, дом грязен навсегда;
- ритуал повторяем: из «дом чист» новый день начинается работой;
- ритуал обязателен для всех: Автомат ПИД1 в конце любого прогона
  (успех или карантин) закрывает дом через ``finally``.

Эмерджентность: закон, который нельзя нарушить, потому что он — таблица
переходов, а не инструкция.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from itertools import product

from .agent import Agent

REST = "покой"
WORK = "работа"
MADE = "сделано"
CLEAN = "дом чист"
DIRT = "грязь"

WORK_BEGUN = "работа_начата"
WORK_DONE = "работа_сделана"
CLEANED_UP = "за_собой_убрано"

HOUSE_ALPHABET: tuple[str, ...] = (WORK_BEGUN, WORK_DONE, CLEANED_UP)
HOUSE_ACCEPTING = frozenset({CLEAN})

HOUSE_TABLE: dict[str, dict[str, str]] = {
    REST: {WORK_BEGUN: WORK, WORK_DONE: DIRT, CLEANED_UP: REST},
    WORK: {WORK_BEGUN: DIRT, WORK_DONE: MADE, CLEANED_UP: CLEAN},
    MADE: {WORK_BEGUN: DIRT, WORK_DONE: DIRT, CLEANED_UP: CLEAN},
    CLEAN: {WORK_BEGUN: WORK, WORK_DONE: DIRT, CLEANED_UP: DIRT},
    DIRT: {symbol: DIRT for symbol in HOUSE_ALPHABET},
}


class RitualViolation(RuntimeError):
    """Закон Дома нарушен: чужой символ или принято слово без уборки."""


def _verify():
    """Теория подключается лениво: automaton не импортирует ritual наверху."""
    from .automaton import verify

    return verify


class HouseRitual:
    """Живой ритуал дома: каждый шаг — символ Σ; принимается только чистота."""

    motto: str = "Поработал? Сделал? Убрал за собой. Дом закрывается сам."

    def __init__(self, on_step: Callable[[dict], None] | None = None) -> None:
        self._table: dict[str, dict[str, str]] = {
            state: dict(row) for state, row in HOUSE_TABLE.items()
        }
        self._proofs = _verify()(self._table, HOUSE_ALPHABET, REST, HOUSE_ACCEPTING)
        self.state: str = REST
        self.word: list[str] = []
        self._on_step = on_step

    def proofs(self) -> list[str]:
        """Доказательства теории, с которыми дом родился."""
        return list(self._proofs)

    def step(self, symbol: str) -> str:
        """Один шаг δ; чужой символ — нарушение закона, а не «странность в логах»."""
        if symbol not in HOUSE_ALPHABET:
            raise RitualViolation(
                f"Чужой символ «{symbol}»: закон дома знает только "
                f"{', '.join(HOUSE_ALPHABET)}"
            )
        self.state = self._table[self.state][symbol]
        self.word.append(symbol)
        if self._on_step is not None:
            self._on_step(
                {
                    "type": "ritual_step",
                    "state": self.state,
                    "symbol": symbol,
                    "step": len(self.word),
                }
            )
        return self.state

    @property
    def cleaned(self) -> bool:
        """Дом чист: вычисление кончилось в допускающем состоянии."""
        return self.state in HOUSE_ACCEPTING

    def close(self) -> dict | None:
        """Убрать за собой — идемпотентно: чистый дом не трогаем.

        Из «работа» и «сделано» уборка доопределена таблицей до «дом чист»:
        закон исполняется при любом исходе прогона, без исключений.
        """
        if self.cleaned:
            return None
        if self.state == REST:  # в доме не работали — убирать нечего
            event = {"type": "house_cleaned", "state": self.state, "steps": 0, "word": []}
            if self._on_step is not None:
                self._on_step(event)
            return event
        self.step(CLEANED_UP)
        event = {
            "type": "house_cleaned",
            "state": self.state,
            "steps": len(self.word),
            "word": list(self.word),
        }
        if self._on_step is not None:
            self._on_step(event)
        return event


@dataclass(frozen=True)
class HouseExam:
    """Итог исполняемого закона: перебор всех слов до max_len включительно."""

    max_len: int
    accepted: int
    rejected: int
    made_without_cleanup_accepted: bool
    notify_free: bool
    accepted_all_end_cleaned: bool


def house_exam(max_len: int = 4) -> HouseExam:
    """Перебрать все слова Σ* до ``max_len``: закон исполняется, а не рассказывается.

    Инварианты закона, проверяемые перебором:

    1. принимаются **только** слова, кончающиеся «за_собой_убрано»;
    2. «сделал и не убрал» отвергается навсегда (грязь не допускается);
    3. в алфавите нет символа уведомлений — дом закрывается сам.
    """
    verify = _verify()
    verify(HOUSE_TABLE, HOUSE_ALPHABET, REST, HOUSE_ACCEPTING)
    accepted = rejected = 0
    all_end_cleaned = True
    for length in range(1, max_len + 1):
        for word in product(HOUSE_ALPHABET, repeat=length):
            state = REST
            for symbol in word:
                state = HOUSE_TABLE[state][symbol]
            if state in HOUSE_ACCEPTING:
                accepted += 1
                if word[-1] != CLEANED_UP:
                    all_end_cleaned = False
            else:
                rejected += 1
    made_state = HOUSE_TABLE[HOUSE_TABLE[REST][WORK_BEGUN]][WORK_DONE]
    made_without_cleanup_accepted = made_state in HOUSE_ACCEPTING
    notify_free = all(
        not any(
            token in symbol
            for token in ("уведом", "хозя", "notify", "ждать", "вопрос", "спрос")
        )
        for symbol in HOUSE_ALPHABET
    )
    if not all_end_cleaned:
        raise RitualViolation("Закон сломан: принято слово, не кончающееся уборкой")
    if made_without_cleanup_accepted:
        raise RitualViolation("Закон сломан: «сделано» допущено без уборки")
    if not notify_free:
        raise RitualViolation("Закон сломан: в алфавите появился символ уведомлений")
    return HouseExam(
        max_len=max_len,
        accepted=accepted,
        rejected=rejected,
        made_without_cleanup_accepted=made_without_cleanup_accepted,
        notify_free=notify_free,
        accepted_all_end_cleaned=all_end_cleaned,
    )


def house_law_agent() -> Agent:
    """Домовой Полимата: навык ``ritual`` — закон исполняется, а не рассказывается.

    Агент сам: сдаёт таблицу теории, перебирает все короткие слова,
    доказывает, что «сделал без уборки» не допускается, и закрывает
    собственный ритуал по закону.
    """

    async def act(task: str) -> list[str]:
        if not task.strip():
            raise RitualViolation("Домовой не принимает пустого мандата")
        exam = house_exam()
        ritual = HouseRitual()
        ritual.step(WORK_BEGUN)  # поработал
        ritual.step(WORK_DONE)  # сделал
        closed = ritual.close()  # убрал за собой
        return [
            (
                f"Домовой: закон дома — поработал → сделал → убрал за собой "
                f"({len(HOUSE_TABLE)} состояний × {len(HOUSE_ALPHABET)} символов)"
            ),
            (
                f"Домовой: таблица прошла экзамен теории "
                f"({len(ritual.proofs())} доказательств: детерминизм, полнота, "
                f"достижимость, допуск, единственность вердикта)"
            ),
            (
                f"Домовой: перебор всех слов до {exam.max_len} символов — "
                f"{exam.accepted} принято, {exam.rejected} отвергнуто; принимаются "
                f"только слова, кончающиеся уборкой ({exam.accepted_all_end_cleaned})"
            ),
            (
                f"Домовой: «сделал и не убрал» отвергнуто автоматом "
                f"({not exam.made_without_cleanup_accepted}) — грязь не допускается"
            ),
            (
                f"Домовой: в алфавите нет символа уведомлений "
                f"({exam.notify_free}) — дом закрывается сам, ноль нотификаций"
            ),
            (
                f"Домовой: мандат «{task}» закрыт — {closed['state']} "
                f"(слово ритуала: {' → '.join(closed['word'])})"
            ),
        ]

    return Agent(name="Домовой", skill="ritual", act=act)
