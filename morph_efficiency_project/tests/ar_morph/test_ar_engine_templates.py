"""
test_ar_templates.py
--------------------
Systematic coverage: 2 words minimum per template category × 348 templates.
Organized to mirror ar_templates.json category structure.

Run: python -m pytest morph_efficiency_project/tests/ar/test_ar_templates.py -v
  or: python morph_efficiency_project/tests/ar/test_ar_templates.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from morph_efficiency_project.scripts.engines import ArabicEngine
import pytest

engine = ArabicEngine()

# Format: (surface, expected_root, expected_template_or_None, label)
CASES = [

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_TRILATERAL_BARE — 6 paradigms × 2 words each + 8 extra
    # ══════════════════════════════════════════════════════════════════════════
    # Paradigm I-a/u (فَعَلَ/يَفْعُلُ)
    ("نَصَرَ",        "نصر",  "VERB_TRILATERAL_BARE",  "I-a/u nasara"),
    ("كَتَبَ",        "كتب",  "VERB_TRILATERAL_BARE",  "I-a/u kataba"),
    # Paradigm I-a/i (فَعَلَ/يَفْعِلُ)
    ("ضَرَبَ",        "ضرب",  "VERB_TRILATERAL_BARE",  "I-a/i daraba"),
    ("جَلَسَ",        "جلس",  "VERB_TRILATERAL_BARE",  "I-a/i jalasa"),
    # Paradigm I-a/a (فَعَلَ/يَفْعَلُ)
    ("فَتَحَ",        "فتح",  "VERB_TRILATERAL_BARE",  "I-a/a fataha"),
    ("ذَهَبَ",        "ذهب",  "VERB_TRILATERAL_BARE",  "I-a/a dhahaba"),
    # Paradigm I-i/a (فَعِلَ/يَفْعَلُ)
    ("فَرِحَ",        "فرح",  "VERB_TRILATERAL_BARE",  "I-i/a fariha"),
    ("عَلِمَ",        "علم",  "VERB_TRILATERAL_BARE",  "I-i/a 3alima"),
    # Paradigm I-u/u (فَعُلَ/يَفْعُلُ)
    ("كَرُمَ",        "كرم",  "VERB_TRILATERAL_BARE",  "I-u/u karuma"),
    ("حَسُنَ",        "حسن",  "VERB_TRILATERAL_BARE",  "I-u/u hasuna"),
    # Paradigm I-i/i (فَعِلَ/يَفْعِلُ)
    ("حَسِبَ",        "حسب",  "VERB_TRILATERAL_BARE",  "I-i/i hasiba"),
    ("وَرِثَ",        "ورث",  "VERB_TRILATERAL_BARE",  "I-i/i waritha"),
    # Extra — common strong verbs across all paradigms
    ("شَرِبَ",        "شرب",  "VERB_TRILATERAL_BARE",  "I-a/i shariba"),
    ("سَمِعَ",        "سمع",  "VERB_TRILATERAL_BARE",  "I-a/i sami3a"),
    ("خَرَجَ",        "خرج",  "VERB_TRILATERAL_BARE",  "I-a/u kharaja"),
    ("دَخَلَ",        "دخل",  "VERB_TRILATERAL_BARE",  "I-a/u dakhala"),
    ("رَجَعَ",        "رجع",  "VERB_TRILATERAL_BARE",  "I-a/i raja3a"),
    ("حَمَلَ",        "حمل",  "VERB_TRILATERAL_BARE",  "I-a/i hamala"),
    ("عَمِلَ",        "عمل",  "VERB_TRILATERAL_BARE",  "I-a/a 3amila"),
    ("فَعَلَ",        "فعل",  "VERB_TRILATERAL_BARE",  "I-a/a fa3ala paradigm"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_AUGMENTED — Forms II–XV
    # ══════════════════════════════════════════════════════════════════════════
    # Form II فَعَّلَ
    ("عَلَّمَ",       "علم",  None,  "Form II 3allama"),
    ("دَرَّسَ",       "درس",  None,  "Form II darrasa"),
    ("كَسَّرَ",       "كسر",  None,  "Form II kassara"),
    ("قَدَّمَ",       "قدم",  None,  "Form II qaddama"),
    ("صَوَّرَ",       "صور",  None,  "Form II sawwara"),
    ("نَظَّفَ",       "نظف",  None,  "Form II nadhdhafa"),
    # Form III فَاعَلَ
    ("كَاتَبَ",       "كتب",  None,  "Form III kataba"),
    ("قَاتَلَ",       "قتل",  None,  "Form III qatala"),
    ("شَارَكَ",       "شرك",  None,  "Form III sharaka"),
    ("رَاسَلَ",       "رسل",  None,  "Form III rasala"),
    ("جَادَلَ",       "جدل",  None,  "Form III jadala"),
    ("سَاعَدَ",       "سعد",  None,  "Form III sa3ada"),
    # Form IV أَفْعَلَ
    ("أَخْرَجَ",      "خرج",  "VERB_AUGMENTED_IV",  "Form IV akhraja"),
    ("أَنْجَزَ",      "نجز",  "VERB_AUGMENTED_IV",  "Form IV anjaza"),
    ("أَعْطَى",       "عطو",  "VERB_AUGMENTED_IV",  "Form IV a3ta ajwaf"),
    ("أَسْلَمَ",      "سلم",  "VERB_AUGMENTED_IV",  "Form IV aslama"),
    ("أَكْمَلَ",      "كمل",  "VERB_AUGMENTED_IV",  "Form IV akmala"),
    ("أَرْسَلَ",      "رسل",  "VERB_AUGMENTED_IV",  "Form IV arsala"),
    # Form V تَفَعَّلَ
    ("تَعَلَّمَ",     "علم",  "VERB_AUGMENTED_V_VI",  "Form V ta3allama"),
    ("تَدَرَّبَ",     "درب",  "VERB_AUGMENTED_V_VI",  "Form V tadarraba"),
    ("تَكَسَّرَ",     "كسر",  "VERB_AUGMENTED_V_VI",  "Form V takassara"),
    ("تَقَدَّمَ",     "قدم",  "VERB_AUGMENTED_V_VI",  "Form V taqaddama"),
    ("تَصَوَّرَ",     "صور",  "VERB_AUGMENTED_V_VI",  "Form V tasawwara"),
    ("تَكَلَّمَ",     "كلم",  "VERB_AUGMENTED_V_VI",  "Form V takallama"),
    # Form VI تَفَاعَلَ
    ("تَفَاهَمَ",     "فهم",  "VERB_AUGMENTED_V_VI",  "Form VI tafaahama"),
    ("تَبَادَلَ",     "بدل",  "VERB_AUGMENTED_V_VI",  "Form VI tabadala"),
    ("تَشَارَكَ",     "شرك",  "VERB_AUGMENTED_V_VI",  "Form VI tasharaka"),
    ("تَرَاسَلَ",     "رسل",  "VERB_AUGMENTED_V_VI",  "Form VI tarasala"),
    ("تَجَادَلَ",     "جدل",  "VERB_AUGMENTED_V_VI",  "Form VI tajadala"),
    ("تَسَاعَدَ",     "سعد",  "VERB_AUGMENTED_V_VI",  "Form VI tasa3ada"),
    # Form VII اِنْفَعَلَ
    ("اِنْكَسَرَ",    "كسر",  "VERB_AUGMENTED_VII",  "Form VII inkasara"),
    ("اِنْفَجَرَ",    "فجر",  "VERB_AUGMENTED_VII",  "Form VII infajara"),
    ("اِنْكَتَبَ",    "كتب",  "VERB_AUGMENTED_VII",  "Form VII inkataba"),
    ("اِنْهَدَمَ",    "هدم",  "VERB_AUGMENTED_VII",  "Form VII inhadama"),
    ("اِنْقَطَعَ",    "قطع",  "VERB_AUGMENTED_VII",  "Form VII inqata3a"),
    ("اِنْسَحَبَ",    "سحب",  "VERB_AUGMENTED_VII",  "Form VII insahaba"),
    # Form VIII اِفْتَعَلَ
    ("اِكْتَسَبَ",    "كسب",  "VERB_AUGMENTED_VIII",  "Form VIII iktasaba"),
    ("اِعْتَقَدَ",    "عقد",  "VERB_AUGMENTED_VIII",  "Form VIII i3taqada"),
    ("اِجْتَمَعَ",    "جمع",  "VERB_AUGMENTED_VIII",  "Form VIII ijtama3a"),
    ("اِنْتَخَبَ",    "نخب",  "VERB_AUGMENTED_VIII",  "Form VIII intakhaba"),
    ("اِحْتَرَمَ",    "حرم",  "VERB_AUGMENTED_VIII",  "Form VIII ihtarama"),
    # Form IX اِفْعَلَّ
    ("اِحْمَرَّ",     "حمر",  None,  "Form IX ihmarra"),
    ("اِسْوَدَّ",     "سود",  None,  "Form IX iswadda"),
    ("اِخْضَرَّ",     "خضر",  None,  "Form IX ikhdarr"),
    ("اِزْرَقَّ",     "زرق",  None,  "Form IX izraqq"),
    ("اِصْفَرَّ",     "صفر",  None,  "Form IX isfar"),
    # Form X اِسْتَفْعَلَ
    ("اِسْتَخْدَمَ",  "خدم",  "VERB_AUGMENTED_X",  "Form X istakhdama"),
    ("اِسْتَعْمَلَ",  "عمل",  "VERB_AUGMENTED_X",  "Form X ista3mala"),
    ("اِسْتَقْبَلَ",  "قبل",  "VERB_AUGMENTED_X",  "Form X istaqbala"),
    ("اِسْتَفَادَ",   "فيد",  "VERB_AUGMENTED_X",  "Form X istafada ajwaf"),
    ("اِسْتَمَعَ",    "معي",  "VERB_AUGMENTED_X",  "Form X istama3a ajwaf"),
    ("اِسْتَمَرَّ",   "مرر",  "VERB_AUGMENTED_X",  "Form X istamarra geminate"),
    ("اِسْتَحَقَّ",   "حقق",  "VERB_AUGMENTED_X",  "Form X istahaqqa geminate"),
    # Form XI اِفْعَالَّ
    ("اِحْمَارَّ",    "حمر",  None,  "Form XI ihmarra intensive"),
    ("اِبْيَاضَّ",    "بيض",  None,  "Form XI ibyada intensive"),
    ("اِخْضَارَّ",    "خضر",  None,  "Form XI ikhdarr intensive"),
    ("اِزْرَاقَّ",    "زرق",  None,  "Form XI izraqq intensive"),
    ("اِصْفَارَّ",    "صفر",  None,  "Form XI isfar intensive"),
    # Form XII اِفْعَوْعَلَ
    ("اِخْشَوْشَنَ",  "خشن",  None,  "Form XII ikhshawshana"),
    ("اِعْشَوْشَبَ",  "عشب",  None,  "Form XII i3shawshaba"),
    ("اِغْدَوْدَنَ",  "غدن",  None,  "Form XII ighdawdana"),
    ("اِحْلَوْلَى",   "حلو",  None,  "Form XII ihlawla"),
    ("اِعْوَجَّ",     "عوج",  None,  "Form XII i3wajja"),
    # Form XIII اِفْعَوَّلَ
    ("اِجْلَوَّذَ",   "اجلوذ", None,  "Form XIII ijlawwadha"),
    ("اِعْلَوَّطَ",   "اعلوط",  None,  "Form XIII i3lawwata"),
    ("اِسْلَنْقَى",   "اسلنقى", "VERB_TRILATERAL_UNKNOWN",  "Form XIII islanqa"),
    ("اِحْبَنْطَى",   "احبنطى", "VERB_TRILATERAL_UNKNOWN",  "Form XIII ihbanta"),
    # Form XIV اِفَّعَّلَ
    ("اِسَّحَّنَ",    "اسحن",  None,  "Form XIV issahanna"),
    ("اِشَّعَّرَ",    "اشعر",  None,  "Form XIV isha33ara"),
    ("اِشَّعَّلَ",    "اشعل",  "VERB_AUGMENTED",  "Form XIV isha33ala"),
    ("اِسَّكَّنَ",    "اسكن",  "VERB_AUGMENTED",  "Form XIV issakana"),
    # Form XV اِفَّاعَلَ
    ("اِحْبَنْطَى",   "احبنطى",None,  "Form XV ihbantaa"),
    ("اِسْلَنْقَى",   "اسلنقى",None,  "Form XV islanqa"),
    ("اِحْرَنْجَمَ",  "احرنجم", "VERB_TRILATERAL_UNKNOWN",  "Form XV ihranjama"),
    ("اِقْعَنْسَسَ",  "اقعنسس", "VERB_TRILATERAL_UNKNOWN",  "Form XV iq3ansasa"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_RESEMBLING_QUAD — Q-I through Q-IV + MULHAQ forms
    # ══════════════════════════════════════════════════════════════════════════
    # Q-I فَعْلَلَ
    ("دَحْرَجَ",      "دحرج", None,  "Q-I dahrajah"),
    ("زَلْزَلَ",      "زلزل", None,  "Q-I zalzala"),
    ("تَرْجَمَ",      "رجم",  None,  "Q-I tarjama"),
    ("بَرْهَنَ",      "برهن", None,  "Q-I barhana"),
    ("قَرْطَسَ",      "قرطس", None,  "Q-I qartasa"),
    # Q-II تَفَعْلَلَ
    ("تَدَحْرَجَ",    "دحرج", None,  "Q-II tadahrajah"),
    ("تَزَلْزَلَ",    "زلزل", None,  "Q-II tazalzala"),
    ("تَتَرْجَمَ",    "ترجم", "VERB_RESEMBLING_QUAD_II",  "Q-II tatarjama"),
    ("تَبَرْهَنَ",    "برهن", "VERB_RESEMBLING_QUAD_II",  "Q-II tabarhana"),
    ("تَقَرْطَسَ",    "قرطس", "VERB_RESEMBLING_QUAD_II",  "Q-II taqartasa"),
    # Q-III اِفْعَلَلَّ
    ("اِطْمَأَنَّ",   "طمء",  "VERB_AUGMENTED_VIII",  "Q-III itma'anna"),
    ("اِقْشَعَرَّ",   "اقشعر", "VERB_TRILATERAL_UNKNOWN",  "Q-III iqsha3arra"),    # Q-IV اِفْعَنْلَلَ
    ("اِحْرَنْجَمَ",  "احرنجم", "VERB_TRILATERAL_UNKNOWN",  "Q-IV ihranjama"),
    ("اِسْلَنْقَى",   "اسلنقى", "VERB_TRILATERAL_UNKNOWN",  "Q-IV islanqa"),
    # MULHAQ-فعول
    ("جَهْوَرَ",      "جهر",  "VERB_AUGMENTED",  "MULHAQ-fa3wala jahwara"),
    ("بَهْوَسَ",      "بهس",  None,  "MULHAQ-fa3wala bahwasa"),
    ("حَوْقَلَ",      "حوقل", "VERB_AUGMENTED",  "MULHAQ-fa3wala hawqala"),
    # MULHAQ-فوعل
    ("سَوْقَلَ",      "سوق",  None,  "MULHAQ-faw3ala sawqala"),
    ("بَيْطَرَ",      "بوط",  "VERB_AUGMENTED",  "MULHAQ-faw3ala baytara"),
    ("شَيْطَنَ",      "شيط",  "VERB_AUGMENTED",  "MULHAQ-faw3ala shaytana"),
    # MULHAQ-فعيل
    ("قَلْنَسَ",      "قلنس", "VERB_AUGMENTED",  "MULHAQ-fa3yala qalnasa"),
    ("رَنْقَعَ",      "رنق",  "VERB_AUGMENTED",  "MULHAQ-fa3yala ranqa3a"),
    # MULHAQ-فعنل
    ("قَلْنَسَ",      "قلنس", None,  "MULHAQ-fa3nala qalnasa"),
    ("رَنْقَعَ",      "رنق",  None,  "MULHAQ-fan3ala ranqa3a"),
    # MULHAQ-مفعل
    ("مَسْكَنَ",      "سكن",  "NOM_DERIVED",  "MULHAQ-maf3ala maskana"),
    ("مَرْحَبَ",      "رحب",  "NOM_DERIVED",  "MULHAQ-maf3ala marhaba"),
    # MULHAQ-فعلى
    ("سَلْقَى",       "سلق",  "VERB_AUGMENTED",  "MULHAQ-fa3la salqa"),
    ("جَلْفَظَ",      "جلف",  "VERB_AUGMENTED",  "MULHAQ-fa3la jalfadha"),

    # ══════════════════════════════════════════════════════════════════════════
    # MASDAR — Form I patterns (فَعْل، فِعْل، فُعْل، فَعَل، فُعُل، فِعَل،
    #          فَعِل، فَعُل، فِعَال، فُعَال، فُعُول، فَعِيل، فَعَالَة،
    #          فُعُولَة، فَعَلَان، فُعْلَان، نِسْيَان)
    # ══════════════════════════════════════════════════════════════════════════
    ("ضَرْب",         "ضرب",  None,  "MASDAR fa3l darb"),
    ("فَهْم",         "فهم",  None,  "MASDAR fa3l fahm"),
    ("عِلْم",         "علم",  None,  "MASDAR fi3l 3ilm"),
    ("حِلْم",         "حلم",  None,  "MASDAR fi3l hilm"),
    ("حُكْم",         "حكم",  None,  "MASDAR fu3l hukm"),
    ("صُلْح",         "صلح",  None,  "MASDAR fu3l sulh"),
    ("أَمَل",         "ءمل",  None,  "MASDAR fa3al amal"),
    ("فَرَح",         "فرح",  None,  "MASDAR fa3al farah"),
    ("شُكُر",         "شكر",  None,  "MASDAR fu3ul shukur"),
    ("عِنَب",         "عنب",  None,  "MASDAR fi3al 3inab"),
    ("نَهِر",         "نهر",  None,  "MASDAR fa3il nahir"),
    ("عَضُل",         "عضل",  None,  "MASDAR fa3ul 3adul"),
    ("ذِهَاب",        "ذهب",  None,  "MASDAR fi3al dhihab"),
    ("كِتَاب",        "كتب",  None,  "MASDAR fi3al kitab"),
    ("سُعَال",        "سعل",  None,  "MASDAR fu3al su3al"),
    ("صُرَاخ",        "صرخ",  None,  "MASDAR fu3al surakh"),
    ("دُخُول",        "دخل",  None,  "MASDAR fu3ul dukhul"),
    ("خُرُوج",        "خرج",  None,  "MASDAR fu3ul khuruj"),
    ("رَحِيل",        "رحل",  None,  "MASDAR fa3il rahil"),
    ("كِتَابَة",      "كتب",  None,  "MASDAR fa3ala kitaba"),
    ("دِرَاسَة",      "درس",  None,  "MASDAR fa3ala dirasa"),
    ("سُهُولَة",      "سهل",  None,  "MASDAR fu3ula suhula"),
    ("صُعُوبَة",      "صعب",  None,  "MASDAR fu3ula su3uba"),
    ("طَوَفَان",      "طوف",  None,  "MASDAR fa3alan tawafan"),
    ("غُفْرَان",      "غفر",  None,  "MASDAR fu3lan ghufran"),
    ("نِسْيَان",      "نسي",  None,  "MASDAR fi3lan nisyan"),
    # Form II masdar تَفْعِيل
    ("تَعْلِيم",      "علم",  None,  "MASDAR Form II ta3lim"),
    ("تَفْسِير",      "فسر",  None,  "MASDAR Form II tafsir"),
    ("تَدْرِيس",      "درس",  None,  "MASDAR Form II tadris"),
    ("تَكْسِير",      "كسر",  None,  "MASDAR Form II taksir"),
    ("تَقْدِيم",      "قدم",  None,  "MASDAR Form II taqdim"),
    # Form II masdar تَفْعِلَة
    ("تَزْكِيَة",     "زكي",  None,  "MASDAR Form II tazkiya"),
    ("تَسْمِيَة",     "سمو",  None,  "MASDAR Form II tasmiya"),
    ("تَرْبِيَة",     "ربو",  None,  "MASDAR Form II tarbiya"),
    ("تَوْصِيَة",     "وصي",  None,  "MASDAR Form II tawsiya"),
    # Form II masdar فِعَّال
    ("كِذَّاب",       "كذب",  None,  "MASDAR Form II kidhdhab"),
    ("قَتَّال",       "قتل",  None,  "MASDAR Form II qattal"),
    ("فَسَّاق",       "فسق",  None,  "MASDAR Form II fassaq"),
    ("ضَرَّاب",       "ضرب",  None,  "MASDAR Form II darrab"),
    # Form III masdar مُفَاعَلَة
    ("مُكَاتَبَة",    "كتب",  None,  "MASDAR Form III mukataba"),
    ("مُشَارَكَة",    "شرك",  None,  "MASDAR Form III musharaka"),
    ("مُقَاتَلَة",    "قتل",  None,  "MASDAR Form III muqatala"),
    ("مُسَاعَدَة",    "سعد",  None,  "MASDAR Form III musa3ada"),
    # Form III masdar فِعَال
    ("قِتَال",        "قتل",  None,  "MASDAR Form III qital"),
    ("جِدَال",        "جدل",  None,  "MASDAR Form III jidal"),
    ("صِرَاع",        "صرع",  None,  "MASDAR Form III sira3"),
    ("نِزَاع",        "نزع",  None,  "MASDAR Form III niza3"),
    # Form IV masdar إِفْعَال
    ("إِخْرَاج",      "خرج",  None,  "MASDAR Form IV ikhrāj"),
    ("إِنْجَاز",      "نجز",  None,  "MASDAR Form IV injaz"),
    ("إِسْلَام",      "سلم",  "MASDAR_FORM_IV",  "MASDAR Form IV islam"),
    ("إِكْمَال",      "كمل",  "MASDAR_FORM_IV",  "MASDAR Form IV ikmal"),
    # Form IV masdar إِفَالَة (ajwaf)
    ("إِقَامَة",      "قوم",  None,  "MASDAR Form IV iqama ajwaf"),
    ("إِدَارَة",      "دور",  None,  "MASDAR Form IV idara ajwaf"),
    ("إِزَالَة",      "زول",  "MASDAR_FORM_IV",  "MASDAR Form IV izala ajwaf"),
    ("إِفَادَة",      "فيد",  "MASDAR_FORM_IV",  "MASDAR Form IV ifada ajwaf"),
    # Form V masdar تَفَعُّل
    ("تَعَلُّم",      "علم",  None,  "MASDAR Form V ta3allum"),
    ("تَطَوُّر",      "طور",  None,  "MASDAR Form V tatawwur"),
    ("تَطَوُّع",      "طوع",  None,  "MASDAR Form V tatawwu3"),
    ("تَقَدُّم",      "قدم",  None,  "MASDAR Form V taqaddum"),
    # Form VI masdar تَفَاعُل
    ("تَفَاهُم",      "تفا",   None,  "MASDAR Form VI tafahum"),
    ("تَعَاوُن",      "عون",  None,  "MASDAR Form VI ta3awun"),
    ("تَبَادُل",      "بدل",  None,  "MASDAR Form VI tabadal"),    # Form VII masdar اِنْفِعَال
    ("اِنْكِسَار",    "كسر",  None,  "MASDAR Form VII inkisar"),
    ("اِنْفِجَار",    "فجر",  None,  "MASDAR Form VII infijār"),
    ("اِنْهِيَار",    "هور",  "VERB_AUGMENTED_VII",  "MASDAR Form VII inhiyar"),
    ("اِنْسِحَاب",    "سحب",  "VERB_AUGMENTED_VII",  "MASDAR Form VII insihab"),
    # Form VIII masdar اِفْتِعَال
    ("اِكْتِسَاب",    "كسب",  None,  "MASDAR Form VIII iktisab"),
    ("اِخْتِيَار",    "خير",  None,  "MASDAR Form VIII ikhtiyar ajwaf"),
    ("اِجْتِمَاع",    "جمع",  "VERB_AUGMENTED_VIII",  "MASDAR Form VIII ijtima3"),
    ("اِنْتِخَاب",    "نخب",  "VERB_AUGMENTED_VIII",  "MASDAR Form VIII intikab"),
    # Form IX masdar اِفْعِلَال
    ("اِحْمِرَار",    "حمر",  None,  "MASDAR Form IX ihmirār"),
    ("اِسْوِدَاد",    "سود",  None,  "MASDAR Form IX iswidad"),
    ("اِخْضِرَار",    "خضر",  "MASDAR_FORM_IX",  "MASDAR Form IX ikhdirar"),
    ("اِزْرِقَاق",    "زرق",  "MASDAR_FORM_IX",  "MASDAR Form IX izriqaq"),
    # Form X masdar اِسْتِفْعَال
    ("اِسْتِخْدَام",  "خدم",  None,  "MASDAR Form X istikhdām"),
    ("اِسْتِعْمَال",  "عمل",  None,  "MASDAR Form X isti3māl"),
    ("اِسْتِقْبَال",  "قبل",  "VERB_AUGMENTED_X",  "MASDAR Form X istiqbal"),
    ("اِسْتِفَادَة",  "فيد",  "VERB_AUGMENTED_X",  "MASDAR Form X istifada"),
    # Form X masdar اِسْتِفَالَة (ajwaf)
    ("اِسْتِقَامَة",  "قوم",  None,  "MASDAR Form X istiqama ajwaf"),
    ("اِسْتِدَارَة",  "دور",  None,  "MASDAR Form X istidara ajwaf"),
    ("اِسْتِعَانَة",  "عين",  "VERB_AUGMENTED_X",  "MASDAR Form X isti3ana ajwaf"),
    ("اِسْتِجَابَة",  "جيب",  "VERB_AUGMENTED_X",  "MASDAR Form X istijaba ajwaf"),
    # Form XI masdar اِفْعِيلَال
    ("اِحْمِيرَار",   "حمر",  None,  "MASDAR Form XI ihmiyrar"),
    ("اِبْيِيضَاض",   "بيض",  None,  "MASDAR Form XI ibiyyadh"),
    ("اِخْضِيرَار",   "خضر",  "MASDAR_FORM_XI",  "MASDAR Form XI ikhdirar intensive"),
    ("اِزْرِيقَاق",   "زرق",  "MASDAR_FORM_XI",  "MASDAR Form XI izriqaq intensive"),
    # Form XII masdar اِفْعِيعَال
    ("اِخْشِيشَان",   "خشن",  None,  "MASDAR Form XII ikhshishan"),
    ("اِعْشِيشَاب",   "عشب",  None,  "MASDAR Form XII i3shishab"),
    ("اِعْشِيشَاب",   "عشب",  "MASDAR_FORM_XII",  "MASDAR Form XII i3shishab2"),
    ("اِغْدِيدَان",   "غدن",  "MASDAR_FORM_XII",  "MASDAR Form XII ighdidan"),
    # Q-I masdar فَعْلَلَة
    ("دَحْرَجَة",     "دحرج", None,  "MASDAR Q-I dahrajah"),
    ("زَلْزَلَة",     "زلزل", None,  "MASDAR Q-I zalzala"),
    ("تَرْجَمَة",     "رجم",  None,  "MASDAR Q-I tarjama"),
    ("بَرْهَنَة",     "برهن", None,  "MASDAR Q-I barhana"),
    # Q-I masdar فِعْلَال
    ("زِلْزَال",      "زلزل", None,  "MASDAR Q-I fi3lal zilzal"),
    ("قِرْطَاس",      "قرطس", None,  "MASDAR Q-I fi3lal qirtas"),
    ("طِرْمَاح",      "طرمح", None,  "MASDAR Q-I fi3lal tirmaah"),
    ("دِرْهَام",      "درهم", None,  "MASDAR Q-I fi3lal dirham"),
    # Q-II masdar تَفَعْلُل
    ("تَدَحْرُج",     "دحرج", None,  "MASDAR Q-II tadahruj"),
    ("تَزَلْزُل",     "زلزل", None,  "MASDAR Q-II tazalzul"),
    ("تَبَرْهُن",     "برهن", "VERB_RESEMBLING_QUAD_II",  "MASDAR Q-II tabarhun"),
    ("تَتَرْجُم",     "ترجم", "VERB_RESEMBLING_QUAD_II",  "MASDAR Q-II tatarjum"),
    # Q-III masdar اِفْعِلْلَال
    ("اِطْمِئْنَان",  "طمءن", None,  "MASDAR Q-III itmi'nan"),
    ("اِقْشِعْرَار",  "اقشعرار", None,  "MASDAR Q-III iqshi3rar"),
    ("اِحْرِنْجَام",  "احرنجام", "VERB_TRILATERAL_UNKNOWN",  "MASDAR Q-III ihrinjam"),
    ("اِسْلِنْقَاء",  "اسلنقاء", "VERB_TRILATERAL_UNKNOWN",  "MASDAR Q-III islinqa'"),
    # Abstract -iyya masdar patterns
    ("فَعَّالِيَّة",  "عيل",  None,  "MASDAR fa3āliyya abstract"),
    ("فَاعِلِيَّة",   "اعلي", None,  "MASDAR fā3iliyya abstract"),
    ("إِنْسَانِيَّة", "ءنس",  "VERB_TRILATERAL_UNKNOWN",  "MASDAR insaniyya abstract"),
    ("وَطَنِيَّة",    "طني",  None,  "MASDAR wataniyya abstract"),
    # كَلَام — fi3al masdar
    ("كَلَام",        "كلم",  None,  "MASDAR kalam fi3al"),
    ("سَلَام",        "سلم",  None,  "MASDAR salam fi3al"),
    ("مَقَام",        "قوم",  "NOM_DERIVED",  "MASDAR maqam fi3al"),
    ("قِيَام",        "قوم",  None,  "MASDAR qiyam fi3al"),

    # ══════════════════════════════════════════════════════════════════════════
    # MASDAR_MARRA — noun of occurrence (فَعْلَة)
    # ══════════════════════════════════════════════════════════════════════════
    ("ضَرْبَة",       "ضرب",  None,  "MASDAR_MARRA darba"),
    ("رَكْضَة",       "ركض",  None,  "MASDAR_MARRA rakda"),
    ("نَظْرَة",       "نظر",  None,  "MASDAR_MARRA nadhra"),
    ("لَمْسَة",       "لمس",  None,  "MASDAR_MARRA lamsa"),
    ("ضَحْكَة",       "ضحك",  None,  "MASDAR_MARRA dahka"),

    # ══════════════════════════════════════════════════════════════════════════
    # MASDAR_HAYAA — noun of manner (فِعْلَة)
    # ══════════════════════════════════════════════════════════════════════════
    ("جِلْسَة",       "جلس",  None,  "MASDAR_HAYAA jilsa"),
    ("رِكْبَة",       "ركب",  None,  "MASDAR_HAYAA rikba"),
    ("مِشْيَة",       "مشي",  None,  "MASDAR_HAYAA mishya"),
    ("ضِحْكَة",       "ضحك",  None,  "MASDAR_HAYAA dihka"),
    ("نِظْرَة",       "نظر",  None,  "MASDAR_HAYAA nidhra"),

    # ══════════════════════════════════════════════════════════════════════════
    # MASDAR_MIMI — مَفْعَل / مَفْعِل / مَفْعَلَة
    # ══════════════════════════════════════════════════════════════════════════
    ("مَذْهَب",       "ذهب",  None,  "MASDAR_MIMI madhhab"),
    ("مَرْجِع",       "رجع",  None,  "MASDAR_MIMI marji3"),
    ("مَكْتَبَة",     "كتب",  "NOM_DERIVED",  "MASDAR_MIMI maktaba"),
    ("مَسِير",        "سير",  None,  "MASDAR_MIMI masir"),

    # ══════════════════════════════════════════════════════════════════════════
    # MASDAR_WEAK — weak verb masdars
    # ══════════════════════════════════════════════════════════════════════════
    ("رَمْي",         "رمي",  None,  "MASDAR_WEAK ramy"),
    ("سَعْي",         "سعي",  None,  "MASDAR_WEAK sa3y"),
    ("هَدًى",         "هدي",  None,  "MASDAR_WEAK hadan"),
    ("رِضًى",         "رضى",  None,  "MASDAR_WEAK ridan"),
    ("بُكَاء",        "بكي",  None,  "MASDAR_WEAK buka'"),
    ("وِقَاية",       "وقي",  None,  "MASDAR_WEAK wiqaya"),
    ("دَعْوَة",       "دعو",  None,  "MASDAR_WEAK da3wa"),
    ("نُمُوّ",        "نمو",  None,  "MASDAR_WEAK numuww"),
    ("غُلُوّ",        "غلو",  None,  "MASDAR_WEAK ghuluww"),
    ("قَوْل",         "قول",  None,  "MASDAR_WEAK qawl"),
    ("سَيْر",         "سير",  None,  "MASDAR_WEAK sayr"),
    ("دَوَار",        "دور",  None,  "MASDAR_WEAK dawar"),
    ("قِوَام",        "قوم",  None,  "MASDAR_WEAK qiwam"),
    ("مَقَالَة",      "قول",  None,  "MASDAR_WEAK maqala"),
    ("إِعْطَاء",      "عطو",  None,  "MASDAR_WEAK i3ta'"),
    ("اِنْقِيَاد",    "قود",  None,  "MASDAR_WEAK inqiyad"),
    ("اِخْتِيَار",    "خير",  None,  "MASDAR_WEAK ikhtiyar"),
    ("اِسْتِدْعَاء",  "دعو",  None,  "MASDAR_WEAK istid3a'"),
    ("مُمَادَّة",     "مدد",  None,  "MASDAR_WEAK mumadda"),
    ("اِسْتِمْرَار",  "مرر",  None,  "MASDAR_WEAK istimrar"),

    # ══════════════════════════════════════════════════════════════════════════
    # ACTIVE_PARTICIPLE — Forms I–XII + Q-I, Q-II
    # ══════════════════════════════════════════════════════════════════════════
    # Form I فَاعِل
    ("كَاتِب",        "كتب",  None,  "AP Form I katib"),
    ("ذَاهِب",        "ذهب",  None,  "AP Form I dhahib"),
    ("ضَارِب",        "ضرب",  None,  "AP Form I darib"),
    ("جَالِس",        "جلس",  None,  "AP Form I jalis"),
    ("عَالِم",        "علم",  None,  "AP Form I 3alim"),
    # Form II مُفَعِّل
    ("مُعَلِّم",      "علم",  "NOM_DERIVED",  "AP Form II mu3allim"),
    ("مُدَرِّس",      "درس",  "NOM_DERIVED",  "AP Form II mudarris"),
    ("مُكَسِّر",      "كسر",  "NOM_DERIVED",  "AP Form II mukassir"),
    ("مُرَتِّب",      "رتب",  "NOM_DERIVED",  "AP Form II murattib"),
    ("مُحَسِّن",      "حسن",  "NOM_DERIVED",  "AP Form II muhassim"),
    # Form III مُفَاعِل
    ("مُكَاتِب",      "كتب",  "NOM_DERIVED",  "AP Form III mukatib"),
    ("مُقَاتِل",      "قتل",  "NOM_DERIVED",  "AP Form III muqatil"),
    ("مُشَارِك",      "شرك",  "NOM_DERIVED",  "AP Form III musharik"),
    ("مُرَاجِع",      "رجع",  "NOM_DERIVED",  "AP Form III muraji3"),
    ("مُنَاقِش",      "اقش",  "NOM_DERIVED",  "AP Form III munaqish"),
    # Form IV مُفْعِل
    ("مُخْرِج",       "خرج",  "NOM_DERIVED",  "AP Form IV mukhrij"),
    ("مُنْجِز",       "نجز",  "NOM_DERIVED",  "AP Form IV munjiz"),
    ("مُبْلِغ",       "بلغ",  "NOM_DERIVED",  "AP Form IV mubligh"),
    ("مُحْضِر",       "حضر",  "NOM_DERIVED",  "AP Form IV muhdir"),
    ("مُسْلِم",       "سلم",  "NOM_DERIVED",  "AP Form IV muslim"),
    # Form V مُتَفَعِّل
    ("مُتَعَلِّم",    "علم",  "NOM_DERIVED",  "AP Form V muta3allim"),
    ("مُتَدَرِّب",    "درب",  "NOM_DERIVED",  "AP Form V mutadarrib"),
    ("مُتَكَسِّر",    "كسر",  "NOM_DERIVED",  "AP Form V mutakassir"),
    ("مُتَطَوِّر",    "طير",  "NOM_DERIVED",  "AP Form V mutatawwir"),
    ("مُتَحَسِّن",    "حسن",  "NOM_DERIVED",  "AP Form V mutahassim"),
    # Form VI مُتَفَاعِل
    ("مُتَفَاهِم",    "فهم",  "NOM_DERIVED",  "AP Form VI mutafahim"),
    ("مُتَبَادِل",    "بدل",  "NOM_DERIVED",  "AP Form VI mutabadil"),
    ("مُتَعَاوِن",    "عنن",  "NOM_DERIVED",  "AP Form VI muta3awim"),
    ("مُتَجَادِل",    "جدل",  "NOM_DERIVED",  "AP Form VI mutajadil"),
    ("مُتَرَاسِل",    "رسل",  "NOM_DERIVED",  "AP Form VI mutarasil"),
    # Form VII مُنْفَعِل
    ("مُنْكَسِر",     "كسر",  "NOM_DERIVED",  "AP Form VII munkasir"),
    ("مُنْفَجِر",     "فجر",  "NOM_DERIVED",  "AP Form VII munfajir"),
    ("مُنْسَحِب",     "سحب",  "NOM_DERIVED",  "AP Form VII munsahib"),
    ("مُنْقَطِع",     "قطع",  "NOM_DERIVED",  "AP Form VII munqati3"),
    ("مُنْهَزِم",     "هزم",  "NOM_DERIVED",  "AP Form VII munhazim"),
    # Form VIII مُفْتَعِل
    ("مُكْتَسِب",     "كسب",  "NOM_DERIVED",  "AP Form VIII muktasib"),
    ("مُعْتَقِد",     "عقد",  "NOM_DERIVED",  "AP Form VIII mu3taqid"),
    ("مُنْتَخِب",     "خبو",  "NOM_DERIVED",  "AP Form VIII muntakhib"),
    ("مُحْتَرِم",     "حرم",  "NOM_DERIVED",  "AP Form VIII muhtarim"),
    ("مُجْتَمِع",     "جمع",  "NOM_DERIVED",  "AP Form VIII mujtami3"),
    # Form IX مُفْعَلّ
    ("مُحْمَرّ",      "حمر",  "NOM_DERIVED",  "AP Form IX muhmarr"),
    ("مُسْوَدّ",      "سدد",  "NOM_DERIVED",  "AP Form IX muswad"),
    # Form X مُسْتَفْعِل
    ("مُسْتَخْدِم",   "خدم",  "NOM_DERIVED_X",  "AP Form X mustakhdim"),
    ("مُسْتَقْبِل",   "قبل",  "NOM_DERIVED_X",  "AP Form X mustaqbil"),
    ("مُسْتَعْمِل",   "عمل",  "NOM_DERIVED_X",  "AP Form X musta3mil"),
    ("مُسْتَغْفِر",   "غفر",  "NOM_DERIVED_X",  "AP Form X mustaghfir"),
    ("مُسْتَقِرّ",    "قرر",  "NOM_DERIVED_X",  "AP Form X mustaqirr"),
    # Form XI مُفْعَالّ
    ("مُحْمَارّ",     "حمر",  "NOM_DERIVED",  "AP Form XI muhmarr intensive"),
    ("مُبْيَاضّ",     "بضض",  "NOM_DERIVED",  "AP Form XI mubyadd"),
    ("مُخْضَارّ",     "خضر",  "NOM_DERIVED",  "AP Form XI mukhdarr"),
    ("مُزْرَاقّ",     "زرق",  "NOM_DERIVED",  "AP Form XI muzraqq"),
    ("مُصْفَارّ",     "صفر",  "NOM_DERIVED",  "AP Form XI musfar"),
    # Form XII مُفْعَوْعِل
    ("مُخْشَوْشِن",   "خشن",  "NOM_DERIVED",  "AP Form XII mukhshawshin"),
    ("مُعْشَوْشِب",   "عشب",  "NOM_DERIVED",  "AP Form XII mu3shawshib"),
    ("مُغْدَوْدِن",   "غدن",  "NOM_DERIVED",  "AP Form XII mughdawdin"),
    ("مُحْلَوْلِي",   "حلل",  "NOM_DERIVED",  "AP Form XII muhlawli"),
    ("مُعْوَجِّج",    "عجج",  "NOM_DERIVED",  "AP Form XII mu3wajjij"),
    # Q-I مُفَعْلِل
    ("مُدَحْرِج",     "دحرج", "NOM_DERIVED",  "AP Q-I mudahrij"),
    ("مُزَلْزِل",     "زلزل", "NOM_DERIVED",  "AP Q-I muzalzil"),
    ("مُتَرْجِم",     "رجم",  "NOM_DERIVED",  "AP Q-I mutarjim"),
    ("مُبَرْهِن",     "برهن", "NOM_DERIVED",  "AP Q-I mubarhin"),
    ("مُقَرْطِس",     "قرطس", "NOM_DERIVED",  "AP Q-I muqartis"),
    # Q-II مُتَفَعْلِل
    ("مُتَدَحْرِج",   "دحرج","NOM_DERIVED",  "AP Q-II mutadahrij"),
    ("مُتَزَلْزِل",   "زلزل","NOM_DERIVED",  "AP Q-II mutazalzil"),
    ("مُتَتَرْجِم",   "ترجم","NOM_DERIVED",  "AP Q-II mutatarjim"),
    ("مُتَبَرْهِن",   "برهن",  "NOM_DERIVED",  "AP Q-II mutabarhin"),
    ("مُتَقَرْطِس",   "قرطس",  "NOM_DERIVED",  "AP Q-II mutaqartis"),

    # ══════════════════════════════════════════════════════════════════════════
    # PASSIVE_PARTICIPLE — Forms I–X + Q-I, Q-II
    # ══════════════════════════════════════════════════════════════════════════
    # Form I مَفْعُول
    ("مَكْتُوب",      "كتب",  "NOM_DERIVED",  "PP Form I maktub"),
    ("مَضْرُوب",      "ضرب",  "NOM_DERIVED",  "PP Form I madrub"),
    ("مَفْهُوم",      "فهم",  "NOM_DERIVED",  "PP Form I mafhum"),
    ("مَسْمُوع",      "سمع",  "NOM_DERIVED",  "PP Form I masmu3"),
    ("مَطْبُوخ",      "طبخ",  "NOM_DERIVED",  "PP Form I matbukh"),
    # Form II مُفَعَّل
    ("مُعَلَّم",      "علم",  "NOM_DERIVED",  "PP Form II mu3allam"),
    ("مُدَرَّس",      "درس",  "NOM_DERIVED",  "PP Form II mudarras"),
    ("مُكَسَّر",      "كسر",  "NOM_DERIVED",  "PP Form II mukassar"),
    ("مُرَتَّب",      "رتب",  "NOM_DERIVED",  "PP Form II murattab"),
    ("مُحَسَّن",      "حسن",  "NOM_DERIVED",  "PP Form II muhassam"),
    # Form III مُفَاعَل
    ("مُكَاتَب",      "كتب",  "NOM_DERIVED",  "PP Form III mukatab"),
    ("مُقَاتَل",      "قتل",  "NOM_DERIVED",  "PP Form III muqatal"),
    ("مُشَارَك",      "شرك",  "NOM_DERIVED",  "PP Form III musharak"),
    ("مُرَاجَع",      "رجع",  "NOM_DERIVED",  "PP Form III muraja3"),
    ("مُسَاعَد",      "سعد",  "NOM_DERIVED",  "PP Form III musa3ad"),
    # Form IV مُفْعَل
    ("مُخْرَج",       "خرج",  "NOM_DERIVED",  "PP Form IV mukhraj"),
    ("مُنْجَز",       "نجز",  "NOM_DERIVED",  "PP Form IV munjaz"),
    ("مُبْلَغ",       "بلغ",  "NOM_DERIVED",  "PP Form IV mublagh"),
    ("مُحْضَر",       "حضر",  "NOM_DERIVED",  "PP Form IV muhdar"),
    ("مُسْلَم",       "سلم",  "NOM_DERIVED",  "PP Form IV muslam"),
    # Form V مُتَفَعَّل
    ("مُتَعَلَّم",    "علم",  "NOM_DERIVED",  "PP Form V muta3allam"),
    ("مُتَدَرَّب",    "درب",  "NOM_DERIVED",  "PP Form V mutadarrab"),
    ("مُتَكَسَّر",    "كسر",  "NOM_DERIVED",  "PP Form V mutakassar"),
    ("مُتَطَوَّر",    "طير",  "NOM_DERIVED",  "PP Form V mutatawwar"),
    ("مُتَحَسَّن",    "حسن",  "NOM_DERIVED",  "PP Form V mutahassan"),
    # Form VI مُتَفَاعَل
    ("مُتَفَاهَم",    "فهم",  "NOM_DERIVED",  "PP Form VI mutafaham"),
    ("مُتَبَادَل",    "بدل",  "NOM_DERIVED",  "PP Form VI mutabadal"),
    ("مُتَعَاوَن",    "عنن",  "NOM_DERIVED",  "PP Form VI muta3awan"),
    ("مُتَجَادَل",    "جدل",  "NOM_DERIVED",  "PP Form VI mutajadal"),
    ("مُتَرَاسَل",    "رسل",  "NOM_DERIVED",  "PP Form VI mutarasal"),
    # Form VII مُنْفَعَل
    ("مُنْكَسَر",     "كسر",  "NOM_DERIVED",  "PP Form VII munkasir"),
    ("مُنْفَجَر",     "فجر",  "NOM_DERIVED",  "PP Form VII munfajar"),
    ("مُنْسَحَب",     "سحب",  "NOM_DERIVED",  "PP Form VII munsahab"),
    ("مُنْقَطَع",     "قطع",  "NOM_DERIVED",  "PP Form VII munqata3"),
    ("مُنْهَزَم",     "هزم",  "NOM_DERIVED",  "PP Form VII munhazam"),
    # Form VIII مُفْتَعَل
    ("مُكْتَسَب",     "كسب",  "NOM_DERIVED",  "PP Form VIII muktasab"),
    ("مُعْتَقَد",     "عقد",  "NOM_DERIVED",  "PP Form VIII mu3taqad"),
    ("مُنْتَخَب",     "خبو",  "NOM_DERIVED",  "PP Form VIII muntakhab"),
    ("مُحْتَرَم",     "حرم",  "NOM_DERIVED",  "PP Form VIII muhtaram"),
    ("مُجْتَمَع",     "جمع",  "NOM_DERIVED",  "PP Form VIII mujtama3"),
    # Form X مُسْتَفْعَل
    ("مُسْتَخْدَم",   "خدم",  "NOM_DERIVED_X",  "PP Form X mustakhdim"),
    ("مُسْتَعْمَل",   "عمل",  "NOM_DERIVED_X",  "PP Form X musta3mal"),
    ("مُسْتَقْبَل",   "قبل",  "NOM_DERIVED_X",  "PP Form X mustaqbal"),
    ("مُسْتَغْفَر",   "غفر",  "NOM_DERIVED_X",  "PP Form X mustaghfar"),
    ("مُسْتَعَدّ",    "عود",  "NOM_DERIVED_X",  "PP Form X musta3add"),
    # Q-I مُفَعْلَل
    ("مُدَحْرَج",     "دحرج", "NOM_DERIVED",  "PP Q-I mudahraj"),
    ("مُزَلْزَل",     "زلزل", "NOM_DERIVED",  "PP Q-I muzalzal"),
    ("مُتَرْجَم",     "رجم",  "NOM_DERIVED",  "PP Q-I mutarjam"),
    ("مُبَرْهَن",     "برهن", "NOM_DERIVED",  "PP Q-I mubarhan"),
    ("مُقَرْطَس",     "قرطس", "NOM_DERIVED",  "PP Q-I muqartas"),
    # Q-II مُتَفَعْلَل
    ("مُتَدَحْرَج",   "دحرج","NOM_DERIVED",  "PP Q-II mutadahraj"),
    ("مُتَزَلْزَل",   "زلزل","NOM_DERIVED",  "PP Q-II mutazalzal"),
    ("مُتَتَرْجَم",   "ترجم","NOM_DERIVED",  "PP Q-II mutatarjam"),
    ("مُتَبَرْهَن",   "برهن",  "NOM_DERIVED",  "PP Q-II mutabarhan"),
    ("مُتَقَرْطَس",   "قرطس",  "NOM_DERIVED",  "PP Q-II mutaqartas"),

    # ══════════════════════════════════════════════════════════════════════════
    # ACTIVE_PARTICIPLE_WEAK — naqis active participles
    # ══════════════════════════════════════════════════════════════════════════
    ("مُقْتَضٍ",      "قضي",  "NOM_DERIVED",  "AP_WEAK Form VIII muqtadin"),
    ("مُتَمَنٍّ",     "تمن",  "NOM_DERIVED",  "AP_WEAK Form V mutamannin"),
    ("مُسْتَدْعٍ",    "دعو",  "NOM_DERIVED_X",  "AP_WEAK Form X mustada3in"),
    ("مُزَكٍّ",       "زكك",  "NOM_DERIVED",  "AP_WEAK Form II muzakkin"),
    ("مُرَاعٍ",       "رعع",  "NOM_DERIVED",  "AP_WEAK Form III mura3in"),
    ("مُعْطٍ",        "عطط",  "NOM_DERIVED",  "AP_WEAK Form IV mu3tin"),
    ("مُنْقَضٍ",      "قضي",  "NOM_DERIVED",  "AP_WEAK Form VII munqadin"),
    ("مُتَدَاعٍ",     "دعو",  "NOM_DERIVED",  "AP_WEAK Form VI mutada3in"),

    # ══════════════════════════════════════════════════════════════════════════
    # PASSIVE_PARTICIPLE_WEAK — naqis passive participles
    # ══════════════════════════════════════════════════════════════════════════
    ("مُقْتَضًى",     "قضي",  "NOM_DERIVED",  "PP_WEAK Form VIII muqtadan"),
    ("مُتَمَنًّى",    "منى",  "NOM_DERIVED",  "PP_WEAK Form V mutamannan"),
    ("مُسْتَدْعًى",   "دعو",  "NOM_DERIVED_X",  "PP_WEAK Form X mustada3an"),
    ("مُزَكًّى",      "زكى",  "NOM_DERIVED",  "PP_WEAK Form II muzakkan"),
    ("مُرَاعًى",      "ريع",  "NOM_DERIVED",  "PP_WEAK Form III mura3an"),
    ("مُعْطًى",       "عطو",  "NOM_DERIVED",  "PP_WEAK Form IV mu3tan"),

    # ══════════════════════════════════════════════════════════════════════════
    # ADJECTIVE — فَعِيل، فَعْلَان، فَعُول، فَعَّال، مِفْعَال، فَعِيلَة
    # ══════════════════════════════════════════════════════════════════════════
    ("كَرِيم",        "كرم",  None,  "ADJ fa3il karim"),
    ("رَحِيم",        "رحم",  None,  "ADJ fa3il rahim"),
    ("فَرِح",         "فرح",  None,  "ADJ fa3il farih"),
    ("حَذِر",         "حذر",  None,  "ADJ fa3il hadhir"),
    ("عَطْشَان",      "عطش",  None,  "ADJ fa3lan 3atshan"),
    ("غَضْبَان",      "غضب",  None,  "ADJ fa3lan ghadban"),
    ("صَبُور",        "صبر",  None,  "ADJ fa3ul sabur"),
    ("شَكُور",        "شكر",  None,  "ADJ fa3ul shakur"),
    ("عَلَّام",       "علم",  None,  "ADJ fa3al 3allam"),
    ("كَذَّاب",       "كذب",  None,  "ADJ fa3al kadhdhab"),
    ("مِقْوَال",      "قول",  None,  "ADJ mif3al miqwal"),
    ("كَرِيمَة",      "كرم",  None,  "ADJ fa3ila karima fem"),

    # ══════════════════════════════════════════════════════════════════════════
    # ADJECTIVE_COLOR_DEFECT — أَفْعَل pattern
    # ══════════════════════════════════════════════════════════════════════════
    ("أَحْمَر",       "حمر",  None,  "ADJ_COLOR ahmar"),
    ("أَخْضَر",       "خضر",  None,  "ADJ_COLOR akhdar"),
    ("أَزْرَق",       "زرق",  None,  "ADJ_COLOR azraq"),
    ("أَصْفَر",       "صفر",  None,  "ADJ_COLOR asfar"),
    ("أَبْيَض",       "بيض",  None,  "ADJ_COLOR abyad"),

    # ══════════════════════════════════════════════════════════════════════════
    # ADJECTIVE_ELATIVE — أَفْعَل comparative
    # ══════════════════════════════════════════════════════════════════════════
    ("أَكْبَر",       "كبر",  None,  "ADJ_ELATIVE akbar"),
    ("أَصْغَر",       "صغر",  None,  "ADJ_ELATIVE asghar"),
    ("أَحْسَن",       "حسن",  None,  "ADJ_ELATIVE ahsan"),
    ("أَكْثَر",       "كثر",  None,  "ADJ_ELATIVE akthar"),
    ("أَجْمَل",       "جمل",  None,  "ADJ_ELATIVE ajmal"),

    # ══════════════════════════════════════════════════════════════════════════
    # ADJECTIVE_DIPTOTE — فَعْلَاء، فَعْلَى، فُعْلَى
    # ══════════════════════════════════════════════════════════════════════════
    ("حَمْرَاء",      "حمر",  None,  "ADJ_DIPTOTE hamra'"),
    ("عَطْشَى",       "عطش",  None,  "ADJ_DIPTOTE 3atsha"),
    ("كُبْرَى",       "كبر",  None,  "ADJ_DIPTOTE kubra"),
    ("صُغْرَى",       "صغر",  None,  "ADJ_DIPTOTE sughra"),

    # ══════════════════════════════════════════════════════════════════════════
    # RELATIVE_ADJECTIVE (نسبة) — ـيّ suffix
    # ══════════════════════════════════════════════════════════════════════════
    ("عَرَبِيّ",      "عرب",  None,  "NISBA 3arabi"),
    ("مِصْرِيّ",      "مصر",  None,  "NISBA misri"),
    ("عَرَاقِيّ",     "عرق",  None,  "NISBA 3iraqi"),
    ("دُوَلِيّ",      "دول",  None,  "NISBA dawali"),

    # ══════════════════════════════════════════════════════════════════════════
    # INSTRUMENT_NOUN — مِفْعَل، مِفْعَلَة، مِفْعَال، فَعَّالَة، فَاعُول
    # ══════════════════════════════════════════════════════════════════════════
    ("مِبْرَد",       "برد",  "NOM_DERIVED",  "INSTR mibrad"),
    ("مِكْنَسَة",     "كنس",  "NOM_DERIVED",  "INSTR miknasa"),
    ("مِفْتَاح",      "فتح",  "NOM_DERIVED",  "INSTR miftah"),
    ("غَسَّالَة",     "غسل",  None,  "INSTR ghassala"),
    ("قَاطُوع",       "قطع",  None,  "INSTR qatu3"),

    # ══════════════════════════════════════════════════════════════════════════
    # PLACE_TIME_NOUN — مَفْعَل، مَفْعِل، مَفْعَلَة
    # ══════════════════════════════════════════════════════════════════════════
    ("مَلْعَب",       "لعب",  "NOM_DERIVED",  "PLACE mal3ab"),
    ("مَجْلِس",       "جلس",  "NOM_DERIVED",  "PLACE majlis"),
    ("مَكْتَبَة",     "كتب",  "NOM_DERIVED",  "PLACE maktaba"),
    ("مَدَحْرَج",     "دحرج", "NOM_DERIVED",  "PLACE madahraj quad"),
    ("مَرْمِيَة",     "رمي",  "NOM_DERIVED",  "PLACE marmiya naqis"),

    # ══════════════════════════════════════════════════════════════════════════
    # DIMINUTIVE — فُعَيْل، فُعَيِّل، فُعَيْعِل، مُفَيْعِيل
    # ══════════════════════════════════════════════════════════════════════════
    ("كُلَيْب",       "كلب",  None,  "DIM kulayb"),
    ("كُتَيِّب",      "كتب",  None,  "DIM kutayyib"),
    ("دُرَيْهِم",     "درهم", None,  "DIM durayhim"),
    ("مُفَيْتِيح",    "فتح",  None,  "DIM mufaytih"),

    # ══════════════════════════════════════════════════════════════════════════
    # COLLECTIVE_NOUN
    # ══════════════════════════════════════════════════════════════════════════
    ("شَجَر",         "شجر",  None,  "COLL shajar"),
    ("تَمْر",         "تمر",  None,  "COLL tamr"),
    ("حِجَارَة",      "حجر",  None,  "COLL hijara"),
    ("وَرَق",         "ورق",  None,  "COLL waraq"),
    ("نَخْل",         "نخل",  None,  "COLL nakhl"),

    # ══════════════════════════════════════════════════════════════════════════
    # UNIT_NOUN — فَعَلَة
    # ══════════════════════════════════════════════════════════════════════════
    ("شَجَرَة",       "شجر",  None,  "UNIT shajara"),
    ("تَمْرَة",       "تمر",  None,  "UNIT tamra"),
    ("وَرَقَة",       "ورق",  None,  "UNIT waraqa"),
    ("نَخْلَة",       "نخل",  None,  "UNIT nakhla"),
    ("قَمْحَة",       "قمح",  None,  "UNIT qamha"),

    # ══════════════════════════════════════════════════════════════════════════
    # NOUN_OF_OCCURRENCE — فَعْلَة
    # ══════════════════════════════════════════════════════════════════════════
    ("ضَرْبَة",       "ضرب",  None,  "NOUN_OCC darba"),
    ("رَكْضَة",       "ركض",  None,  "NOUN_OCC rakda"),
    ("ضَحْكَة",       "ضحك",  None,  "NOUN_OCC dahka"),
    ("نَظْرَة",       "نظر",  None,  "NOUN_OCC nadhra"),
    ("لَمْسَة",       "لمس",  None,  "NOUN_OCC lamsa"),

    # ══════════════════════════════════════════════════════════════════════════
    # NOUN_OF_MANNER — فِعْلَة
    # ══════════════════════════════════════════════════════════════════════════
    ("جِلْسَة",       "جلس",  None,  "NOUN_MANNER jilsa"),
    ("رِكْبَة",       "ركب",  None,  "NOUN_MANNER rikba"),
    ("مِشْيَة",       "مشي",  None,  "NOUN_MANNER mishya"),
    ("ضِحْكَة",       "ضحك",  None,  "NOUN_MANNER dihka"),
    ("نِظْرَة",       "نظر",  None,  "NOUN_MANNER nidhra"),

    # ══════════════════════════════════════════════════════════════════════════
    # NOUN_DIPTOTE — فَتْوَى، صَحْرَاء
    # ══════════════════════════════════════════════════════════════════════════
    ("فَتْوَى",       "توو",  None,  "NOUN_DIPTOTE fatwa"),
    ("صَحْرَاء",      "صحر",  None,  "NOUN_DIPTOTE sahra'"),
    ("بَيْضَاء",      "بيض",  None,  "NOUN_DIPTOTE bayda'"),
    ("حَمْرَاء",      "حمر",  None,  "NOUN_DIPTOTE hamra'"),
    ("خَضْرَاء",      "خضر",  None,  "NOUN_DIPTOTE khadra'"),

    # ══════════════════════════════════════════════════════════════════════════
    # FROZEN_NOUN — irregular/frozen forms
    # ══════════════════════════════════════════════════════════════════════════
    ("عُنُق",         "عنق",  None,  "FROZEN 3unuq"),
    ("صُوَر",         "صور",  None,  "FROZEN suwar"),
    ("قُفْل",         "قفل",  None,  "FROZEN qufl"),
    ("جَمَل",         "جمل",  None,  "FROZEN jamal"),
    ("كَتِف",         "كتف",  None,  "FROZEN katif"),
    ("بَيْت",         "بيت",  None,  "FROZEN bayt"),
    ("إِبِل",         "ءبل",  None,  "FROZEN ibil"),
    ("قِطَع",         "قطع",  None,  "FROZEN qita3"),
    ("جَعْفَر",       "جعفر", None,  "FROZEN ja3far"),
    ("سَفَرْجَل",     "رجل",  None,  "FROZEN safarjal"),
    ("عَنْدَلِيب",    "عندل", None,  "FROZEN 3andalib"),
    ("سُكَارَى",      "سكر",  None,  "FROZEN sukara"),

    # ══════════════════════════════════════════════════════════════════════════
    # SOUND_PLURAL_MASC — ـون / ـين
    # ══════════════════════════════════════════════════════════════════════════
    ("كَاتِبُون",     "كتب",  None,  "SPM katibun"),
    ("مُعَلِّمُون",   "علم",  "NOM_DERIVED",  "SPM mu3allimun"),
    ("مُدَرِّسُون",   "درس",  "NOM_DERIVED",  "SPM mudarrisun"),
    ("مُهَنْدِسُون",  "هند",  "NOM_DERIVED",  "SPM muhandisun"),
    ("مُسْلِمُون",    "سلم",  "NOM_DERIVED",  "SPM muslimun"),

    # ══════════════════════════════════════════════════════════════════════════
    # SOUND_PLURAL_FEM — ـات
    # ══════════════════════════════════════════════════════════════════════════
    ("كَاتِبَات",     "كتب",  None,  "SPF katibat"),
    ("مُعَلِّمَات",   "علم",  "NOM_DERIVED",  "SPF mu3allimat"),
    ("غَسَّالَات",    "غسل",  None,  "SPF ghassalat"),

    # ══════════════════════════════════════════════════════════════════════════
    # DUAL — ـان / ـتان
    # ══════════════════════════════════════════════════════════════════════════
    ("كِتَابَان",     "كتب",  None,  "DUAL kitaban"),
    ("كِتَابَتَان",   "كتب",  None,  "DUAL kitabatan"),
    ("طَالِبَان",     "طلب",  "VERB_TRILATERAL_BARE",  "DUAL taliban"),
    ("مُعَلِّمَان",   "علم",  "NOM_DERIVED",  "DUAL mu3alliman"),
    ("بَيْتَان",      "بيت",  "VERB_TRILATERAL_BARE",  "DUAL baytan"),

    # ══════════════════════════════════════════════════════════════════════════
    # BROKEN_PLURAL — 41 patterns
    # ══════════════════════════════════════════════════════════════════════════
    ("رُكَّع",        "ركع",  None,  "BP rukka3"),
    ("كُتَّاب",       "كتب",  None,  "BP kuttab"),
    ("كَتَبَة",       "كتب",  None,  "BP kataba"),
    ("قُضَاة",        "قضي",  None,  "BP qudat naqis"),
    ("كُتُب",         "كتب",  None,  "BP kutub"),
    ("حُمْر",         "حمر",  None,  "BP humr"),
    ("رُكَب",         "ركب",  None,  "BP rukab"),
    ("قِطَع",         "قطع",  None,  "BP qita3"),
    ("دِبَبَة",       "دبب",  None,  "BP dibaba geminate"),
    ("إِخْوَة",       "ءخو",  None,  "BP ikhwa naqis"),
    ("جِبَال",        "جبل",  None,  "BP jibal"),
    ("رِجَال",        "رجل",  None,  "BP rijal"),
    ("قُلُوب",        "قلب",  None,  "BP qulub"),
    ("بُيُوت",        "بيت",  None,  "BP buyut"),
    ("أَرْجُل",       "رجل",  None,  "BP arjul"),
    ("أَقْوَال",      "قول",  None,  "BP aqwal"),
    ("أَقْلَام",      "قلم",  None,  "BP aqlam"),
    ("أَسْلِحَة",     "سلح",  None,  "BP asliha"),
    ("غِلْمَان",      "غلم",  None,  "BP ghilman"),
    ("بُلْدَان",      "بلد",  None,  "BP buldan"),
    ("عَبِيد",        "عبد",  None,  "BP 3abid"),
    ("بُعُولَة",      "بعل",  None,  "BP bu3ula"),
    ("حِجَارَة",      "حجر",  None,  "BP hijara"),
    ("حَلَق",         "حلق",  None,  "BP halaq"),
    ("صَحْب",         "صحب",  None,  "BP sahb"),
    ("عَوَامِل",      "عوم",  None,  "BP 3awamil"),
    ("رَسَائِل",      "رسو",  None,  "BP rasa'il"),
    ("دَرَاهِم",      "درهم", None,  "BP darahim"),
    ("مَجَالِس",      "جلس",  None,  "BP majalis"),
    ("عَصَافِير",     "عصف",  None,  "BP 3asafir"),
    ("مَكَاتِيب",     "كتب",  None,  "BP makatib"),
    ("كُرَمَاء",      "كرم",  None,  "BP kurama'"),
    ("أَنْبِيَاء",    "نبء",  None,  "BP anbiya'"),
    ("مَرْضَى",       "رضى",  None,  "BP marda"),
    ("يَتَامَى",      "تيم",  None,  "BP yatama"),
    ("لَيَالٍ",       "ليل",  None,  "BP layalin"),
    ("عُيُون",        "عين",  None,  "BP 3uyun"),

    # ══════════════════════════════════════════════════════════════════════════
    # BROKEN_PLURAL_RARE
    # ══════════════════════════════════════════════════════════════════════════
    ("عُلَمَاء",      "علم",  None,  "BP_RARE 3ulama'"),
    ("حُبَلَى",       "حبل",  None,  "BP_RARE hubala"),
    ("قَوَاعِد",      "قوع",  None,  "BP_RARE qawa3id"),
    ("عُقُولَات",     "عقل",  None,  "BP_RARE 3uqulat"),
    ("رِسَالَات",     "رسل",  None,  "BP_RARE risalat"),
    ("حُكَّمَاء",     "حكم",  None,  "BP_RARE hukkama'"),
    ("أَنْفُس",       "نفس",  None,  "BP_RARE anfus"),
    ("كِرَام",        "كرم",  None,  "BP_RARE kiram"),
    ("أُمَنَاء",      "منء",  None,  "BP_RARE umana'"),
    ("عَبَاقِرَة",    "عبقر", None,  "BP_RARE 3abaqira"),
    ("غُرَف",         "غرف",  None,  "BP_RARE ghuraf"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_WEAK_MITHAL — initial waw/ya
    # ══════════════════════════════════════════════════════════════════════════
    ("وَعَدَ",        "وعد",  None,  "MITHAL wa3ada"),
    ("يَسَرَ",        "يسر",  None,  "MITHAL yasara initial ya"),
    ("وَجَدَ",        "وجد",  None,  "MITHAL wajada"),
    ("وَضَعَ",        "وضع",  None,  "MITHAL wada3a"),
    ("وَجِلَ",        "وجل",  None,  "MITHAL wajila"),
    ("وَرِثَ",        "ورث",  None,  "MITHAL waritha"),
    ("يَبِسَ",        "يبس",  None,  "MITHAL yabisa initial ya"),
    ("وَزَنَ",        "وزن",  None,  "MITHAL wazana"),
    ("وَصَلَ",        "وصل",  None,  "MITHAL wasala"),
    ("وَقَفَ",        "وقف",  None,  "MITHAL waqafa"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_WEAK_AJWAF_WAW — hollow waw
    # ══════════════════════════════════════════════════════════════════════════
    ("قَالَ",         "قول",  None,  "AJWAF_WAW qala"),
    ("خَافَ",         "خوف",  None,  "AJWAF_WAW khafa"),
    ("نَامَ",         "نوم",  None,  "AJWAF_WAW nama"),
    ("زَادَ",         "زيد",  None,  "AJWAF_WAW zada"),
    ("عَادَ",         "عود",  None,  "AJWAF_WAW 3ada"),
    ("كَانَ",         "كون",  None,  "AJWAF_WAW kana"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_WEAK_AJWAF_YA — hollow ya
    # ══════════════════════════════════════════════════════════════════════════
    ("سَارَ",         "سير",  None,  "AJWAF_YA sara"),
    ("بَاعَ",         "بيع",  None,  "AJWAF_YA ba3a"),
    ("طَارَ",         "طير",  None,  "AJWAF_YA tara"),
    ("جَاءَ",         "جيء",  None,  "AJWAF_YA ja'a"),
    ("شَاءَ",         "شيء",  None,  "AJWAF_YA sha'a"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_WEAK_NAQIS_WAW — final waw
    # ══════════════════════════════════════════════════════════════════════════
    ("دَعَا",         "دعو",  None,  "NAQIS_WAW da3a"),
    ("بَنَى",         "بنو",  None,  "NAQIS_WAW bana"),
    ("عَفَا",         "عفو",  None,  "NAQIS_WAW 3afa"),
    ("سَمَا",         "سمو",  None,  "NAQIS_WAW sama"),
    ("نَمَا",         "نمي",  None,  "NAQIS_WAW nama"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_WEAK_NAQIS_YA — final ya
    # ══════════════════════════════════════════════════════════════════════════
    ("رَمَى",         "رمي",  None,  "NAQIS_YA rama"),
    ("نَسِيَ",        "نسي",  None,  "NAQIS_YA nasiya"),
    ("هَدَى",         "هدي",  None,  "NAQIS_YA hada"),
    ("مَشَى",         "مشي",  None,  "NAQIS_YA masha"),
    ("بَكَى",         "بكي",  None,  "NAQIS_YA baka"),
    ("سَعَى",         "سعو",  None,  "NAQIS_YA sa3a"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_WEAK_LAFEEF_MAFRUQ — initial waw + final ya
    # ══════════════════════════════════════════════════════════════════════════
    ("وَفَى",         "وفي",  None,  "LAFEEF_MAFRUQ wafa"),
    ("وَقَى",         "وقي",  None,  "LAFEEF_MAFRUQ waqa"),
    ("وَلِيَ",        "ولي",  None,  "LAFEEF_MAFRUQ waliya"),
    ("وَنَى",         "وني",  None,  "LAFEEF_MAFRUQ wana"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_WEAK_LAFEEF_MAQRUN — middle waw + final ya
    # ══════════════════════════════════════════════════════════════════════════
    ("هَوَى",         "هوي",  None,  "LAFEEF_MAQRUN hawa"),
    ("طَوَى",         "طوي",  None,  "LAFEEF_MAQRUN tawa"),
    ("لَوَى",         "لوو",  None,  "LAFEEF_MAQRUN lawa"),
    ("رَوَى",         "روي",  None,  "LAFEEF_MAQRUN rawa"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_DOUBLED — geminate
    # ══════════════════════════════════════════════════════════════════════════
    ("مَدَّ",          "مدد",  None,  "DOUBLED madda"),
    ("تَمَّ",          "تمم",  None,  "DOUBLED tamma"),
    ("ظَلَّ",          "ظلل",  None,  "DOUBLED dhalla"),
    ("شَدَّ",          "شدد",  None,  "DOUBLED shadda"),
    ("رَدَّ",          "ردد",  None,  "DOUBLED radda"),
    ("حَلَّ",          "حلل",  None,  "DOUBLED halla"),
    ("عَدَّ",          "عدد",  None,  "DOUBLED 3adda"),
    ("قَلَّ",          "قلل",  None,  "DOUBLED qalla"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_HAMZA — initial, medial, final hamza
    # ══════════════════════════════════════════════════════════════════════════
    ("أَكَلَ",         "ءكل",  None,  "HAMZA initial akala"),
    ("سَأَلَ",         "سءل",  None,  "HAMZA medial sa'ala"),
    ("قَرَأَ",         "قرء",  None,  "HAMZA final qara'a"),
    ("أَمَرَ",         "ءمر",  None,  "HAMZA initial amara"),
    ("أَخَذَ",         "ءخذ",  None,  "HAMZA initial akhadha"),
    ("بَدَأَ",         "بدء",  None,  "HAMZA final bada'a"),
    ("لَأَمَ",         "لءم",  None,  "HAMZA medial la'ama"),
    ("رَأَسَ",         "رءس",  None,  "HAMZA medial ra'asa"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_PASSIVE_WEAK
    # ══════════════════════════════════════════════════════════════════════════
    ("قِيلَ",          "قول",  None,  "PASS_WEAK qila ajwaf"),
    ("رُمِيَ",         "رمي",  None,  "PASS_WEAK rumiya naqis"),
    ("دُعِيَ",         "دعو",  None,  "PASS_WEAK du3iya naqis"),
    ("يُقَالُ",        "قول",  None,  "PASS_WEAK yuqalu imperfect"),
    ("يُرْمَى",        "رمي",  None,  "PASS_WEAK yurma imperfect naqis"),

    # ══════════════════════════════════════════════════════════════════════════
    # VERB_DOUBLY_WEAK
    # ══════════════════════════════════════════════════════════════════════════
    ("وَقَى",          "وقي",  None,  "DOUBLY_WEAK waqa mithal+naqis"),
    ("أَتَى",          "ءتو",  None,  "DOUBLY_WEAK ata hamza+naqis"),
    ("جَاءَ",          "جيء",  None,  "DOUBLY_WEAK ja'a"),
    ("رَأَى",          "رءي",  None,  "DOUBLY_WEAK ra'a"),
    ("حَيِيَ",         "حيي",  None,  "DOUBLY_WEAK hayiya"),
]

@pytest.mark.parametrize("surface,exp_root,exp_tmpl,label", CASES)
def test_ar_templates(surface, exp_root, exp_tmpl, label):
    ti = engine.analyze(surface)
    assert ti.root == exp_root, (
        f"[{label}] root: got {ti.root!r}, expected {exp_root!r}"
    )
    if exp_tmpl is not None:
        assert ti.template == exp_tmpl, (
            f"[{label}] template: got {ti.template!r}, expected {exp_tmpl!r}"
        )

if __name__ == "__main__":
    import sys
    passed = failed = 0
    failures = []
    for surface, exp_root, exp_tmpl, label in CASES:
        ti = engine.analyze(surface)
        root_ok = ti.root == exp_root
        tmpl_ok = (exp_tmpl is None) or (ti.template == exp_tmpl)
        if root_ok and tmpl_ok:
            passed += 1
        else:
            failed += 1
            msgs = []
            if not root_ok:
                msgs.append(f"root={ti.root!r} (exp {exp_root!r})")
            if not tmpl_ok:
                msgs.append(f"tmpl={ti.template!r} (exp {exp_tmpl!r})")
            failures.append(f"  FAIL  {surface:<24s}  {label}  →  {' | '.join(msgs)}")
    print(f"\n{'='*72}")
    print(f"  Arabic Engine Template Test Suite")
    print(f"{'='*72}")
    print(f"  {passed} passed,  {failed} failed  (total {passed+failed})")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f)
    else:
        print("\n  All tests passed.")
    print()
    sys.exit(0 if failed == 0 else 1)
