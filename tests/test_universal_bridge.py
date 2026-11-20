# -*- coding: utf-8 -*-
"""Тесты моста рой ↔ ЦУА: мозг — обычный агент роя, без дубля навыка."""

from __future__ import annotations

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from polymath.agent import Agent
from polymath.orchestrator import DuplicateSkillError, PolymathOrchestrator
from polymath.universal_bridge import UNIVERSAL_SKILL, brain_agent


def _echo(name: str) -> Agent:
    async def act(task: str):
        return (f"{name} видит: {task[:20]}",)
    return Agent(name=name, skill=f"skill-{name}", act=act)


class TestBridge(unittest.TestCase):
    def test_skill_is_unique_and_reserved(self):
        agent = brain_agent()
        self.assertEqual(agent.skill, UNIVERSAL_SKILL)
        self.assertEqual(agent.name, "ЦУА-мозг")

    def test_duplicate_skill_rejected(self):
        with self.assertRaises(DuplicateSkillError):
            PolymathOrchestrator([brain_agent(), brain_agent(name="второй ЦУА")])

    def test_orchestrator_mixes_brain_and_scouts(self):
        """Мозг и скауты в одном рое: параллельность сохраняется.
        Мозг получает mock-LLM (без сети) и решает демо-задачу целиком."""
        import tempfile
        from pathlib import Path
        from universal.brain import AgentConfig
        from universal.mock_llm import DEMO_SCRIPT, make_server

        srv = make_server(list(DEMO_SCRIPT))
        try:
            tmp = Path(tempfile.mkdtemp(prefix="bridge-test-"))
            cfg = AgentConfig(
                llm_base_url=f"http://127.0.0.1:{srv.server_address[1]}/v1",
                llm_model="mock",
                workspace_root=str(tmp / "workspace"),
                memory_db=str(tmp / "memory" / "agent.db"),
                knowledge_dir=str(tmp / "knowledge"),
                results_log=str(tmp / "results.log"),
                queue_path=str(tmp / "task_queue.txt"),
                daemon_poll_sec=1,
            )
            orchestrator = PolymathOrchestrator(
                [brain_agent(cfg=cfg), _echo("Скаут"), _echo("Карта")])
            self.assertEqual(len(orchestrator.agents), 3)
            synthesis = self._run(orchestrator.solve("инвентаризация дома"))
            self.assertEqual(len(synthesis.findings), 3)
            brain_line = next(f for f in synthesis.findings if "[T-" in f)
            self.assertIn("done", brain_line)
            self.assertTrue(any("Скаут видит" in f for f in synthesis.findings))
        finally:
            srv.shutdown()
            srv.server_close()

    @staticmethod
    def _run(coro):
        import asyncio
        return asyncio.run(coro)


if __name__ == "__main__":
    unittest.main()
