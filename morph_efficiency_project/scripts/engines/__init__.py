"""
engines/__init__.py
-------------------
Public API for all grammar engines.

Usage:
    from morph_efficiency_project.scripts.engines import EnglishEngine, ArabicEngine, TurkishEngine, MandarinEngine, SpanishEngine, HungarianEngine
    from morph_efficiency_project.scripts.engines import TokenInfo, MorphVocab
"""

from .shared import (
    TokenInfo,
    MorphVocab,
    check_morph_sequence_en,
    check_morph_sequence_ar,
    check_morph_sequence_tr,
    check_morph_sequence_zh,
    check_morph_sequence_es,
    check_morph_sequence_de,
    check_morph_sequence_hu,
    check_morph_sequence_sw,
    validate_sentence_structure_en,
    validate_sentence_structure_ar,
    validate_sentence_structure_tr,
    validate_sentence_structure_zh,
    validate_sentence_structure_es,
    validate_sentence_structure_de,
    validate_sentence_structure_hu,
    validate_sentence_structure_sw,
)
from .en_engine import EnglishEngine
from .ar_engine import ArabicEngine
from .tr_engine import TurkishEngine
from .zh_engine import MandarinEngine
from .es_engine import SpanishEngine
from .de_engine import GermanEngine
from .hu_engine import HungarianEngine
from .sw_engine import SwahiliEngine

__all__ = [
    "TokenInfo", "MorphVocab",
    "EnglishEngine", "ArabicEngine", "TurkishEngine", "MandarinEngine",
    "SpanishEngine", "GermanEngine", "HungarianEngine", "SwahiliEngine",
    "check_morph_sequence_en", "check_morph_sequence_ar", "check_morph_sequence_tr",
    "check_morph_sequence_zh", "check_morph_sequence_es", "check_morph_sequence_de",
    "check_morph_sequence_hu", "check_morph_sequence_sw",
    "validate_sentence_structure_en", "validate_sentence_structure_ar",
    "validate_sentence_structure_tr", "validate_sentence_structure_zh",
    "validate_sentence_structure_es", "validate_sentence_structure_de",
    "validate_sentence_structure_hu", "validate_sentence_structure_sw",
]
