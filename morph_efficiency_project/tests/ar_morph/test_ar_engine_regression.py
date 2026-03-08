"""
test_ar_engine_core.py
----------------------
Regression suite: merged diamond (276) + audit (42) tests, deduplicated.
Covers all engine branches: Steps A/B/C, proclitic/enclitic guards,
weak roots, augmented forms, closed-class intercept, circumfix, and
false-positive guards.

Run: python -m pytest morph_efficiency_project/tests/ar/test_ar_engine_core.py -v
  or: python morph_efficiency_project/tests/ar/test_ar_engine_core.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import ArabicEngine
import pytest

engine = ArabicEngine()

# Format: (surface, expected_root, expected_template_or_None, label)
# expected_template=None  -> only check root
CASES = [
    # ── Form I sound trilateral ───────────────────────────────────────────────
    ("ضَرَبَ",       "ضرب",  "VERB_TRILATERAL_BARE",  "Form I daraba"),
    ("رَكَضَ",       "ركض",  "VERB_TRILATERAL_BARE",  "Form I rakada"),
    ("حَمَلَ",       "حمل",  "VERB_TRILATERAL_BARE",  "Form I hamala"),
    ("شَرِبَ",       "شرب",  "VERB_TRILATERAL_BARE",  "Form I shariba"),
    ("نَزَلَ",       "نزل",  "VERB_TRILATERAL_BARE",  "Form I nazala"),
    ("رَفَعَ",       "رفع",  "VERB_TRILATERAL_BARE",  "Form I rafa3a"),
    ("قَطَعَ",       "قطع",  "VERB_TRILATERAL_BARE",  "Form I qata3a"),
    ("فَهِمَ",       "فهم",  "VERB_TRILATERAL_BARE",  "Form I fahima"),
    ("حَفِظَ",       "حفظ",  "VERB_TRILATERAL_BARE",  "Form I hafidha"),
    ("طَبَخَ",       "طبخ",  "VERB_TRILATERAL_BARE",  "Form I tabakha"),
    ("رَسَمَ",       "رسم",  "VERB_TRILATERAL_BARE",  "Form I rasama"),
    ("سَبَحَ",       "سبح",  "VERB_TRILATERAL_BARE",  "Form I sabaha"),
    ("قَفَزَ",       "قفز",  "VERB_TRILATERAL_BARE",  "Form I qafaza"),
    ("غَسَلَ",       "غسل",  "VERB_TRILATERAL_BARE",  "Form I ghasala"),
    ("لَبِسَ",       "لبس",  "VERB_TRILATERAL_BARE",  "Form I labisa"),
    ("سَمِعَ",       "سمع",  "VERB_TRILATERAL_BARE",  "Form I sami3a"),
    ("كَبُرَ",       "كبر",  "VERB_TRILATERAL_BARE",  "Form I kabura"),
    ("بَدَأَ",       "بدء",  "VERB_TRILATERAL_BARE",  "Form I bada'a hamzated"),
    ("سَأَلَ",       "سءل",  "VERB_TRILATERAL_BARE",  "Form I sa'ala medial hamza"),
    ("لَجَأَ",       "لجء",  "VERB_TRILATERAL_BARE",  "Form I laja'a final hamza"),
    ("نَشَأَ",       "نشء",  "VERB_TRILATERAL_BARE",  "Form I nasha'a final hamza"),
    # ── Form II ───────────────────────────────────────────────────────────────
    ("دَرَّسَ",       "درس",  None,  "Form II darrasa"),
    ("فَسَّرَ",       "فسر",  None,  "Form II fassara"),
    ("رَتَّبَ",       "رتب",  None,  "Form II rattaba"),
    ("نَظَّفَ",       "نظف",  None,  "Form II nadhdhafa"),
    ("حَسَّنَ",       "حسن",  None,  "Form II hassana"),
    ("قَرَّرَ",       "قرر",  None,  "Form II qarrara"),
    ("صَوَّرَ",       "صور",  None,  "Form II sawwara"),
    ("وَسَّعَ",       "وسع",  None,  "Form II wassa3a"),
    # ── Form III ──────────────────────────────────────────────────────────────
    ("قَاتَلَ",       "قتل",  None,  "Form III qatala"),
    ("شَارَكَ",       "شرك",  None,  "Form III sharaka"),
    ("رَاجَعَ",       "رجع",  None,  "Form III raja3a"),
    ("نَاقَشَ",       "نقش",  None,  "Form III naqasha"),
    ("عَامَلَ",       "عمل",  None,  "Form III 3amala"),
    ("سَاعَدَ",       "سعد",  None,  "Form III sa3ada"),
    # ── Form IV ───────────────────────────────────────────────────────────────
    ("أَنْجَزَ",      "نجز",  "VERB_AUGMENTED_IV",  "Form IV anjaza"),
    ("أَبْلَغَ",      "بلغ",  "VERB_AUGMENTED_IV",  "Form IV ablagha"),
    ("أَحْضَرَ",      "حضر",  "VERB_AUGMENTED_IV",  "Form IV ahdara"),
    ("أَفَادَ",       "فيد",  "VERB_AUGMENTED_IV",  "Form IV afada ajwaf-ya"),
    ("أَضَافَ",       "ضيف",  "VERB_AUGMENTED_IV",  "Form IV adafa ajwaf-ya"),
    ("أَقَامَ",       "قوم",  "VERB_AUGMENTED_IV",  "Form IV aqama ajwaf-waw"),
    # ── Form V ────────────────────────────────────────────────────────────────
    ("تَدَرَّبَ",     "درب",  "VERB_AUGMENTED_V_VI",  "Form V tadarraba"),
    ("تَطَوَّرَ",     "طور",  "VERB_AUGMENTED_V_VI",  "Form V tatawwara"),
    ("تَحَسَّنَ",     "حسن",  "VERB_AUGMENTED_V_VI",  "Form V tahassana"),
    ("تَذَكَّرَ",     "ذكر",  "VERB_AUGMENTED_V_VI",  "Form V tadhakkara"),
    ("تَأَخَّرَ",     "ءخر",  "VERB_AUGMENTED_V_VI",  "Form V ta'akhkhara"),
    # ── Form VI ───────────────────────────────────────────────────────────────
    ("تَبَادَلَ",     "بدل",  "VERB_AUGMENTED_V_VI",  "Form VI tabadala"),
    ("تَعَاوَنَ",     "عون",  "VERB_AUGMENTED_V_VI",  "Form VI ta3awana ajwaf"),
    ("تَسَاءَلَ",     "سءل",  "VERB_AUGMENTED_V_VI",  "Form VI tasa'ala hamzated"),
    # ── Form VII ──────────────────────────────────────────────────────────────
    ("اِنْفَجَرَ",    "فجر",  "VERB_AUGMENTED_VII",  "Form VII infajara"),
    ("اِنْسَحَبَ",    "سحب",  "VERB_AUGMENTED_VII",  "Form VII insahaba"),
    ("اِنْقَطَعَ",    "قطع",  "VERB_AUGMENTED_VII",  "Form VII inqata3a"),
    ("اِنْكَشَفَ",    "كشف",  "VERB_AUGMENTED_VII",  "Form VII inkashafa"),
    ("اِنْهَزَمَ",    "هزم",  "VERB_AUGMENTED_VII",  "Form VII inhazama"),
    # ── Form VIII ─────────────────────────────────────────────────────────────
    ("اِعْتَقَدَ",    "عقد",  "VERB_AUGMENTED_VIII",  "Form VIII i3taqada"),
    ("اِنْتَظَرَ",    "نظر",  "VERB_AUGMENTED_VIII",  "Form VIII intadhara"),
    ("اِبْتَسَمَ",    "بسم",  "VERB_AUGMENTED_VIII",  "Form VIII ibtasama"),
    ("اِرْتَفَعَ",    "رفع",  "VERB_AUGMENTED_VIII",  "Form VIII irtafa3a"),
    ("اِحْتَاجَ",     "حوج",  "VERB_AUGMENTED_VIII",  "Form VIII ihtaja ajwaf-waw"),
    ("اِخْتَارَ",     "خير",  "VERB_AUGMENTED_VIII",  "Form VIII ikhtara ajwaf ya"),
    ("اِلْتَقَى",     "لقي",  "VERB_AUGMENTED_VIII",  "Form VIII iltaqa naqis"),
    ("اِحْتَرَمَ",    "حرم",  "VERB_AUGMENTED_VIII",  "Form VIII ihtarama"),
    ("انتخاب",        "نخب",  "VERB_AUGMENTED_VIII",  "Form VIII unvoweled intikab"),
    ("اِكْتَسَبَ",    "كسب",  "VERB_AUGMENTED_VIII",  "Form VIII iktasaba"),
    ("اِتَّصَلَ",     "وصل",  "VERB_AUGMENTED_VIII",  "Form VIII ittasala waw-assim"),
    ("اِتَّخَذَ",     "ءخذ",  "VERB_AUGMENTED_VIII",  "Form VIII ittakhadha hamza-assim"),
    ("اِطَّلَعَ",     "طلع",  "VERB_AUGMENTED_VIII",  "Form VIII ittala3a emphatic"),
    ("اِضْطَرَّ",     "ضرر",  "VERB_AUGMENTED_VIII",  "Form VIII idtarra emphatic"),
    # ── Form IX ───────────────────────────────────────────────────────────────
    ("اِحْمَرَّ",     "حمر",  None,  "Form IX ihmarra"),
    ("اِسْوَدَّ",     "سود",  None,  "Form IX iswadda"),
    # ── Form X ────────────────────────────────────────────────────────────────
    ("اِسْتَعْمَلَ",  "عمل",  "VERB_AUGMENTED_X",  "Form X ista3mala"),
    ("اِسْتَقَالَ",   "قول",  "VERB_AUGMENTED_X",  "Form X istaqala ajwaf-waw"),
    ("اِسْتَعَدَّ",   "عدد",  "VERB_AUGMENTED_X",  "Form X ista3adda geminate"),
    ("اِسْتَمَرَّ",   "مرر",  "VERB_AUGMENTED_X",  "Form X istamarra geminate"),
    ("اِسْتَحَقَّ",   "حقق",  "VERB_AUGMENTED_X",  "Form X istahaqqa geminate"),
    ("اِسْتَقَرَّ",   "قرر",  "VERB_AUGMENTED_X",  "Form X istaqarra geminate"),
    ("اِسْتَغْفَرَ",  "غفر",  "VERB_AUGMENTED_X",  "Form X istaghfara"),
    ("اِسْتَقْبَلَ",  "قبل",  "VERB_AUGMENTED_X",  "Form X istaqbala"),
    # ── أجوف واو ──────────────────────────────────────────────────────────────
    ("كَانَ",         "كون",  None,  "ajwaf waw kana"),
    ("عَادَ",         "عود",  None,  "ajwaf waw 3ada"),
    ("قَامَ",         "قوم",  None,  "ajwaf waw qama"),
    ("مَاتَ",         "موت",  None,  "ajwaf waw mata"),
    ("خَافَ",         "خوف",  None,  "ajwaf waw khafa"),
    ("هَانَ",         "هون",  None,  "ajwaf waw hana"),
    ("رَاحَ",         "روح",  None,  "ajwaf waw raha"),
    ("جَالَ",         "جول",  None,  "ajwaf waw jala"),
    ("دَارَ",         "دور",  None,  "ajwaf waw dara"),
    ("طَالَ",         "طول",  None,  "ajwaf waw tala"),
    # ── أجوف يا ───────────────────────────────────────────────────────────────
    ("عَاشَ",         "عيش",  None,  "ajwaf ya 3asha"),
    ("نَالَ",         "نيل",  None,  "ajwaf ya nala"),
    ("غَابَ",         "غيب",  None,  "ajwaf ya ghaba"),
    ("مَالَ",         "ميل",  None,  "ajwaf ya mala"),
    ("ضَاقَ",         "ضيق",  None,  "ajwaf ya daqa"),
    ("كَادَ",         "كيد",  None,  "ajwaf ya kada"),
    ("حَادَ",         "حيد",  None,  "ajwaf ya hada"),
    ("لَانَ",         "لين",  None,  "ajwaf ya lana"),
    # ── ناقص ──────────────────────────────────────────────────────────────────
    ("بَنَى",         "بنو",  None,  "naqis waw bana"),
    ("سَعَى",         "سعو",  None,  "naqis waw sa3a"),
    ("جَرَى",         "جرو",  None,  "naqis waw jara"),
    ("هَدَى",         "هدي",  None,  "naqis ya hada"),
    ("قَضَى",         "قضي",  None,  "naqis ya qada"),
    ("مَضَى",         "مضي",  None,  "naqis ya mada"),
    ("نَهَى",         "نهي",  None,  "naqis ya naha"),
    ("أَتَى",         "ءتو",  None,  "naqis waw ata hamzated"),
    # ── مثال ──────────────────────────────────────────────────────────────────
    ("وَزَنَ",        "وزن",  None,  "mithal waw wazana"),
    ("وَهَبَ",        "وهب",  None,  "mithal waw wahaba"),
    ("وَرَدَ",        "ورد",  None,  "mithal waw warada"),
    ("وَقَعَ",        "وقع",  None,  "mithal waw waqa3a"),
    ("وَثَقَ",        "وثق",  None,  "mithal waw wathaqa"),
    # ── Geminate (مضعّف) ──────────────────────────────────────────────────────
    ("فَرَّ",          "فرر",  None,  "geminate farra"),
    ("دَلَّ",          "دلل",  None,  "geminate dalla"),
    ("عَدَّ",          "عدد",  None,  "geminate 3adda"),
    ("مَدَّ",          "مدد",  None,  "geminate madda"),
    ("تَمَّ",          "تمم",  None,  "geminate tamma"),
    ("ظَلَّ",          "ظلل",  None,  "geminate dhalla"),
    ("شَدَّ",          "شدد",  None,  "geminate shadda"),
    # ── Hamzated (مهموز) ──────────────────────────────────────────────────────
    ("أَمَرَ",         "ءمر",  None,  "hamza initial amara"),
    ("أَكَلَ",         "ءكل",  None,  "hamza initial akala"),
    ("أَخَذَ",         "ءخذ",  None,  "hamza initial akhadha"),
    ("سَأَلَ",         "سءل",  None,  "hamza medial sa'ala"),
    ("بَدَأَ",         "بدء",  None,  "hamza final bada'a"),
    ("لَجَأَ",         "لجء",  None,  "hamza final laja'a"),
    ("نَشَأَ",         "نشء",  None,  "hamza final nasha'a"),
    ("قَرَأَ",         "قرء",  None,  "hamza final qara'a"),
    # ── NOM_DERIVED ───────────────────────────────────────────────────────────
    ("مُدِير",         "دور",  "NOM_DERIVED",  "NOM_DERIVED mudir ajwaf waw"),
    ("مُشَارِك",       "شرك",  "NOM_DERIVED",  "NOM_DERIVED musharik"),
    ("مُسَافِر",       "سفر",  "NOM_DERIVED",  "NOM_DERIVED musafir"),
    ("مَكْتُوب",       "كتب",  "NOM_DERIVED",  "NOM_DERIVED maktub passive participle"),
    ("مَفْهُوم",       "فهم",  "NOM_DERIVED",  "NOM_DERIVED mafhum passive participle"),
    ("مَسْمُوع",       "سمع",  "NOM_DERIVED",  "NOM_DERIVED masmu3 passive participle"),
    ("مَطْبَخ",        "طبخ",  "NOM_DERIVED",  "NOM_DERIVED matbakh place noun"),
    ("مَلْعَب",        "لعب",  "NOM_DERIVED",  "NOM_DERIVED mal3ab place noun"),
    ("مَسْبَح",        "سبح",  "NOM_DERIVED",  "NOM_DERIVED masbah place noun"),
    ("مَكْتَب",        "كتب",  "NOM_DERIVED",  "NOM_DERIVED maktab place noun"),
    ("مَدْخَل",        "دخل",  "NOM_DERIVED",  "NOM_DERIVED madkhal place noun"),
    ("مَخْرَج",        "خرج",  "NOM_DERIVED",  "NOM_DERIVED makhraj place noun"),
    ("مَدِينَة",       "مدن",  None,  "ta marbuta madina NOM_DERIVED internal-ya strip"),
    ("مَدْرَسَة",      "درس",  "NOM_DERIVED",  "ta marbuta madrasa"),
    ("مَكْتَبَة",      "كتب",  "NOM_DERIVED",  "ta marbuta maktaba"),
    ("مُعَلِّمَة",     "علم",  "NOM_DERIVED",  "ta marbuta mu3allima"),
    ("صَحِيفَة",       "صحف",  None,  "ta marbuta sahifa root صحف"),
    ("سَفِينَة",       "سفن",  None,  "ta marbuta safina root سفن"),
    # ── Stacked proclitics ────────────────────────────────────────────────────
    ("وَذَهَبَ",       "ذهب",  None,  "waw conj + verb voweled"),
    ("فَرَجَعَ",       "رجع",  None,  "fa conj + verb voweled"),
    ("وَجَلَسَ",       "جلس",  None,  "waw conj + verb voweled"),
    ("فَقَرَأَ",       "قرء",  None,  "fa conj + hamzated verb"),
    ("وذهب",           "ذهب",  None,  "unvoweled waw + verb"),
    ("فرجع",           "رجع",  None,  "unvoweled fa + verb"),
    ("بِالْبَيْتِ",    "بيت",  None,  "bi+al stacked proclitic"),
    ("لِلْمَدْرَسَةِ", "درس",  "NOM_DERIVED",  "li+li stacked + NOM_DERIVED"),
    ("وَبِالْكِتَابِ", "كتب",  None,  "wa+bi+al triple proclitic"),
    ("فَبِالْعِلْمِ",  "علم",  None,  "fa+bi+al triple proclitic"),
    ("كَالْأَسَدِ",    "ءسد",  None,  "ka+al proclitic + hamzated noun"),
    # ── Proclitic false-positive guards ──────────────────────────────────────
    ("بَدَأَ",         "بدء",  None,  "voweled ba = root, not proclitic"),
    ("فَهِمَ",         "فهم",  None,  "voweled fa = root, not proclitic"),
    ("سَمِعَ",         "سمع",  None,  "voweled sa = root, not proclitic"),
    ("لَبِسَ",         "لبس",  None,  "voweled la = root, not proclitic"),
    ("كَبُرَ",         "كبر",  None,  "voweled ka = root, not proclitic"),
    ("وَصَلَ",         "وصل",  None,  "voweled wa = mithal root, not proclitic"),
    # ── Enclitic stripping ────────────────────────────────────────────────────
    ("كَتَبَهُ",       "كتب",  None,  "3MSG enclitic hu"),
    ("كَتَبَهُمَا",    "كتب",  None,  "3DU enclitic huma"),
    ("كَتَبَكَ",       "كتب",  None,  "2MSG enclitic ka"),
    ("كَتَبَنِي",      "كتب",  None,  "1SG enclitic ni"),
    ("ضَرَبَهُ",       "ضرب",  None,  "3MSG enclitic hu on daraba"),
    ("ضَرَبَهَا",      "ضرب",  None,  "3FSG enclitic ha on daraba"),
    ("ضَرَبَهُمْ",     "ضرب",  None,  "3MPL enclitic hum on daraba"),
    ("ضَرَبَنَا",      "ضرب",  None,  "1PL enclitic na on daraba"),
    # ── Enclitic false-positive guards ───────────────────────────────────────
    ("يَرْمِي",        "رمي",  None,  "imperfect ya + naqis ya rami"),
    ("يَمْشِي",        "مشي",  None,  "imperfect ya + naqis ya yamshi"),
    ("يَبْكِي",        "بكي",  None,  "imperfect ya + naqis ya yabki"),
    ("يَسْعَى",        "سعو",  None,  "imperfect ya + naqis waw yas3a"),
    ("يَبْنِي",        "بنو",  None,  "imperfect ya + naqis waw yabni"),
    ("يَقْضِي",        "قضي",  None,  "imperfect ya + naqis ya yaqdhi"),
    ("نَسِيَ",         "نسي",  None,  "naqis ya nasiya voweled ya NOT stripped"),
    # ── Imperfect prefix يَ stripping ─────────────────────────────────────────
    ("يَكْتُبُ",       "كتب",  None,  "imperfect ya yaktub"),
    ("يَذْهَبُ",       "ذهب",  None,  "imperfect ya yadhab"),
    ("يَجْلِسُ",       "جلس",  None,  "imperfect ya yajlis"),
    ("يَفْهَمُ",       "فهم",  None,  "imperfect ya yafham"),
    ("يَعْمَلُ",       "عمل",  None,  "imperfect ya ya3mal"),
    ("يَضْرِبُ",       "ضرب",  None,  "imperfect ya yadrib"),
    ("يَقْرَأُ",       "قرء",  None,  "imperfect ya + hamzated yaqra'"),
    ("يَسْأَلُ",       "سءل",  None,  "imperfect ya + medial hamza yas'al"),
    # ── Circumfix لام + نون ───────────────────────────────────────────────────
    ("لَيَذْهَبَنَّ",  "ذهب",  None,  "circumfix LAM_NUN on dhahaba"),
    ("لَيَضْرِبَنَّ",  "ضرب",  None,  "circumfix LAM_NUN on daraba"),
    ("لَيَجْلِسَنَّ",  "جلس",  None,  "circumfix LAM_NUN on jalasa"),
    ("لَيَفْهَمَنَّ",  "فهم",  None,  "circumfix LAM_NUN on fahima"),
    # ── Audit cases: Form VI, IX, doubly-weak, Form VIII assimilation ─────────
    ("تَعَاوَنَ",      "عون",  "VERB_AUGMENTED_V_VI",  "Form VI ta3awana ajwaf"),
    ("وَقَى",          "وقي",  None,  "doubly-weak waqa"),
    ("وَفَى",          "وفي",  None,  "doubly-weak wafa"),
    ("وَاتَّصَلَ",     "وصل",  "VERB_AUGMENTED_VIII",  "wa + Form VIII ittasala"),
    ("مُقَاتِل",       "قتل",  "NOM_DERIVED",  "NOM_DERIVED Form III muqatil"),
    ("مُسْتَقْبِل",    "قبل",  "NOM_DERIVED_X",  "NOM_DERIVED Form X mustaqbil"),
    ("مُسْتَشَار",     "شور",  "NOM_DERIVED_X",  "NOM_DERIVED Form X mustashar ajwaf"),
    ("كُتُب",          "كتب",  None,  "broken plural kutub"),
    ("رِجَال",         "رجل",  None,  "broken plural rijal"),
    ("أَقْلَام",       "قلم",  None,  "broken plural aqlam"),
    ("بُيُوت",         "بيت",  None,  "broken plural buyut"),
    ("عُيُون",         "عين",  None,  "broken plural 3uyun"),
    ("تَعْلِيم",       "علم",  None,  "masdar ta3lim Form II"),
    ("تَفْسِير",       "فسر",  None,  "masdar tafsir Form II"),
    ("مُشَارَكَة",     "شرك",  "NOM_DERIVED",  "masdar musharaka Form III"),
    ("إِنْجَاز",       "نجز",  None,  "masdar injaz Form IV"),
    ("اِسْتِعْمَال",   "عمل",  "VERB_AUGMENTED_X",  "masdar isti3mal Form X"),
    ("أَكْبَر",        "كبر",  None,  "elative akbar"),
    ("أَصْغَر",        "صغر",  None,  "elative asghar"),
    ("أَحْسَن",        "حسن",  None,  "elative ahsan"),
    ("كُبْرَى",        "كبر",  None,  "fem elative kubra"),
    ("صُغْرَى",        "صغر",  None,  "fem elative sughra"),
    ("عَرَبِيّ",       "عرب",  None,  "nisba 3arabi"),
    ("مِصْرِيّ",       "مصر",  None,  "nisba misri"),
    ("ضَرْب",          "ضرب",  None,  "masdar I darb"),
    ("فَهْم",          "فهم",  None,  "masdar I fahm"),
    ("تَكْتُبُ",       "كتب",  None,  "imperfect ta 2nd/3rd F"),
    ("تَذْهَبُ",       "ذهب",  None,  "imperfect ta"),
    ("نَكْتُبُ",       "نكت",  None,  "imperfect na 1PL"),
    ("أَكْتُبُ",       "كتب",  None,  "imperfect a 1SG"),
    ("كِتَابٌ",        "كتب",  None,  "tanwin dammatain"),
    ("رَجُلٍ",         "رجل",  None,  "tanwin kasratan"),
    ("مُحَمَّد",       "حمد",  None,  "proper noun muhammad"),
    ("مُرَاعٍ",        "رعع",  "NOM_DERIVED",  "AP_WEAK Form III mura3in"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tmpl,label", CASES)
def test_ar_engine(surface, exp_root, exp_tmpl, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, f"[{label}] root={ti.root!r} expected={exp_root!r}"
    if exp_tmpl is not None:
        assert ti.template == exp_tmpl, (
            f"[{label}] template={ti.template!r} expected={exp_tmpl!r}"
        )

if __name__ == "__main__":
    passed = failed = 0
    failures = []
    for surface, exp_root, exp_tmpl, label in CASES:
        ti = engine.analyze(surface)
        root_ok = ti.root == exp_root
        tmpl_ok = exp_tmpl is None or ti.template == exp_tmpl
        if root_ok and tmpl_ok:
            passed += 1
        else:
            failed += 1
            msgs = []
            if not root_ok:
                msgs.append(f"root={ti.root!r} exp={exp_root!r}")
            if not tmpl_ok:
                msgs.append(f"tmpl={ti.template!r} exp={exp_tmpl!r}")
            failures.append(f"  FAIL  {surface:<22}  {label}  ->  {' | '.join(msgs)}")
    print(f"\n{'='*70}")
    print(f"  Arabic Engine Core Regression Suite")
    print(f"{'='*70}")
    print(f"  {passed} passed,  {failed} failed  (total {passed+failed})")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f)
    else:
        print("\n  All tests passed.")
    import sys; sys.exit(0 if failed == 0 else 1)
