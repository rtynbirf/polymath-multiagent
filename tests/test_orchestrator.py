"""Тесты Полимата: контракт навыков, параллельность, синтез."""

import asyncio
import time
import unittest

from polymath import Agent, DuplicateSkillError, PolymathOrchestrator


def make_agent(name: str, skill: str, delay: float = 0.05, findings=("находка",)) -> Agent:
    """Фабрика тестовых агентов с управляемой задержкой."""

    async def act(task: str) -> list[str]:
        await asyncio.sleep(delay)
        return [f"{finding} ({task})" for finding in findings]

    return Agent(name=name, skill=skill, act=act)


class TestSkillsContract(unittest.TestCase):
    """Контракт «одно другое не исключает»: навыки уникальны."""

    def test_duplicate_skill_rejected(self) -> None:
        with self.assertRaises(DuplicateSkillError):
            PolymathOrchestrator(
                [make_agent("Альфа", "research"), make_agent("Бета", "research")]
            )

    def test_unique_skills_accepted(self) -> None:
        orch = PolymathOrchestrator(
            [make_agent("Альфа", "research"), make_agent("Бета", "coding")]
        )
        self.assertEqual(len(orch.agents), 2)

    def test_error_message_lists_duplicates(self) -> None:
        with self.assertRaisesRegex(DuplicateSkillError, "research"):
            PolymathOrchestrator(
                [
                    make_agent("Альфа", "research"),
                    make_agent("Бета", "research"),
                    make_agent("Гамма", "coding"),
                ]
            )


class TestParallelism(unittest.IsolatedAsyncioTestCase):
    """Параллельность по умолчанию: время ≈ самый медленный агент."""

    async def test_agents_run_in_parallel(self) -> None:
        orch = PolymathOrchestrator(
            [
                make_agent("Альфа", "research", delay=0.4),
                make_agent("Бета", "coding", delay=0.4),
                make_agent("Гамма", "critique", delay=0.4),
            ]
        )
        started = time.perf_counter()
        synthesis = await orch.solve("параллельный тест")
        elapsed = time.perf_counter() - started
        # Последовательно было бы ~1.2s; параллельно должно быть ~0.4s.
        self.assertLess(elapsed, 1.0)
        self.assertEqual(synthesis.agents_count, 3)

    async def test_reports_cover_all_agents(self) -> None:
        orch = PolymathOrchestrator(
            [make_agent("Альфа", "research"), make_agent("Бета", "coding")]
        )
        synthesis = await orch.solve("тест отчётов")
        self.assertEqual({r.agent for r in synthesis.reports}, {"Альфа", "Бета"})
        self.assertEqual({r.skill for r in synthesis.reports}, {"research", "coding"})


class TestSynthesis(unittest.IsolatedAsyncioTestCase):
    """Синтез: дедупликация находок с сохранением порядка."""

    async def test_findings_deduplicated_in_order(self) -> None:
        orch = PolymathOrchestrator(
            [
                make_agent("Альфа", "research", findings=("x", "y")),
                make_agent("Бета", "coding", findings=("y", "z")),
                make_agent("Гамма", "critique", findings=("z", "w")),
            ]
        )
        synthesis = await orch.solve("синтез")
        expected = ("x (синтез)", "y (синтез)", "z (синтез)", "w (синтез)")
        self.assertEqual(synthesis.findings, expected)

    async def test_summary_contains_key_facts(self) -> None:
        orch = PolymathOrchestrator([make_agent("Альфа", "research", delay=0.05)])
        synthesis = await orch.solve("сводка")
        text = synthesis.summary()
        self.assertIn("Задача: сводка", text)
        self.assertIn("Агентов: 1", text)
        self.assertIn("Уникальных навыков: 1", text)


if __name__ == "__main__":
    unittest.main()
