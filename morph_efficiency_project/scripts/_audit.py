import sys; sys.path.insert(0, '.')
from morph_efficiency_project.scripts.preprocess_morph import ArabicEngine
e = ArabicEngine()

cases = [
    # Form VI تَفَاعَلَ
    ('تَبَادَلَ', 'بدل', 'Form VI tabadala'),
    ('تَعَاوَنَ', 'عون', 'Form VI ta3awana ajwaf'),
    ('تَسَاءَلَ', 'سءل', 'Form VI tasa\'ala hamzated'),
    # Form IX اِفْعَلَّ (colour/defect verbs)
    ('اِحْمَرَّ', 'حمر', 'Form IX ihmarra'),
    ('اِسْوَدَّ', 'سود', 'Form IX iswadda'),
    # Doubly-weak: initial و + final ي
    ('وَقَى', 'وقي', 'doubly-weak waqa'),
    ('وَفَى', 'وفي', 'doubly-weak wafa'),
    # Form VIII with root-initial ت assimilation (ت+ت→تّ)
    ('اِتَّصَلَ', 'وصل', 'Form VIII ittasala waw-assim'),
    ('اِتَّخَذَ', 'ءخذ', 'Form VIII ittakhadha hamza-assim'),
    # Form VIII emphatic assimilation (ت→ط/د)
    ('اِطَّلَعَ', 'طلع', 'Form VIII ittala3a emphatic'),
    ('اِضْطَرَّ', 'ضرر', 'Form VIII idtarra emphatic'),
    # Stacked proclitic + Form VIII
    ('وَاتَّصَلَ', 'وصل', 'wa + Form VIII ittasala'),
    # NOM_DERIVED: Form III active participle مُفَاعِل
    ('مُقَاتِل', 'قتل', 'NOM_DERIVED Form III muqatil'),
    # NOM_DERIVED: Form X active participle مُسْتَفْعِل
    ('مُسْتَقْبِل', 'قبل', 'NOM_DERIVED Form X mustaqbil'),
    ('مُسْتَشَار', 'شور', 'NOM_DERIVED Form X mustashar ajwaf'),
    # Broken plural patterns
    ('كُتُب', 'كتب', 'broken plural kutub'),
    ('رِجَال', 'رجل', 'broken plural rijal'),
    ('أَقْلَام', 'قلم', 'broken plural aqlam'),
    ('بُيُوت', 'بيت', 'broken plural buyut'),
    ('عُيُون', 'عين', 'broken plural 3uyun'),
    # Masdar patterns
    ('تَعْلِيم', 'علم', 'masdar ta3lim Form II'),
    ('تَفْسِير', 'فسر', 'masdar tafsir Form II'),
    ('مُشَارَكَة', 'شرك', 'masdar musharaka Form III'),
    ('إِنْجَاز', 'نجز', 'masdar injaz Form IV'),
    ('اِسْتِعْمَال', 'عمل', 'masdar isti3mal Form X'),
    # Elative أَفْعَل
    ('أَكْبَر', 'كبر', 'elative akbar'),
    ('أَصْغَر', 'صغر', 'elative asghar'),
    ('أَحْسَن', 'حسن', 'elative ahsan'),
    # Feminine elative فُعْلَى
    ('كُبْرَى', 'كبر', 'fem elative kubra'),
    ('صُغْرَى', 'صغر', 'fem elative sughra'),
    # Nisba ـيّ
    ('عَرَبِيّ', 'عرب', 'nisba 3arabi'),
    ('مِصْرِيّ', 'مصر', 'nisba misri'),
    # Masdar Form I
    ('ضَرْب', 'ضرب', 'masdar I darb'),
    ('فَهْم', 'فهم', 'masdar I fahm'),
    # Imperfect تَ prefix (2nd/3rd F) — NOT stripped (ambiguous with root)
    ('تَكْتُبُ', 'كتب', 'imperfect ta 2nd/3rd F'),
    ('تَذْهَبُ', 'ذهب', 'imperfect ta'),
    # Imperfect نَ prefix (1PL) — NOT stripped
    ('نَكْتُبُ', 'نكت', 'imperfect na 1PL'),
    # Imperfect أَ prefix (1SG) — NOT stripped
    ('أَكْتُبُ', 'كتب', 'imperfect a 1SG'),
    # Tanwin — stripped as diacritic
    ('كِتَابٌ', 'كتب', 'tanwin dammatain'),
    ('رَجُلٍ', 'رجل', 'tanwin kasratan'),
    # Loanwords
    ('تِلِفِزْيُون', 'تلف', 'loanword television — first 3 consonants تلف happen to be a valid root'),
    # Proper nouns
    ('مُحَمَّد', 'حمد', 'proper noun muhammad — root حمد is correct'),
]

fails = 0
for surface, exp_root, label in cases:
    ti = e.analyze(surface)
    ok = ti.root == exp_root
    if not ok:
        fails += 1
    mark = 'PASS' if ok else 'FAIL'
    print(f"{mark}  {surface:<22} root={ti.root!r:<14} exp={exp_root!r:<14} tmpl={ti.template!r:<26} {label}")

print(f"\n{fails} failures / {len(cases)} total")
