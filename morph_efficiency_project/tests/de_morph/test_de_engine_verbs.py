"""
test_de_engine_verbs.py
-----------------------
Verb morphology tests: weak conjugation, strong verbs, modals, Partizip II/I.

Run: python -m pytest morph_efficiency_project/tests/de_morph/test_de_engine_verbs.py -v
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import GermanEngine
import pytest

engine = GermanEngine()

# ── Weak verb Präsens conjugation ────────────────────────────────────────────

WEAK_PRESENT = [
    ("mache",   "machen", {"tense": "PRES", "person": "1", "num": "SG"}, "1SG"),
    ("machst",  "machen", {"tense": "PRES", "person": "2", "num": "SG"}, "2SG"),
    ("macht",   "machen", {"tense": "PRES"}, "3SG/2PL"),
    ("machen",  "machen", {"tense": "PRES", "person": "1", "num": "PL"}, "1PL/3PL"),
    ("spielst", "spielen", {"tense": "PRES", "person": "2", "num": "SG"}, "spielen 2SG"),
    ("spielen", "spielen", {"tense": "PRES", "person": "1", "num": "PL"}, "spielen inf/1PL"),
    ("arbeite", "arbeiten", {"tense": "PRES", "person": "1", "num": "SG"}, "arbeiten 1SG"),
    ("lernst",  "lernen", {"tense": "PRES", "person": "2", "num": "SG"}, "lernen 2SG"),
    ("lernt",   "lernen", {"tense": "PRES"}, "lernen 3SG"),
    ("lernen",  "lernen", {"tense": "PRES", "person": "1", "num": "PL"}, "lernen 1PL"),
    ("kaufe",   "kaufen", {"tense": "PRES", "person": "1", "num": "SG"}, "kaufen 1SG"),
    ("kaufst",  "kaufen", {"tense": "PRES", "person": "2", "num": "SG"}, "kaufen 2SG"),
    ("kauft",   "kaufen", {"tense": "PRES"}, "kaufen 3SG"),
    ("zeige",   "zeigen", {"tense": "PRES", "person": "1", "num": "SG"}, "zeigen 1SG"),
    ("zeigst",  "zeigen", {"tense": "PRES", "person": "2", "num": "SG"}, "zeigen 2SG"),
]


@pytest.mark.parametrize("surface, root, tag_subset, desc", WEAK_PRESENT)
def test_weak_present(surface, root, tag_subset, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r}"
    assert info.pos == "VERB", f"[{desc}] pos: {info.pos!r}"
    for k, v in tag_subset.items():
        assert info.tags.get(k) == v, f"[{desc}] tag {k}: {info.tags.get(k)!r} != {v!r}"


# ── Weak verb Präteritum ─────────────────────────────────────────────────────

WEAK_PAST = [
    ("machte",    "machen", {"tense": "PAST", "person": "1", "num": "SG"}, "1SG"),
    ("machtest",  "machen", {"tense": "PAST", "person": "2", "num": "SG"}, "2SG"),
    ("machten",   "machen", {"tense": "PAST", "person": "1", "num": "PL"}, "1PL"),
    ("machtet",   "machen", {"tense": "PAST", "person": "2", "num": "PL"}, "2PL"),
    ("spielte",   "spielen", {"tense": "PAST", "person": "1", "num": "SG"}, "spielen 1SG"),
    ("spieltest", "spielen", {"tense": "PAST", "person": "2", "num": "SG"}, "spielen 2SG"),
    ("spielten",  "spielen", {"tense": "PAST", "person": "1", "num": "PL"}, "spielen 1PL"),
    ("spieltet",  "spielen", {"tense": "PAST", "person": "2", "num": "PL"}, "spielen 2PL"),
    ("lernte",    "lernen", {"tense": "PAST", "person": "1", "num": "SG"}, "lernen 1SG"),
    ("lerntest",  "lernen", {"tense": "PAST", "person": "2", "num": "SG"}, "lernen 2SG"),
    ("lernten",   "lernen", {"tense": "PAST", "person": "1", "num": "PL"}, "lernen 1PL"),
    ("lerntet",   "lernen", {"tense": "PAST", "person": "2", "num": "PL"}, "lernen 2PL"),
    ("kaufte",    "kaufen", {"tense": "PAST", "person": "1", "num": "SG"}, "kaufen 1SG"),
    ("kauftest",  "kaufen", {"tense": "PAST", "person": "2", "num": "SG"}, "kaufen 2SG"),
]


@pytest.mark.parametrize("surface, root, tag_subset, desc", WEAK_PAST)
def test_weak_past(surface, root, tag_subset, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r}"
    assert info.pos == "VERB", f"[{desc}] pos: {info.pos!r}"
    for k, v in tag_subset.items():
        assert info.tags.get(k) == v, f"[{desc}] tag {k}: {info.tags.get(k)!r} != {v!r}"


# ── Partizip II (weak regular) ───────────────────────────────────────────────

PARTIZIP_II_WEAK = [
    ("gemacht",   "machen",   "weak ge-...-t"),
    ("gespielt",  "spielen",  "weak ge-...-t"),
    ("gelernt",   "lernen",   "weak ge-...-t"),
    ("gekauft",   "kaufen",   "weak ge-...-t"),
    ("gehört",    "hören",    "weak ge-...-t with umlaut stem"),
    ("gezeigt",   "zeigen",   "weak ge-...-t"),
    ("gefragt",   "fragen",   "weak ge-...-t"),
    ("gelegt",    "legen",    "weak ge-...-t"),
    ("gesetzt",   "setzen",   "weak ge-...-t"),
]


@pytest.mark.parametrize("surface, root, desc", PARTIZIP_II_WEAK)
def test_partizip_ii_weak(surface, root, desc):
    info = engine.analyze(surface)
    assert info.pos == "VERB", f"[{desc}] pos: {info.pos!r}"
    assert info.tags.get("aspect") == "PERF", f"[{desc}] aspect: {info.tags!r}"


# ── Partizip II (strong irregular, from irregulars.json) ─────────────────────

PARTIZIP_II_STRONG = [
    ("gesungen",     "singen",     "strong -en"),
    ("gegeben",      "geben",      "strong -en"),
    ("genommen",     "nehmen",     "strong -en"),
    ("gesprochen",   "sprechen",   "strong -en"),
    ("geholfen",     "helfen",     "strong -en"),
    ("getrunken",    "trinken",    "strong -en"),
    ("gefunden",     "finden",     "strong -en"),
    ("geschrieben",  "schreiben",  "strong -en"),
    ("gelesen",      "lesen",      "strong -en"),
    ("gefahren",     "fahren",     "strong -en"),
    ("gelaufen",     "laufen",     "strong -en"),
    ("gefallen",     "fallen",     "strong -en"),
    ("gehalten",     "halten",     "strong -en"),
    ("geschlafen",   "schlafen",   "strong -en"),
    ("getragen",     "tragen",     "strong -en"),
    ("gewaschen",    "waschen",    "strong -en"),
    ("gewachsen",    "wachsen",    "strong -en"),
    ("gebrochen",    "brechen",    "strong -en"),
    ("gestorben",    "sterben",    "strong -en"),
    ("geworfen",     "werfen",     "strong -en"),
    ("getroffen",    "treffen",    "strong -en"),
    ("gegolten",     "gelten",     "strong -en"),
    ("gekommen",     "kommen",     "strong -en"),
    ("gegangen",     "gehen",      "irregular"),
    ("gestanden",    "stehen",     "irregular"),
    ("gewesen",      "sein",       "irregular"),
    ("gehabt",       "haben",      "irregular"),
    ("geworden",     "werden",     "irregular"),
    ("getan",        "tun",        "irregular"),
]


@pytest.mark.parametrize("surface, root, desc", PARTIZIP_II_STRONG)
def test_partizip_ii_strong(surface, root, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.pos == "VERB", f"[{desc}] pos: {info.pos!r}"
    assert info.tags.get("aspect") == "PERF", f"[{desc}] tags: {info.tags!r}"


# ── Partizip II with separable prefix ────────────────────────────────────────

PARTIZIP_II_SEPARABLE = [
    ("aufgemacht",    "machen",   "AUF",  "separable auf-"),
    ("eingeladen",    "laden",    "EIN",  "separable ein-"),
    ("zugemacht",     "machen",   "ZU",   "separable zu-"),
    ("abgeholt",      "holen",    "AB",   "separable ab-"),
    ("angerufen",     "rufen",    "AN",   "separable an-"),
    ("ausgemacht",    "machen",   "AUS",  "separable aus-"),
    ("mitgebracht",   "bringen",  "MIT",  "separable mit-"),
]


@pytest.mark.parametrize("surface, root_substr, prefix, desc", PARTIZIP_II_SEPARABLE)
def test_partizip_ii_separable(surface, root_substr, prefix, desc):
    info = engine.analyze(surface)
    assert info.pos == "VERB", f"[{desc}] pos: {info.pos!r}"
    assert info.tags.get("aspect") == "PERF", f"[{desc}] tags: {info.tags!r}"
    assert info.tags.get("verb_prefix") == prefix, f"[{desc}] prefix: {info.tags.get('verb_prefix')!r}"


# ── Partizip I ───────────────────────────────────────────────────────────────

PARTIZIP_I = [
    ("laufend",     "laufen",    "laufen"),
    ("singend",     "singen",    "singen"),
    ("spielend",    "spielen",   "spielen"),
    ("lachend",     "lachen",    "lachen"),
    ("schlafend",   "schlafen",  "schlafen"),
    ("kommend",     "kommen",    "kommen"),
]


@pytest.mark.parametrize("surface, root, desc", PARTIZIP_I)
def test_partizip_i(surface, root, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.pos == "VERB", f"[{desc}] pos: {info.pos!r}"
    assert info.tags.get("aspect") == "PROG", f"[{desc}] tags: {info.tags!r}"


# ── Strong verb Präteritum (from irregulars) ─────────────────────────────────

STRONG_PAST = [
    ("sang",    "singen",   "singen past"),
    ("gab",     "geben",    "geben past"),
    ("nahm",    "nehmen",   "nehmen past"),
    ("sprach",  "sprechen", "sprechen past"),
    ("half",    "helfen",   "helfen past"),
    ("trank",   "trinken",  "trinken past"),
    ("fand",    "finden",   "finden past"),
    ("schrieb", "schreiben","schreiben past"),
    ("fuhr",    "fahren",   "fahren past"),
    ("lief",    "laufen",   "laufen past"),
    ("fiel",    "fallen",   "fallen past"),
    ("hielt",   "halten",   "halten past"),
    ("schlief", "schlafen", "schlafen past"),
    ("trug",    "tragen",   "tragen past"),
    ("wusch",   "waschen",  "waschen past"),
    ("warf",    "werfen",   "werfen past"),
    ("traf",    "treffen",  "treffen past"),
    ("kam",     "kommen",   "kommen past"),
    ("ging",    "gehen",    "gehen past"),
    ("stand",   "stehen",   "stehen past"),
]


@pytest.mark.parametrize("surface, root, desc", STRONG_PAST)
def test_strong_past(surface, root, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.tags.get("tense") == "PAST", f"[{desc}] tense: {info.tags!r}"


# ── Strong verb irregular Präsens (2SG/3SG) ────────────────────────────────

STRONG_PRESENT = [
    ("gibt",     "geben",     "geben 3SG"),
    ("gibst",    "geben",     "geben 2SG"),
    ("nimmt",    "nehmen",    "nehmen 3SG"),
    ("nimmst",   "nehmen",    "nehmen 2SG"),
    ("spricht",  "sprechen",  "sprechen 3SG"),
    ("hilft",    "helfen",    "helfen 3SG"),
    ("fährt",    "fahren",    "fahren 3SG"),
    ("läuft",    "laufen",    "laufen 3SG"),
    ("fällt",    "fallen",    "fallen 3SG"),
    ("hält",     "halten",    "halten 3SG"),
    ("schläft",  "schlafen",  "schlafen 3SG"),
    ("trägt",    "tragen",    "tragen 3SG"),
    ("wirft",    "werfen",    "werfen 3SG"),
    ("trifft",   "treffen",   "treffen 3SG"),
    ("gilt",     "gelten",    "gelten 3SG"),
    ("liest",    "lesen",     "lesen 3SG"),
    ("isst",     "essen",     "essen 3SG"),
]


@pytest.mark.parametrize("surface, root, desc", STRONG_PRESENT)
def test_strong_present(surface, root, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.tags.get("tense") == "PRES", f"[{desc}] tense: {info.tags!r}"


# ── Modal verbs ─────────────────────────────────────────────────────────────

MODAL_CASES = [
    ("kann",    "können",   "können 1SG/3SG"),
    ("kannst",  "können",   "können 2SG"),
    ("muss",    "müssen",   "müssen 1SG/3SG"),
    ("musst",   "müssen",   "müssen 2SG"),
    ("darf",    "dürfen",   "dürfen 1SG/3SG"),
    ("darfst",  "dürfen",   "dürfen 2SG"),
    ("soll",    "sollen",   "sollen 1SG/3SG"),
    ("sollst",  "sollen",   "sollen 2SG"),
    ("will",    "wollen",   "wollen 1SG/3SG"),
    ("willst",  "wollen",   "wollen 2SG"),
    ("mag",     "mögen",    "mögen 1SG/3SG"),
    ("magst",   "mögen",    "mögen 2SG"),
]


@pytest.mark.parametrize("surface, root, desc", MODAL_CASES)
def test_modal_verbs(surface, root, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.tags.get("modal") == "YES", f"[{desc}] modal tag missing: {info.tags!r}"


# ── Mixed verb Präteritum ───────────────────────────────────────────────────

MIXED_PAST = [
    ("kannte",   "kennen",  "kennen past"),
    ("nannte",   "nennen",  "nennen past"),
    ("rannte",   "rennen",  "rennen past"),
    ("brannte",  "brennen", "brennen past"),
    ("dachte",   "denken",  "denken past"),
    ("brachte",  "bringen", "bringen past"),
    ("sandte",   "senden",  "senden past"),
    ("wusste",   "wissen",  "wissen past"),
]


@pytest.mark.parametrize("surface, root, desc", MIXED_PAST)
def test_mixed_past(surface, root, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.tags.get("tense") == "PAST", f"[{desc}] tense: {info.tags!r}"


# ── Mixed verb Partizip II ───────────────────────────────────────────────────

MIXED_PARTIZIP = [
    ("gekannt",   "kennen",  "kennen"),
    ("genannt",   "nennen",  "nennen"),
    ("gerannt",   "rennen",  "rennen"),
    ("gebrannt",  "brennen", "brennen"),
    ("gedacht",   "denken",  "denken"),
    ("gebracht",  "bringen", "bringen"),
    ("gesandt",   "senden",  "senden"),
    ("gewusst",   "wissen",  "wissen"),
]


@pytest.mark.parametrize("surface, root, desc", MIXED_PARTIZIP)
def test_mixed_partizip(surface, root, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.tags.get("aspect") == "PERF", f"[{desc}] tags: {info.tags!r}"


# ── sein/haben/werden forms ─────────────────────────────────────────────────

SEIN_HABEN = [
    ("bin",   "sein",   "VERB", "sein 1SG"),
    ("bist",  "sein",   "VERB", "sein 2SG"),
    ("ist",   "sein",   "VERB", "sein 3SG"),
    ("sind",  "sein",   "VERB", "sein 1PL"),
    ("seid",  "sein",   "VERB", "sein 2PL"),
    ("war",   "sein",   "VERB", "sein past 1SG"),
    ("habe",  "haben",  "VERB", "haben 1SG"),
    ("hast",  "haben",  "VERB", "haben 2SG"),
    ("hat",   "haben",  "VERB", "haben 3SG"),
    ("hatte", "haben",  "VERB", "haben past 1SG"),
    ("werde", "werden", "VERB", "werden 1SG"),
    ("wirst", "werden", "VERB", "werden 2SG"),
    ("wird",  "werden", "VERB", "werden 3SG"),
    ("wurde", "werden", "VERB", "werden past"),
]


@pytest.mark.parametrize("surface, root, pos, desc", SEIN_HABEN)
def test_sein_haben_werden(surface, root, pos, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.pos == pos, f"[{desc}] pos: {info.pos!r} != {pos!r}"


# ── Separable prefix infinitives ────────────────────────────────────────────

SEPARABLE_INF = [
    ("aufmachen",  "machen",  "AUF",  "auf+machen"),
    ("zumachen",   "machen",  "ZU",   "zu+machen"),
    ("einladen",   "laden",   "EIN",  "ein+laden"),
    ("ausgehen",   "gehen",   "AUS",  "aus+gehen"),
    ("ankommen",   "kommen",  "AN",   "an+kommen"),
    ("mitnehmen",  "nehmen",  "MIT",  "mit+nehmen"),
    ("abfahren",   "fahren",  "AB",   "ab+fahren"),
    ("vorlesen",   "lesen",   "VOR",  "vor+lesen"),
]


@pytest.mark.parametrize("surface, root, prefix, desc", SEPARABLE_INF)
def test_separable_infinitive(surface, root, prefix, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.pos == "VERB", f"[{desc}] pos: {info.pos!r}"
    assert info.tags.get("verb_prefix") == prefix, f"[{desc}] prefix: {info.tags!r}"


# ── Non-separable prefix Partizip II ────────────────────────────────────────

NONSEP_PARTIZIP = [
    ("besucht",     "besuchen",     "non-sep be-"),
    ("erzählt",     "erzählen",     "non-sep er-"),
    ("verstanden",  "verstanden",   "non-sep ver- (from irregulars or rule)"),
    ("entdeckt",    "entdecken",    "non-sep ent-"),
    ("zerbrochen",  "zerbrochen",   "non-sep zer- (if in irregulars)"),
]


@pytest.mark.parametrize("surface, root_contains, desc", NONSEP_PARTIZIP)
def test_nonsep_partizip(surface, root_contains, desc):
    info = engine.analyze(surface)
    assert info.pos == "VERB", f"[{desc}] pos: {info.pos!r}"
    assert info.tags.get("aspect") == "PERF", f"[{desc}] tags: {info.tags!r}"


# ── Konjunktiv II forms ─────────────────────────────────────────────────────

KONJ_II = [
    ("wäre",     "sein",    "mood=SUBJ_II", "sein Konj II"),
    ("hätte",    "haben",   "mood=SUBJ_II", "haben Konj II"),
    ("würde",    "werden",  "mood=SUBJ_II", "werden Konj II"),
    ("könnte",   "können",  "mood=SUBJ_II", "können Konj II"),
    ("müsste",   "müssen",  "mood=SUBJ_II", "müssen Konj II"),
    ("dürfte",   "dürfen",  "mood=SUBJ_II", "dürfen Konj II"),
    ("möchte",   "mögen",   "mood=SUBJ_II", "mögen Konj II"),
]


@pytest.mark.parametrize("surface, root, mood_tag, desc", KONJ_II)
def test_konjunktiv_ii(surface, root, mood_tag, desc):
    info = engine.analyze(surface)
    assert info.root == root, f"[{desc}] root: {info.root!r} != {root!r}"
    assert info.tags.get("mood") == "SUBJ_II", f"[{desc}] mood: {info.tags!r}"
