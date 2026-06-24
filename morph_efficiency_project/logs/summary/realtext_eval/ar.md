# Real-text eval: AR

Sample: 250 real Wikipedia sentences.

## Agreement vs gold

| Metric | Agree | Total | Rate |
|---|---:|---:|---:|
| Root agreement (fair: weak=wildcard) | 2886 | 3185 | 90.6% |
| Root agreement (skeleton) | 3070 | 3185 | 96.4% |
| POS-class agreement (context) | 4020 | 5135 | 78.3% |
| POS-class agreement (isolated) | 3387 | 5135 | 66.0% |

## Top Root mismatches

- (15×) الحياة: gold=ل.ح.# eng=حيي
- (7×) الحيّة: gold=ل.ح.# eng=حيي
- (4×) وخاصة: gold=خ.ص.ص eng=خيص
- (3×) قوّة: gold=ق.#.# eng=قوي
- (3×) أكسيد: gold=#.ك.س.د eng=ءكسيد
- (3×) الكربون: gold=ك.ر.ب.ن eng=كرب
- (3×) مليار: gold=م.ل.#.ر eng=ليار
- (2×) ذرّتا: gold=ذ.ر.# eng=ذرتا
- (2×) بالتالي: gold=بلتل eng=تول
- (2×) خاص: gold=خ.ص.ص eng=خيص
- (2×) التالية: gold=#.ل.# eng=تول
- (2×) المطريّة: gold=ط.ر.# eng=مطر
- (2×) وبالتالي: gold=بلتل eng=تول
- (2×) للحياة: gold=ل.ح.# eng=حيي
- (2×) أنابيب: gold=ن.ب.ب eng=ءنب
- (2×) إنّما: gold=#.ن.ن eng=ءنم
- (2×) وادي: gold=#.د.# eng=ودي
- (2×) انهارت: gold=ه.#.ر eng=هرت
- (2×) أدّى: gold=#.د.د eng=ءدى
- (2×) الصحي: gold=ص.ح.ح eng=صحو
- (2×) بوسائل: gold=#.س.ل eng=سءل
- (2×) الأمور: gold=#.م.ر eng=مور
- (2×) اللغة: gold=ل.غ.# eng=ولغ
- (2×) الأغاني: gold=غ.ن.# eng=غين
- (2×) المادية: gold=م.د.د eng=مدي

## Top POS mismatches

- (160×) من: gold=['ADP', 'OTHER'] eng=PART
- (39×) كما: gold=['CONJ', 'NOMINAL', 'VERB'] eng=PART
- (29×) التي: gold=['NOMINAL', 'OTHER'] eng=PART
- (28×) عند: gold=['NOMINAL', 'VERB'] eng=ADP
- (24×) ذلك: gold=['NOMINAL', 'OTHER'] eng=PART
- (22×) ماء: gold=['NOMINAL'] eng=VERB
- (21×) وذلك: gold=['NOMINAL', 'OTHER'] eng=PART
- (17×) والتي: gold=['NOMINAL', 'OTHER'] eng=PART
- (16×) أيضاً: gold=['ADV', 'NOMINAL', 'VERB'] eng=PART
- (13×) بين: gold=['NOMINAL', 'VERB'] eng=ADP
- (13×) ما: gold=['OTHER'] eng=PART
- (13×) حدوث: gold=['NOMINAL'] eng=VERB
- (11×) أجل: gold=['NOMINAL', 'VERB'] eng=PART
- (10×) بخار: gold=['NOMINAL'] eng=VERB
- (10×) حيث: gold=['CONJ'] eng=PART
- (10×) حوالي: gold=['ADP', 'NOMINAL'] eng=VERB
- (10×) ولكن: gold=['ADP', 'CONJ', 'NOMINAL'] eng=VERB
- (10×) عندما: gold=['NOMINAL'] eng=CONJ
- (10×) يؤدّي: gold=['VERB'] eng=NOM
- (10×) كبيرة: gold=['NOMINAL'] eng=VERB
- (9×) أمّا: gold=['CONJ', 'NOMINAL', 'OTHER', 'VERB'] eng=PART
- (9×) أخرى: gold=['NOMINAL'] eng=VERB
- (9×) تحت: gold=['ADV', 'NOMINAL', 'VERB'] eng=ADP
- (8×) حين: gold=['ADP', 'NOMINAL'] eng=CONJ
- (8×) تلك: gold=['NOMINAL', 'OTHER', 'VERB'] eng=PART
