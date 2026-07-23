"""Prompts full ops."""
from aios_core.prompts import PromptManager
def test(): s=PromptManager().stats(); assert isinstance(s,dict)
