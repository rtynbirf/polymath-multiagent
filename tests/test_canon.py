"""Канон косЯков держится не на честном слове.

Философия: ошибка, не ставшая уроком, обязана повториться. Журнал
``MISTAKES.md`` обязателен к чтению до работы и к пополнению после;
``AGENTS.md`` — канон для всех агентов. Словам агентов верить нельзя —
машина отвечает только на перебор, поэтому формат журнала, порядок
чтения и запрет молчания проверяются кодом. Выбросить запись, промолчать
или замести формат нельзя навсегда.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_MD = ROOT / "AGENTS.md"
MISTAKES_MD = ROOT / "MISTAKES.md"

SECTION_RE = re.compile(r"^## \[M-(\d+)\] .+$", re.MULTILINE)
REQUIRED_FIELDS = ("Симптом", "Причина", "Исправление", "Урок")


def journal_sections() -> list[tuple[int, str]]:
    """Разбор журнала на записи: номер и тело каждой."""
    text = MISTAKES_MD.read_text(encoding="utf-8")
    matches = list(SECTION_RE.finditer(text))
    out: list[tuple[int, str]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append((int(m.group(1)), text[m.end():end]))
    return out


def test_canon_files_exist_and_nonempty() -> None:
    """Канон и журнал существуют и не пусты — молчание невозможно."""
    for path in (AGENTS_MD, MISTAKES_MD):
        assert path.is_file(), f"{path.name}: файла нет — канон снесён"
        assert path.read_text(encoding="utf-8").strip(), f"{path.name}: пуст"


def test_agents_md_orders_mistakes_first() -> None:
    """Первое дело агента — знакомство с косЯками, до любой правки."""
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "MISTAKES.md" in text, "канон не указывает на журнал"
    assert "ПЕРВЫМ ДЕЛОМ" in text, "чтение журнала не объявлено первым делом"
    assert "до любой правки кода" in text, "нет запрета править до чтения"


def test_agents_md_demands_recording() -> None:
    """После работы агент обязан дописать свои косЯки в журнал."""
    text = AGENTS_MD.read_text(encoding="utf-8")
    assert "дописываются в" in text, "нет обязанности пополнить журнал"
    assert "Урок" in text, "формат записи без урока не назван"


def test_journal_orders_reading_before_work() -> None:
    """Сам журнал тоже несёт правило чтения — защита от вырождения."""
    text = MISTAKES_MD.read_text(encoding="utf-8")
    assert "первым делом" in text.lower(), "в журнале нет правила чтения"


def test_journal_entries_have_fixed_format() -> None:
    """Каждая запись: Симптом / Причина / Исправление / Урок."""
    sections = journal_sections()
    assert sections, "журнал пуст — косЯки замолчали"
    for number, body in sections:
        for field in REQUIRED_FIELDS:
            assert f"{field}:" in body, f"[M-{number:02d}]: нет поля «{field}»"


def test_journal_numbers_are_sequential() -> None:
    """Номера записей растут без пропусков и дублей — журнал только растёт."""
    numbers = [n for n, _ in journal_sections()]
    assert numbers, "журнал пуст"
    assert numbers == sorted(numbers), "номера не по порядку"
    assert len(numbers) == len(set(numbers)), "дубли номеров"
    assert numbers == list(range(numbers[0], numbers[0] + len(numbers))), (
        "пропуск в нумерации — кто-то вычеркнул запись"
    )


def test_journal_is_not_a_stub() -> None:
    """Журнал с реальными уроками, а не заглушка: записи > 9."""
    assert len(journal_sections()) > 9, "журнал поредел"


def test_canon_files_have_no_placeholders() -> None:
    """В каноне и журнале нет ленивых остатков: TODO/XXX/заглушки."""
    for path in (AGENTS_MD, MISTAKES_MD):
        text = path.read_text(encoding="utf-8")
        for stub in ("TODO", "XXX", "【", "待补充"):
            assert stub not in text, f"{path.name}: остаток {stub!r}"
