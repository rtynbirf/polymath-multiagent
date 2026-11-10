# 🧠 POLYMATH = MULTIAGENT

[![CI](https://github.com/rtynbirf/polymath-multiagent/actions/workflows/ci.yml/badge.svg)](https://github.com/rtynbirf/polymath-multiagent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-261230)](https://github.com/astral-sh/ruff)
![MCP](https://img.shields.io/badge/MCP-server--ready-2d00f7)
![Dashboard](https://img.shields.io/badge/dashboard-SSE--live-D9A441)
![Мотто](https://img.shields.io/badge/одно_другое_не_исключает-⚡-red)

> **Одно другое не исключает.**
> *Skills complement — never exclude.*

**polymath-multiagent** — микро-оркестратор параллельных ИИ-агентов, в котором философия
зашита прямо в код: агенты с разными навыками работают **одновременно**, дополняют
друг друга и физически не могут дублировать навыки друг друга. Пока другие фреймворки
строят иерархии и очереди — Полимат выпускает всех на поле сразу.

---

## ⚡ Почему такого нет ни у кого

1. **Контракт уникальных навыков.** Попытка собрать команду из двух агентов с одним
   и тем же навыком падает с `DuplicateSkillError` ещё до старта. Мотто проекта —
   не лозунг, а проверяемый инвариант (см. тесты).
2. **Параллельность по умолчанию.** Все агенты стартуют строго одновременно через
   `asyncio.gather`: общее время ≈ времени самого медленного агента, а не сумме
   времён. В демо: **0.70s вместо 1.90s** при 4 агентах.
3. **Синтез, а не свалка.** Находки агентов дедуплицируются с сохранением порядка
   первых вхождений — результат читается как единый документ, а не как лог чата.

## 🗺️ Архитектура

```mermaid
flowchart LR
    T(["Задача"]) --> O["PolymathOrchestrator"]
    O -->|"asyncio.gather"| A1["Скаут · research"]
    O --> A2["Зодчий · architecture"]
    O --> A3["Кузнец · coding"]
    O --> A4["Софист · critique"]
    A1 --> S["Synthesis<br/>дедупликация + порядок"]
    A2 --> S
    A3 --> S
    A4 --> S
```

## 🚀 Быстрый старт

```bash
git clone https://github.com/rtynbirf/polymath-multiagent.git
cd polymath-multiagent
python -m pip install -e ".[dev]"
polymath demo        # живая демонстрация параллельной оркестрации
```

Требуется Python **3.10+**. Ноль внешних зависимостей в рантайме — только стандартная библиотека.

## 🎬 Живое демо (`polymath demo`)

```text
Мотто: Одно другое не исключает.
------------------------------------------------------------
[Скаут] (research, 0.30s)
  + Разведка: собран контекст по «построить уникальный проект»
  + Разведка: мировые аналоги найдены и проанализированы
[Зодчий] (architecture, 0.50s)
  + Архитектура: схема из 3 модулей для «построить уникальный проект» готова
[Кузнец] (coding, 0.70s)
  + Код: каркас «построить уникальный проект» собран
  + Код: тесты написаны и зелёные
[Софист] (critique, 0.40s)
  + Критика: риски под контролем
  + Критика: «построить уникальный проект» жизнеспособен
------------------------------------------------------------
Задача: построить уникальный проект
Агентов: 4 | Уникальных навыков: 4
Время (параллельно): 0.70s вместо 1.90s (экономия 1.20s)
```

## 🔒 Контракт уникальных навыков

```python
from polymath import Agent, DuplicateSkillError, PolymathOrchestrator

try:
    PolymathOrchestrator([Agent("Альфа", "research", act=...),
                          Agent("Бета", "research", act=...)])
except DuplicateSkillError as e:
    print(e)  # Навыки должны дополнять друг друга... Повторяются: research
```

Свой агент — это три поля: имя, навык и асинхронная функция `act(task) -> list[str]`.
Никаких базовых классов, никаких конфигов на 200 строк.

## ✅ Тесты и CI

```bash
pytest -q      # 58 тестов: контракт навыков, параллельность, синтез, MCP, SSE,
               # надзор, ПИД1, теория конечных автоматов, CI-ритуал
ruff check .   # чистота кода
```

GitHub Actions гоняет матрицу Python 3.10 → 3.13 на каждый push.

## 🔌 MCP-сервер · v0.2

Полимат теперь — **инструмент для любых LLM-хостов**: Claude Desktop, IDE-агенты и любой
MCP-клиент оркестрируют экипаж, не устанавливая ничего сверх протокола.

```bash
pip install "polymath-multiagent[mcp]"
```

Конфигурация MCP-хоста:

```json
{
  "mcpServers": {
    "polymath": { "command": "polymath", "args": ["mcp"] }
  }
}
```

| Инструмент / ресурс | Что даёт |
|---|---|
| `polymath_info` | паспорт: версия, мотто, состав экипажа |
| `orchestrate(task)` | параллельный прогон 4 агентов + измеренный выигрыш времени |
| `polymath://motto` | мотто проекта одной строкой |
| `polymath://skills` | уникальные навыки экипажа |

Проверка без внешних хостов: `fastmcp.Client` подключается к серверу прямо в памяти —
этими тестами CI и живёт (`tests/test_mcp_server.py`).

## 📊 Живой дашборд оркестрации

```bash
polymath dashboard --port 8765   # открыть http://127.0.0.1:8765
```

Экипаж живёт в фоне бесконечными циклами оркестрации; события агент-за-агентом летят
в браузер по **Server-Sent Events**. Ноль зависимостей — чистый stdlib:
`http.server` + `asyncio` + одна шина событий.

- 🔴 карточка агента пульсирует, пока он работает, и зеленеет, когда закончил
- 🚨 в нечётных циклах экипаж ведёт ПИД1: упавший агент рестартует на глазах, а карантин горит **красным** — карточка, панель вердикта и журнал
- 🤖 каждый нечётный цикл закрывается вердиктом автомата: слово из N символов принято → «доверие»
- 💰 панель «СИНТЕЗ» считает экономию времени от параллельности в реальном времени
- 📜 журнал событий внизу — каждый цикл, каждый агент, каждый шаг δ

![Живой дашборд: 4 агента параллельно, синтез за 0.7s вместо 1.9s](docs/dashboard.png)

## 👀 Надзиратель · ритуал стал агентом

Философия проверяется не только тестами, но и живым агентом. Надзиратель (навык
`supervision`, уникален по контракту) после каждого прогона проверяет три гарантии
оркестратора: контракт навыков, параллельность и чистоту синтеза. Нарушение
любого инварианта поднимает `AuditViolation`.

Вердикт декларирует собственную неполноту (`polymath.LIMITS`): по второй теореме
Гёделя система не доказывает свою полноту изнутри — Надзиратель делит инструменты
с поднадзорным кодом, поэтому финальный надзор остаётся вне системы (Хозяин,
внешние тесты, независимая реализация).

```bash
polymath audit   # демо-прогон + вердикт Надзирателя
```

```python
from polymath import audit, supervisor_agent

verdicts = audit(synthesis)          # ["Контракт: 4 навыков уникальны", ...]
crew = demo_agents() + [supervisor_agent()]   # 5-й агент: навык supervision
```

## 🧬 ПИД1 · init(8) экипажа — LFS-дух, OTP-надзор

Выведено из практик гуру и доведено до своего: Erlang/OTP (`one_for_one` —
падение ребёнка не трогает остальных), systemd (`RestartSec` + экспоненциальный
backoff с потолком), Unix init (ПИД1 не умирает, зомби переполучаются), «let it
crash», Linux From Scratch (stdlib-only). Своё: **карантин** вместо смерти
надзора, **реестр попыток** (`attempts == completions + restarts` — зомби
невозможны), **вердикт с гёделевыми пределами** и эмпатия в тоне.

```bash
polymath pid1   # живая самозаживающая оркестрация: Кузнец бракует 2 удара — ПИД1 учит
```

```python
from polymath import ChildSpec, PolymathPid1

pid1 = PolymathPid1(crew_specs, on_event=print)   # события — в шину/браузер
synthesis = await pid1.run("мандат")               # ПИД1 сам не умирает
```

Эмерджентность: экипаж, который не может умереть и не может дублировать навыки.

## 🤖 Автомат · теория конечных автоматов — агент, который всё делает сам

Надзор стал автоматом — в математическом смысле: конечный детерминированный
автомат (Q, Σ, δ, q0, F), где жизнь экипажа ПИД1 — слово над алфавитом событий.
Слово, не принятое автоматом, — нарушение теории, а не «странность в логах».

```mermaid
stateDiagram-v2
    [*] --> ожидание
    ожидание --> работа: pid1_started
    работа --> работа: раунд / ребёнок-вверх
    работа --> лечение: ребёнок-вниз
    лечение --> карантин: бюджет падений исчерпан
    карантин --> работа: новый раунд (экипаж живёт без бракодела)
    работа --> доверие: pid1_verdict ✓ (допуск)
    работа --> опыт: pid1_degraded ✓ (допуск)
```

Автомат рождается проверенным и **обучен всему через экзамены**:

- `verify` — детерминизм, полнота δ, достижимость, допуск, единственность вердикта;
- `minimize` — минимизация Мура: 7 → 5 состояний, поведение доказано неизменным;
- `equivalent` — теорема о ядре: **ПИД1 ≡ OTP one_for_one** на общих символах
  (обход произведения автоматов), а три отступления от гуру — карантин,
  вердикт, деградация — доказаны антитеоремой на полном алфавите
  (построчно см. [docs/OTP.md](docs/OTP.md));
- `drive` — автономный цикл: экипаж, ПИД1, автомат, Надзиратель — **ноль
  Хозяина в контуре**; отклонённое слово не убивает машину — она просит
  новый мандат (эмпатия).

```bash
polymath automat   # живой прогон: δ-шаги, слово, реестр попыток, вердикт
```

```python
from polymath import AutomatonPid1, automaton_agent
from polymath.crews import pid1_demo_specs

pid1 = AutomatonPid1(pid1_demo_specs(), on_event=print)  # каждое событие — символ Σ
report = await pid1.drive("мандат")   # слово принято → «доверие», аудит Надзирателя
crew = demo_agents() + [supervisor_agent(), automaton_agent()]  # навык automata уникален
```

Эмерджентность: агент, который сам ведёт экипаж, сам доказывает корректность
своего поведения и сам называет, где сознательно отошёл от гуру.

## 🗺️ Дорожная карта

| Фаза | Что будет |
|------|-----------|
| v0.2 | ✅ **MCP-сервер** — Полимат как инструменты для любых LLM-хостов |
| v0.3 | ✅ **Живой дашборд** — SSE-оркестрация в браузере, stdlib-only |
| v0.4 | ✅ **Надзор стал жизнью** — ПИД1 (init × OTP × systemd) и Автомат на теории конечных автоматов: минимизация Мура, теорема о ядре с OTP, автономный `drive` без Хозяина |
| v0.5 | Распределённый режим: агенты в разных процессах/на разных машинах |
| v0.6 | Опциональные LLM-провайдеры внутри агентов |

## 🇬🇧 English in one paragraph

**polymath-multiagent** is a zero-dependency micro-orchestrator for parallel AI agents.
Its philosophy is enforced in code: agents with unique skills run **simultaneously**
(`asyncio.gather`), duplicate skills are rejected at construction time with
`DuplicateSkillError`, and findings are merged into a deduplicated, order-preserving
`Synthesis`. v0.4 adds a PID1 layer (`init(8)` × OTP `one_for_one` × systemd backoff)
formalized as a **finite-state automaton**: the crew's life is a word over the event
alphabet, runs must be accepted by the DFA (Moore minimization, Hopcroft–Ullman
product equivalence proves the OTP-core theorem), and `polymath automat` drives the
whole crew autonomously — no human in the loop. Install with `pip install -e ".[dev]"`,
run `polymath demo`, and watch four agents finish in the time of the slowest one.

## 📄 Лицензия

[MIT](LICENSE) — **rtynbirf · Полимат-Универсум** · 2026
