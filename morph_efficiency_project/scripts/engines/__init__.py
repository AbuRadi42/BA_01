"""
engines/__init__.py
-------------------
Public API for all three grammar engines.

Usage:
    from morph_efficiency_project.scripts.engines import EnglishEngine, ArabicEngine, TurkishEngine
    from morph_efficiency_project.scripts.engines import TokenInfo, MorphVocab
"""

from .shared import (
    TokenInfo,
    MorphVocab,
    check_morph_sequence_en,
    check_morph_sequence_ar,
    check_morph_sequence_tr,
    validate_sentence_structure_en,
    validate_sentence_structure_ar,
    validate_sentence_structure_tr,
)
from .en_engine import EnglishEngine
from .ar_engine import ArabicEngine
from .tr_engine import TurkishEngine

__all__ = [
    "TokenInfo", "MorphVocab",
    "EnglishEngine", "ArabicEngine", "TurkishEngine",
    "check_morph_sequence_en", "check_morph_sequence_ar", "check_morph_sequence_tr",
    "validate_sentence_structure_en", "validate_sentence_structure_ar", "validate_sentence_structure_tr",
]
