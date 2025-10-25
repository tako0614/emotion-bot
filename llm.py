"""
LLM functionality removed.

This file previously contained functions to generate insults/praise/comfort using a local model.
Per request to keep only the "きもち" (emotion) and "きもい" (kimoi) features, the heavy LLM code has been replaced
with lightweight stubs to avoid accidental expensive model loads.

If you later want to restore these features, re-add the implementation here or recover from Git history.
"""

def generate_insult(_text: str) -> str:
    return "(insult generation removed)"

def generate_praise(_text: str) -> str:
    return "(praise generation removed)"

def generate_comfort(_text: str) -> str:
    return "(comfort generation removed)"

