"""Polymath Multiagent — «Одно другое не исключает».

Параллельная оркестрация ИИ-агентов с контрактом уникальных навыков:
навыки агентов дополняют друг друга и никогда не дублируются.
"""

from .agent import Agent, AgentReport
from .orchestrator import DuplicateSkillError, PolymathOrchestrator, Synthesis

__version__ = "0.1.0"

__all__ = [
    "Agent",
    "AgentReport",
    "DuplicateSkillError",
    "PolymathOrchestrator",
    "Synthesis",
    "__version__",
]
