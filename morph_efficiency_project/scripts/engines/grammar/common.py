"""
engines/grammar/common.py
=========================
Shared utilities for sentence-level grammar modules:
    - sentence terminator detection
    - abbreviation handling
    - basic tokenization helpers
"""

from typing import List, Tuple


# Latin-script sentence terminators
LATIN_TERMINATORS = set(".!?;")

# Arabic-script sentence terminators
ARABIC_TERMINATORS = set("؟؛")

# Chinese sentence terminators (CJK punctuation)
CJK_TERMINATORS = set("。！？；…")

# Conservative English abbreviation list (extend per-language as needed)
COMMON_ABBREVIATIONS = {
    "Dr.", "Mr.", "Mrs.", "Ms.", "Jr.", "Sr.", "Prof.", "St.",
    "U.S.A.", "U.K.", "U.S.", "e.g.", "i.e.", "etc.", "vs.",
    "Inc.", "Ltd.", "Co.", "Corp.",
}


def is_sentence_terminator(token: str, terminators: set, abbrevs: set) -> bool:
    """Return True if `token` ends a sentence."""
    if not token:
        return False
    if token in abbrevs:
        return False
    return token[-1] in terminators


def split_on_punctuation(text: str, terminators: set, abbrevs: set = None) -> List[List[str]]:
    """Tokenize on whitespace and split into sentences on terminator-final tokens.

    Returns a list of sentences, each a list of word tokens.
    """
    if abbrevs is None:
        abbrevs = set()
    sentences: List[List[str]] = []
    current: List[str] = []
    for word in text.split():
        current.append(word)
        if is_sentence_terminator(word, terminators, abbrevs):
            sentences.append(current)
            current = []
    if current:
        sentences.append(current)
    return sentences
