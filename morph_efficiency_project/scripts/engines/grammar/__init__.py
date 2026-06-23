"""
engines/grammar/
================
Sentence-level grammar layer per language.

Each module exposes:
    split_into_sentences(text) -> List[List[str]]
    disambiguate_pos(tokens)   -> List[TokenInfo]
    validate_sentence(tokens)  -> Tuple[bool, str]

The engines call these from analyze_sentence() to enrich per-word morphological
analysis with neighbour context and to enforce language-specific structural rules.
"""
