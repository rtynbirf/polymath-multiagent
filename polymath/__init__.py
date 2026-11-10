"""Polymath Multiagent — «Одно другое не исключает».

Параллельная оркестрация ИИ-агентов с контрактом уникальных навыков:
навыки агентов дополняют друг друга и никогда не дублируются.
"""

from .agent import Agent, AgentReport
from .automaton import AutomatonPid1, AutomatonViolation, DriveReport, automaton_agent
from .orchestrator import DuplicateSkillError, PolymathOrchestrator, Synthesis
from .pid1 import ChildSpec, PolymathPid1, QuarantinedError
from .supervisor import LIMITS, AuditViolation, audit, supervisor_agent

__version__ = "0.3.0"

__all__ = [
    "LIMITS",
    "Agent",
    "AgentReport",
    "AuditViolation",
    "AutomatonPid1",
    "AutomatonViolation",
    "ChildSpec",
    "DriveReport",
    "DuplicateSkillError",
    "PolymathOrchestrator",
    "PolymathPid1",
    "QuarantinedError",
    "Synthesis",
    "__version__",
    "audit",
    "automaton_agent",
    "supervisor_agent",
]
