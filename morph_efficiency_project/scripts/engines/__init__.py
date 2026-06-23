"""
engines/__init__.py
-------------------
Public API for the four target grammar engines.

Usage:
    from morph_efficiency_project.scripts.engines import (
        EnglishEngine, ArabicEngine, TurkishEngine, MandarinEngine,
        TokenInfo, MorphVocab,
    )
"""

from .shared import (
    TokenInfo,
    MorphVocab,
    check_morph_sequence_en,
    check_morph_sequence_ar,
    check_morph_sequence_tr,
    check_morph_sequence_zh,
    validate_sentence_structure_en,
    validate_sentence_structure_ar,
    validate_sentence_structure_tr,
    validate_sentence_structure_zh,
)
from .en_engine import EnglishEngine
from .ar_engine import ArabicEngine
from .tr_engine import TurkishEngine
from .zh_engine import MandarinEngine

__all__ = [
    "TokenInfo", "MorphVocab",
    "EnglishEngine", "ArabicEngine", "TurkishEngine", "MandarinEngine",
    "check_morph_sequence_en", "check_morph_sequence_ar",
    "check_morph_sequence_tr", "check_morph_sequence_zh",
    "validate_sentence_structure_en", "validate_sentence_structure_ar",
    "validate_sentence_structure_tr", "validate_sentence_structure_zh",
]
