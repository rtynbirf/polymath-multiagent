"""ОПЕ Полимата: среда открытого порождения возможностей — OPE-0, Meta-Model Mutation Lab.

Гуру (исследование Хозяина, 10.11.2026, «Человек ≡ ⟨S,E,Uq,Uv⟩» + мировые практики):

- Степни/Banzhaf (Royal Society, 2025): три уровня новизны — ВАРИАЦИЯ (новое
  слово внутри модели), ИННОВАЦИЯ (новая модель: символы, состояния, правила),
  ТРАНСФОРМАЦИЯ (новая метамодель: меняются сами правила построения моделей);
- POPPER (ICML 2025): проверка на опровержение; создатель гипотезы не объявляет
  её доказанной — генератор и верификатор разделены (capability-based security);
- FAIR/воспроизводимость: происхождение, версии, независимое воспроизведение;
- Local-first и открытая эволюция: своё состояние, откат без потери истории.

Своё (выведено в доме, на теории конечных автоматов):

- Модель = DFA (Q, Σ, δ, q0, F); явление = слово; невыразимость = символ вне Σ
  или путь в «тупик»; пространство возможностей Ω измеримо: |Ω(n)| — число
  принятых слов до длины n (перебор, а не декларация);
- Мутация метамодели принимается только через экзамены: verify (структура) +
  ТЕОРЕМА О МОНОТОННОСТИ L(M0) ⊆ L(M1) (обход произведения автоматов) +
  СТРОГАЯ НОВИЗНА L(M0) ≠ L(M1) — старые возможности не теряются, новые
  принимаются; вместе: L(M0) ⊊ L(M1), доказано машиной;
- Лестница вердиктов — тоже автомат: UNKNOWN → TESTABLE → PARTIALLY_VERIFIED →
  REPRODUCED; ловушки FALSIFIED / INCONCLUSIVE / BLOCKED; самовольный вердикт
  генератора блокируется — полномочия разделены структурно;
- Три запрета Хозяина исполняются кодом: record.identity is None (Хозяина не
  моделируем), множество реализаций (fork, любые таблицы через экзамены),
  развитие = смена Φ, а не подгонка параметров;
- Закон дома: каждый эксперимент — рабочий день ритуала; откат сохраняет M0 —
  история не уничтожается.

Эмерджентность: среда, которая сама находит свой предел, сама предлагает
мутацию метамодели, сама доказывает монотонность и новизну — и сама называет,
где заканчивается наука и начинается гипотеза Хозяина (LIMITS_OPE).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from itertools import product

from .agent import Agent
from .automaton import (
    ACCEPTING,
    ALPHABET,
    DEGRADED,
    DOWN,
    INITIAL,
    QUARANTINED,
    ROUND,
    SINK,
    STARTED,
    TABLE,
    UP,
    VERDICT,
    AutomatonViolation,
    verify,
)
from .ritual import WORK_BEGUN, WORK_DONE, HouseRitual

# ── Явление, невыразимое моделью M0: ребёнок вырос и повышен ─────────────────
PROMOTED = "pid1_child_promoted"
GROWTH = "рост"

# ── Лестница вердиктов: события протокола проверки ───────────────────────────
HYPOTHESIS = "гипотеза_сформулирована"
LIMIT_OK = "предел_подтверждён"
THEORY_OK = "теория_приняла"
MONOTONICITY_OK = "монотонность_доказана"
NOVELTY_OK = "новизна_доказана"
REPRO_OK = "воспроизведение_совпало"
CONTRADICTION = "противоречие_найдено"
EXHAUSTED = "ресурсы_исчерпаны"
SELF_APPROVED = "самовольный_вердикт"

LADDER_ALPHABET: tuple[str, ...] = (
    HYPOTHESIS,
    LIMIT_OK,
    THEORY_OK,
    MONOTONICITY_OK,
    NOVELTY_OK,
    REPRO_OK,
    CONTRADICTION,
    EXHAUSTED,
    SELF_APPROVED,
)

UNKNOWN = "неизвестно"
TESTABLE = "проверяемо"
PARTIAL = "частично_проверено"
REPRODUCED = "воспроизведено"
FALSIFIED = "опровергнуто"
INCONCLUSIVE = "неясно"
BLOCKED = "заблокировано"

LADDER_ACCEPTING = frozenset({REPRODUCED, FALSIFIED})  # опровержение — тоже результат

VERDICT_TABLE: dict[str, dict[str, str]] = {
    UNKNOWN: {
        HYPOTHESIS: TESTABLE,
        LIMIT_OK: UNKNOWN,
        THEORY_OK: UNKNOWN,
        MONOTONICITY_OK: UNKNOWN,
        NOVELTY_OK: UNKNOWN,
        REPRO_OK: UNKNOWN,
        CONTRADICTION: FALSIFIED,
        EXHAUSTED: INCONCLUSIVE,
        SELF_APPROVED: BLOCKED,
    },
    TESTABLE: {
        HYPOTHESIS: TESTABLE,
        LIMIT_OK: TESTABLE,
        THEORY_OK: TESTABLE,
        MONOTONICITY_OK: TESTABLE,
        NOVELTY_OK: PARTIAL,
        REPRO_OK: TESTABLE,
        CONTRADICTION: FALSIFIED,
        EXHAUSTED: INCONCLUSIVE,
        SELF_APPROVED: BLOCKED,
    },
    PARTIAL: {
        HYPOTHESIS: PARTIAL,
        LIMIT_OK: PARTIAL,
        THEORY_OK: PARTIAL,
        MONOTONICITY_OK: PARTIAL,
        NOVELTY_OK: PARTIAL,
        REPRO_OK: REPRODUCED,
        CONTRADICTION: FALSIFIED,
        EXHAUSTED: INCONCLUSIVE,
        SELF_APPROVED: BLOCKED,
    },
    REPRODUCED: {  # вердикт получен — новый цикл открывает только новая гипотеза
        HYPOTHESIS: UNKNOWN,
        LIMIT_OK: INCONCLUSIVE,
        THEORY_OK: INCONCLUSIVE,
        MONOTONICITY_OK: INCONCLUSIVE,
        NOVELTY_OK: INCONCLUSIVE,
        REPRO_OK: INCONCLUSIVE,
        CONTRADICTION: INCONCLUSIVE,
        EXHAUSTED: INCONCLUSIVE,
        SELF_APPROVED: BLOCKED,
    },
    FALSIFIED: {  # честный нулевой результат; реабилитация — только новая гипотеза
        HYPOTHESIS: UNKNOWN,
        LIMIT_OK: INCONCLUSIVE,
        THEORY_OK: INCONCLUSIVE,
        MONOTONICITY_OK: INCONCLUSIVE,
        NOVELTY_OK: INCONCLUSIVE,
        REPRO_OK: INCONCLUSIVE,
        CONTRADICTION: INCONCLUSIVE,
        EXHAUSTED: INCONCLUSIVE,
        SELF_APPROVED: BLOCKED,
    },
    INCONCLUSIVE: {symbol: INCONCLUSIVE for symbol in LADDER_ALPHABET},
    BLOCKED: {symbol: BLOCKED for symbol in LADDER_ALPHABET},
}

# Канонические вердикты PossibilityRecord (схема Хозяина, английские ключи).
VERDICT_OF: dict[str, str] = {
    UNKNOWN: "UNKNOWN",
    TESTABLE: "TESTABLE",
    PARTIAL: "PARTIALLY_VERIFIED",
    REPRODUCED: "REPRODUCED",
    FALSIFIED: "FALSIFIED",
    INCONCLUSIVE: "INCONCLUSIVE",
    BLOCKED: "BLOCKED",
}

VARIATION = "VARIATION"
INNOVATION = "INNOVATION"
TRANSFORMATION = "TRANSFORMATION"

PHI1 = "Φ1"
PHI2 = "Φ2"  # новый закон метамодели: монотонность L(M0) ⊆ L(M1) обязательна

# Гёделевы пределы ОПЕ: что эта система НЕ доказывает о себе.
LIMITS_OPE: tuple[str, ...] = (
    "Шаблоны мутаций конечны (реестр генератора) — генератор не выдумывает молча",
    "Воспроизведение внутри одного кода — не внешняя проверка: финальный вердикт вне системы (Гёдель II)",
    "Ω измерима лишь до выбранного n — отсутствие роста при n не доказывает отсутствие роста",
    "H ≡ ⟨S,E,Uq,Uv⟩ — философская гипотеза Хозяина и проектный принцип, не доказанный закон",
)


class OPEViolation(RuntimeError):
    """Теория ОПЕ нарушена: чужой символ лестницы, нет шаблона мутации, подмена полномочий."""


def includes(
    big_table: dict[str, dict[str, str]],
    big_initial: str,
    big_accepting: Iterable[str],
    small_table: dict[str, dict[str, str]],
    small_initial: str,
    small_accepting: Iterable[str],
    alphabet: Iterable[str],
) -> bool:
    """Языковое включение L(small) ⊆ L(big): обход произведения автоматов.

    Включение нарушено, если достижима пара, где маленькая машина допускает
    слово, а большая — нет (старые возможности потеряны). Недостающие символы
    доопределяются до «тупика» — полнота δ обеспечивается, а не предполагается.
    """
    symbols = tuple(alphabet)

    def completed(table: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
        rows = {state: dict(row) for state, row in table.items()}
        for row in rows.values():
            for symbol in symbols:
                row.setdefault(symbol, SINK)
        rows.setdefault(SINK, {symbol: SINK for symbol in symbols})
        return rows

    left, right = completed(big_table), completed(small_table)
    acc_big, acc_small = frozenset(big_accepting), frozenset(small_accepting)
    seen = {(big_initial, small_initial)}
    stack = [(big_initial, small_initial)]
    while stack:
        state_big, state_small = stack.pop()
        if state_small in acc_small and state_big not in acc_big:
            return False  # старое слово новым языком потеряно
        for symbol in symbols:
            pair = (left[state_big][symbol], right[state_small][symbol])
            if pair not in seen:
                seen.add(pair)
                stack.append(pair)
    return True


@dataclass
class MetaModel:
    """Модель ОПЕ: DFA + версия машины и версия метамодели Φ."""

    version: str
    table: dict[str, dict[str, str]]
    alphabet: tuple[str, ...]
    initial: str
    accepting: frozenset[str]
    theory_version: str = PHI1

    @classmethod
    def pid1(cls) -> MetaModel:
        """M0: жизнь экипажа ПИД1 как язык — исходная модель дома."""
        return cls(
            version="M0-ПИД1",
            table={state: dict(row) for state, row in TABLE.items()},
            alphabet=ALPHABET,
            initial=INITIAL,
            accepting=frozenset(ACCEPTING),
        )

    def clone(self) -> MetaModel:
        return MetaModel(
            version=self.version,
            table={state: dict(row) for state, row in self.table.items()},
            alphabet=self.alphabet,
            initial=self.initial,
            accepting=frozenset(self.accepting),
            theory_version=self.theory_version,
        )

    def accepts(self, word: tuple[str, ...]) -> bool:
        state = self.initial
        for symbol in word:
            if symbol not in self.alphabet:
                return False
            state = self.table[state][symbol]
        return state in self.accepting

    def expressible(self, word: tuple[str, ...]) -> bool:
        return all(symbol in self.alphabet for symbol in word)

    def omega(self, n: int) -> int:
        """|Ω(n)|: сколько слов до длины n модель принимает — перебором."""
        count = 0
        for length in range(1, n + 1):
            for word in product(self.alphabet, repeat=length):
                state = self.initial
                for symbol in word:
                    state = self.table[state][symbol]
                if state in self.accepting:
                    count += 1
        return count

    def emergent_words(self, new_symbols: Iterable[str], n: int) -> int:
        """Принятые слова до длины n, содержащие новый символ, — цена эмерджентности."""
        fresh = set(new_symbols)
        count = 0
        for length in range(1, n + 1):
            for word in product(self.alphabet, repeat=length):
                if not (fresh & set(word)):
                    continue
                state = self.initial
                for symbol in word:
                    state = self.table[state][symbol]
                if state in self.accepting:
                    count += 1
        return count


@dataclass
class PossibilityRecord:
    """Запись возможности — схема Хозяина ``OPE/PossibilityRecord/1.0``.

    ``identity`` всегда None: Хозяин не моделируется — запрет №1 исполнен
    структурно, а не обещанием.
    """

    schema: str = "OPE/PossibilityRecord/1.0"
    identity: None = None
    observation: tuple[str, ...] = ()
    current_model_limit: str = ""
    novelty_level: str = UNKNOWN
    proposed_symbols: tuple[str, ...] = ()
    proposed_states: tuple[str, ...] = ()
    proposed_rows: dict[str, dict[str, str]] = field(default_factory=dict)
    proposed_law: str = ""
    predictions: tuple[str, ...] = ()
    test_protocol: tuple[str, ...] = ()
    falsification_conditions: tuple[str, ...] = ()
    provenance: list[str] = field(default_factory=list)
    independent_reproduction: list[str] = field(default_factory=list)
    verdict: str = "UNKNOWN"
    limitations: tuple[str, ...] = ()
    parent_versions: tuple[str, ...] = ()
    created_capabilities: tuple[str, ...] = ()
    house_word: tuple[str, ...] = ()
    house_cleaned: bool = False


class VerdictLadderMachine:
    """Живая лестница: шаг δ; чужой символ — нарушение, а не «странность в логах»."""

    def __init__(self) -> None:
        self._proofs = verify(
            VERDICT_TABLE, LADDER_ALPHABET, UNKNOWN, LADDER_ACCEPTING
        )
        self.state: str = UNKNOWN
        self.word: list[str] = []

    def step(self, symbol: str) -> str:
        if symbol not in LADDER_ALPHABET:
            raise OPEViolation(f"Чужой символ лестницы «{symbol}»")
        self.state = VERDICT_TABLE[self.state][symbol]
        self.word.append(symbol)
        return self.state

    @property
    def verdict(self) -> str:
        return VERDICT_OF[self.state]

    @property
    def decided(self) -> bool:
        return self.state in LADDER_ACCEPTING


class PossibilityGenerator:
    """Генератор гипотез: только реестр шаблонов — выдумывать молча запрещено."""

    def __init__(self) -> None:
        self._templates: dict[frozenset[str], Callable[[MetaModel], dict]] = {}
        self._templates[frozenset({PROMOTED})] = self._growth_template

    def hypothesize(self, model: MetaModel, word: tuple[str, ...]) -> PossibilityRecord:
        """Предел модели → запись возможности; предел не найден — честный VARIATION."""
        record = PossibilityRecord(observation=tuple(word))
        if model.accepts(word):
            record.current_model_limit = (
                "предела нет: слово выражено и принято — нового не требуется"
            )
            record.novelty_level = VARIATION
            record.verdict = "UNKNOWN"
            record.provenance.append("детектор: слово внутри Ω(M0) — гипотеза новизны без основания")
            record.falsification_conditions = (
                "старая модель принимает слово — гипотеза опровергнута",
            )
            return record
        missing = frozenset(symbol for symbol in word if symbol not in model.alphabet)
        template = self._templates.get(missing)
        if template is None:
            raise OPEViolation(
                "Шаблон мутации не зарегистрирован — генератор не выдумывает молча"
            )
        record.current_model_limit = (
            f"невыразимость: символ(ы) {', '.join(sorted(missing))} вне Σ — "
            f"явление «{word}» модель не может описать"
        )
        record.novelty_level = TRANSFORMATION
        proposal = template(model)
        record.proposed_symbols = proposal["symbols"]
        record.proposed_states = proposal["states"]
        record.proposed_rows = proposal["rows"]
        record.proposed_law = (
            "Φ2: монотонность L(M0) ⊆ L(M1) — обязательный экзамен будущих мутаций"
        )
        record.predictions = (
            "слово с новым символом принимается новой моделью",
            "все старые слова принимаются по-прежнему",
        )
        record.test_protocol = (
            "verify: экзамен структуры таблицы",
            "монотонность: обход произведения L(M0) ⊆ L(M1)",
            "строгая новизна: L(M0) ≠ L(M1)",
            "независимое воспроизведение протокола дважды",
        )
        record.falsification_conditions = (
            "старая модель принимает слово (предела нет)",
            "новая таблица больна (verify)",
            "новая модель теряет старые слова (монотонность)",
            "воспроизведения разошлись",
        )
        record.provenance.append(
            f"генератор: шаблон «рост» — +символ {PROMOTED}, +состояние «{GROWTH}»"
        )
        record.parent_versions = (model.version,)
        return record

    def _growth_template(self, model: MetaModel) -> dict:
        """Мутация «рост»: ребёнок вырос и повышен; старая жизнь не тронута."""
        rows = {state: dict(row) for state, row in model.table.items()}
        for state, row in rows.items():
            row[PROMOTED] = GROWTH if state in ("работа", "лечение") else SINK
        rows[GROWTH] = {
            STARTED: SINK,
            ROUND: "работа",
            UP: GROWTH,
            DOWN: "лечение",
            QUARANTINED: "карантин",
            PROMOTED: GROWTH,
            VERDICT: "доверие",
            DEGRADED: "опыт",
        }
        return {
            "symbols": (PROMOTED,),
            "states": (GROWTH,),
            "rows": rows,
        }


class IndependentVerifier:
    """Верификатор: единственный, кто двигает лестницу; хранит свою копию M0.

    Полномочия разделены структурно: у генератора нет метода вердикта,
    у верификатора — метода выдумки (capability-based security).
    """

    def __init__(self, original: MetaModel) -> None:
        self._original = original.clone()

    @property
    def original(self) -> MetaModel:
        return self._original.clone()

    def _protocol(
        self, record: PossibilityRecord, current: MetaModel, mutant: MetaModel | None,
        theory_version: str,
    ) -> dict:
        """Один проход протокола проверки — чистая функция гипотезы."""
        word = record.observation
        limit_confirmed = (
            not self._original.accepts(word) or not self._original.expressible(word)
        )
        theory_ok = mutant is not None
        if theory_ok:
            try:
                verify(mutant.table, mutant.alphabet, mutant.initial, mutant.accepting)
            except AutomatonViolation:
                theory_ok = False
        monotone = mutant is not None and includes(
            mutant.table, mutant.initial, mutant.accepting,
            self._original.table, self._original.initial, self._original.accepting,
            mutant.alphabet,
        )
        novelty = mutant is not None and mutant.accepts(word)
        return {
            "limit_confirmed": limit_confirmed,
            "theory_ok": theory_ok,
            "monotone": monotone,
            "novelty": novelty,
        }

    def adjudicate(
        self,
        record: PossibilityRecord,
        current: MetaModel,
        mutant: MetaModel | None,
        theory_version: str = PHI1,
    ) -> tuple[str, tuple[str, ...]]:
        """Протокол на опровержение: два прохода, лестница, вердикт.

        Самовольный вердикт (заполненный генератором) — BLOCKED, не принятый.
        Под Φ2 монотонность обязательна: новый закон имеет зубы.
        """
        ladder = VerdictLadderMachine()
        proofs: list[str] = list(ladder._proofs)
        if record.verdict != "UNKNOWN":
            ladder.step(SELF_APPROVED)
            proofs.append("Полномочия: генератор попытался объявить вердикт сам — BLOCKED")
            return ladder.verdict, tuple(proofs)
        ladder.step(HYPOTHESIS)
        first = self._protocol(record, current, mutant, theory_version)
        second = self._protocol(record, current, mutant, theory_version)
        if first != second:
            ladder.step(CONTRADICTION)
            proofs.append("Воспроизведение: протоколы разошлись — вердикту веры нет")
            return ladder.verdict, tuple(proofs)
        record.independent_reproduction.extend(
            [f"проход 1: {first}", f"проход 2: {second} (совпал)"]
        )
        if not first["limit_confirmed"]:
            ladder.step(CONTRADICTION)
            proofs.append("Опровержение: старая модель справляется — предела нет")
            return ladder.verdict, tuple(proofs)
        ladder.step(LIMIT_OK)
        if not first["theory_ok"]:
            ladder.step(CONTRADICTION)
            proofs.append("Опровержение: мутация не прошла экзамен структуры")
            return ladder.verdict, tuple(proofs)
        ladder.step(THEORY_OK)
        mandatory = theory_version == PHI2 or bool(record.proposed_law)
        if mandatory and not first["monotone"]:
            ladder.step(CONTRADICTION)
            proofs.append("Опровержение: мутация теряет старые слова — закон Φ2 против")
            return ladder.verdict, tuple(proofs)
        ladder.step(MONOTONICITY_OK)
        if not first["novelty"]:
            ladder.step(CONTRADICTION)
            proofs.append("Опровержение: новой возможности нет — расширение пусто")
            return ladder.verdict, tuple(proofs)
        ladder.step(NOVELTY_OK)  # → частично_проверено
        ladder.step(REPRO_OK)  # → воспроизведено (проходы совпали)
        proofs.append(
            "Теорема о монотонности: L(M0) ⊆ L(M1) — обход произведения, старые слова живы"
        )
        proofs.append("Строгая новизна: L(M0) ≠ L(M1) — слово с новым символом принято")
        proofs.append("Воспроизведение: протокол совпал дважды — REPRODUCED")
        return ladder.verdict, tuple(proofs)


class OPE:
    """Среда открытого порождения возможностей: Ω_t → Discover(ΔΦ) → Ω_{t+1}."""

    motto = "Порождать возможности, а не исполнять команды."

    def __init__(
        self,
        model: MetaModel | None = None,
        on_event: Callable[[dict], None] | None = None,
    ) -> None:
        self._original = (model or MetaModel.pid1()).clone()
        self.model = self._original.clone()
        self.theory_version: str = self._original.theory_version
        self.generator = PossibilityGenerator()
        self.verifier = IndependentVerifier(self._original)
        self.history: list[PossibilityRecord] = []
        self._on_event = on_event

    def _emit(self, event: dict) -> None:
        if self._on_event is not None:
            self._on_event(event)

    @property
    def version(self) -> str:
        return self.model.version

    def discover(self, phenomenon: Iterable[str] | str) -> PossibilityRecord:
        """Полный цикл: детектор → генератор → верификатор → (усыновление, Φ2)."""
        word = (phenomenon,) if isinstance(phenomenon, str) else tuple(phenomenon)
        ritual = HouseRitual(on_step=self._emit)
        ritual.step(WORK_BEGUN)  # поработал
        record = self.generator.hypothesize(self.model, word)
        mutant: MetaModel | None = None
        if record.proposed_rows:
            mutant = MetaModel(
                version=f"{self.model.version}+{'+'.join(record.proposed_symbols)}",
                table=record.proposed_rows,
                alphabet=self.model.alphabet + record.proposed_symbols,
                initial=self.model.initial,
                accepting=frozenset(self.model.accepting),
                theory_version=self.theory_version,
            )
        verdict, proofs = self.verifier.adjudicate(
            record, self.model, mutant, self.theory_version
        )
        record.verdict = verdict
        record.limitations = LIMITS_OPE
        record.provenance.append("верификатор: независимая копия M0, полномочия разделены")
        if verdict == "REPRODUCED" and mutant is not None:
            self._adopt(record, mutant, proofs)
        self.history.append(record)
        ritual.step(WORK_DONE)  # сделал (вердикт получен)
        ritual.close()  # убрал за собой
        record.house_word = tuple(ritual.word)
        record.house_cleaned = ritual.cleaned
        self._emit({"type": "ope_verdict", "verdict": verdict, "omega": self.model.omega(3)})
        return record

    def _adopt(self, record: PossibilityRecord, mutant: MetaModel, proofs: tuple) -> None:
        """Усыновление мутации: новая возможность входит в дом, Φ получает зубы."""
        record.created_capabilities = record.proposed_symbols
        self.model = mutant
        if record.proposed_law:
            self.theory_version = PHI2
            self.model.theory_version = PHI2
        record.provenance.append(f"усыновлено: дом живёт в {self.model.version}, {self.theory_version}")

    def rollback(self) -> str:
        """Откат к исходной модели: история не уничтожается, записи живы."""
        self.model = self._original.clone()
        self.theory_version = self._original.theory_version
        return self.model.version

    def fork(self) -> OPE:
        """Множественность реализаций: песочница с копией истории и запретов."""
        sandbox = OPE(model=self.model.clone())
        sandbox.theory_version = self.theory_version
        sandbox._original = self._original.clone()
        sandbox.verifier = IndependentVerifier(self._original)
        sandbox.history = list(self.history)
        return sandbox

    def report(self) -> list[str]:
        """Итог среды: версии, Ω, вердикты, пределы — дом отчитывается сам."""
        lines = [
            (
                f"ОПЕ: модель {self.version}, метамодель {self.theory_version}, "
                f"записей в истории: {len(self.history)}"
            ),
            f"Ω(3) текущей модели: {self.model.omega(3)} слов приняты",
        ]
        for record in self.history:
            lines.append(
                f"  [{record.novelty_level}] «{' '.join(record.observation)}» → "
                f"{record.verdict} ({record.current_model_limit})"
            )
        lines.append(f"Пределы ОПЕ: {len(LIMITS_OPE)} объявлено (Гёдель II)")
        return lines


def ope_agent() -> Agent:
    """Генезис: навык ``ope`` — теория исполняется, а не рассказывается.

    Агент сам: находит предел модели, предлагает мутацию метамодели, доказывает
    монотонность и строгую новизну, дважды воспроизводит протокол, показывает
    зубы нового закона Φ2 и закрывает дом по закону.
    """

    async def act(task: str) -> list[str]:
        if not task.strip():
            raise OPEViolation("Пустой мандат: ОПЕ не порождает из пустоты")
        ope = OPE()
        omega_before = ope.model.omega(4)
        variation = ope.discover((STARTED, ROUND, UP, VERDICT))
        transformation = ope.discover((STARTED, ROUND, UP, PROMOTED, VERDICT))
        omega_after = ope.model.omega(4)
        emergent = ope.model.emergent_words((PROMOTED,), 4)
        teeth: str = "зубы Φ2 не проверялись"
        if ope.theory_version == PHI2:
            template = ope.generator.hypothesize(
                ope._original, (STARTED, ROUND, UP, PROMOTED, VERDICT)
            )
            bad_rows = template.proposed_rows
            bad_rows["работа"]["pid1_child_up"] = SINK  # теряет старые слова
            bad = MetaModel(
                version="M-bad",
                table=bad_rows,
                alphabet=ope._original.alphabet + (PROMOTED,),
                initial=ope._original.initial,
                accepting=frozenset(ope._original.accepting),
            )
            probe = PossibilityRecord(
                observation=(STARTED, PROMOTED, VERDICT),
                novelty_level=INNOVATION,
                proposed_rows=bad_rows,
            )
            verdict_bad, _ = ope.verifier.adjudicate(
                probe, ope.model, bad, ope.theory_version
            )
            teeth = f"немонотонная мутация → {verdict_bad} (закон Φ2 работает)"
        sandbox = ope.fork()
        rolled = sandbox.rollback()
        return [
            f"ОПЕ: Ω(4) модели {ope._original.version} = {omega_before} слов",
            (
                f"Вариация: слово {(STARTED, ROUND, UP, VERDICT)} внутри Ω — гипотеза "
                f"новизны {variation.verdict} (честный нулевой результат)"
            ),
            (
                f"Невыразимость: «ребёнок вырос» — символ вне Σ → мутация метамодели: "
                f"+{PROMOTED}, +состояние «{GROWTH}»"
            ),
            (
                f"Экзамены: verify + монотонность L(M0) ⊆ L(M1) + строгая новизна "
                f"L(M0) ≠ L(M1) → вердикт {transformation.verdict}"
            ),
            (
                f"Эмерджентность измерена: Ω(4) {omega_before} → {omega_after} "
                f"(+{omega_after - omega_before} слов, из них {emergent} с «ростом»)"
            ),
            f"Дом живёт в {ope.version}, метамодель {ope.theory_version}; {teeth}",
            (
                f"Откат: песочница вернулась к {rolled} — история не уничтожается "
                f"({len(ope.history)} записей, identity = None — запрет №1)"
            ),
            f"Пределы ОПЕ: {', '.join(LIMITS_OPE[:2])}…",
            (
                f"Закон дома: {'дом чист' if transformation.house_cleaned else 'грязь'} — "
                f"{' → '.join(transformation.house_word)}"
            ),
            f"Мандат «{task}»: среда порождает возможности, а не исполняет команды",
        ]

    return Agent(name="Генезис", skill="ope", act=act)
