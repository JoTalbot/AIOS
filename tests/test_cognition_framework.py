"""Tests for Cognition, Autonomous Science, Engineering, and Role Frameworks."""

import pytest

from aios_core.ai_engineer import AIEngineer
from aios_core.ai_product_manager import AIProductManager
from aios_core.ai_researcher import AIResearcher
from aios_core.ai_scientist import AIScientist
from aios_core.ai_startup import AIStartup
from aios_core.creativity import CreativityEngine
from aios_core.emotional_intelligence import EmotionalIntelligence
from aios_core.metacognition import MetaCognition
from aios_core.social_intelligence import SocialIntelligence
from aios_core.theory_of_mind import TheoryOfMind


def test_theory_of_mind():
    tom = TheoryOfMind()
    tom.model_agent("agent_alpha", {"sky": "blue"}, ["complete_task"], ["send_message"])
    pred = tom.predict_action("agent_alpha", {"situation": "normal"})
    assert pred is not None


def test_emotional_intelligence():
    eq = EmotionalIntelligence()
    emotion = eq.recognize_emotion({"signal": "calm"})
    assert emotion == "neutral"

    eq.regulate_emotion("joy", 0.8)
    assert eq.emotions["joy"] == 0.8


def test_metacognition():
    meta = MetaCognition()
    meta.monitor_reasoning("solve_math", 0.95)
    assess = meta.self_assess(0.85)
    assert assess["awareness"] is True


def test_social_intelligence():
    si = SocialIntelligence()
    for _ in range(20):
        si.update_relationship("agent_1", "agent_2", {"outcome": "positive"})
    actions = si.social_reasoning({"context": "group_work"})
    assert "cooperate" in actions


def test_creativity_engine():
    creative = CreativityEngine()
    idea = creative.generate_idea("quantum_computing")
    assert idea["domain"] == "quantum_computing"
    assert "description" in idea


def test_ai_roles_suite():
    scientist = AIScientist()
    hypo = scientist.generate_hypothesis("neuroscience")
    assert hypo["domain"] == "neuroscience"

    researcher = AIResearcher()
    paper = researcher.write_paper("Quantum AI", [{"exp": 1}])
    assert paper["status"] == "draft"

    engineer = AIEngineer()
    system = engineer.design_system({"name": "AgentMesh"})
    assert system["name"] == "AgentMesh"

    pm = AIProductManager()
    prod = pm.create_product("AIOS Hub", "Empower AI networks")
    assert prod["name"] == "AIOS Hub"

    startup = AIStartup("Cognitive AI Corp")
    startup.hire("Lead AI Engineer", 0.95)
    startup.raise_funding(1000000.0)
    assert len(startup.team) == 1
    assert startup.funding == 1000000.0
