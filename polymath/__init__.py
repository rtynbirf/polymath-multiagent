"""Polymath Multiagent — «Одно другое не исключает».

Параллельная оркестрация ИИ-агентов с контрактом уникальных навыков:
навыки агентов дополняют друг друга и никогда не дублируются.
"""

from .agent import Agent, AgentReport
from .automaton import AutomatonPid1, AutomatonViolation, DriveReport, automaton_agent
from .ope import OPE, MetaModel, OPEViolation, PossibilityRecord, ope_agent
from .orchestrator import DuplicateSkillError, PolymathOrchestrator, Synthesis
from .pid1 import ChildSpec, PolymathPid1, QuarantinedError
from .ritual import HouseRitual, RitualViolation, house_law_agent
from .supervisor import LIMITS, AuditViolation, audit, supervisor_agent

__version__ = "0.5.1"

__all__ = [
    "LIMITS",
    "OPE",
    "Agent",
    "AgentReport",
    "AuditViolation",
    "AutomatonPid1",
    "AutomatonViolation",
    "ChildSpec",
    "DriveReport",
    "DuplicateSkillError",
    "HouseRitual",
    "MetaModel",
    "OPEViolation",
    "PolymathOrchestrator",
    "PolymathPid1",
    "PossibilityRecord",
    "QuarantinedError",
    "RitualViolation",
    "Synthesis",
    "__version__",
    "audit",
    "automaton_agent",
    "house_law_agent",
    "ope_agent",
    "supervisor_agent",
]
