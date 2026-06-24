# Real-text eval: TR

Sample: 250 real Wikipedia sentences.

## Agreement vs gold

| Metric | Agree | Total | Rate |
|---|---:|---:|---:|
| Lemma agreement | 2919 | 3109 | 93.9% |
| POS agreement (context) | 2533 | 3306 | 76.6% |
| POS agreement (isolated) | 2390 | 3306 | 72.3% |

## Top Lemma mismatches

- (21×) olan: gold=['o'] eng=ol
- (5×) biri: gold=['biri'] eng=bir
- (3×) birer: gold=['birer'] eng=bir
- (3×) giden: gold=['gide', 'git'] eng=gid
- (3×) giderek: gold=['giderek', 'git'] eng=gid
- (2×) ilaveten: gold=['ilâveten'] eng=ilave
- (2×) doğumu: gold=['doğu', 'doğum'] eng=doğ
- (2×) dolu: gold=['do', 'dolu'] eng=dol
- (2×) kalan: gold=['kala', 'kalan'] eng=kal
- (2×) kesip: gold=['kes'] eng=kesip
- (2×) durumu: gold=['duru', 'durum'] eng=dur
- (2×) teşkilatı: gold=['teşkilât'] eng=teşkil
- (2×) öldürülmesini: gold=['öl'] eng=öldür
- (2×) sadakati: gold=['sadakat'] eng=sadakati
- (1×) Hükümdarlığı: gold=['hükümdar'] eng=hükümdarlık
- (1×) gerçekleştirdiği: gold=['gerçek'] eng=gerçekle
- (1×) birleştirip: gold=['bir', 'birleş'] eng=birleştirip
- (1×) siyasi: gold=['siyasî'] eng=siyasi
- (1×) liderliğini: gold=['lider'] eng=liderlik
- (1×) ölüme: gold=['ölü', 'ölüm'] eng=öl
- (1×) istemeyen: gold=['iste'] eng=istem
- (1×) saygı: gold=['saygı'] eng=say
- (1×) gelindiğinde: gold=['gel'] eng=gelin
- (1×) edilmesini: gold=['et'] eng=ed
- (1×) teşkilatsız: gold=['teşkilât'] eng=teşkil

## Top POS mismatches

- (21×) olan: gold=['ADJ'] eng=NOUN
- (20×) Yesügey: gold=['OTHER'] eng=PROPN
- (14×) onun: gold=['ADJ', 'NUM', 'PRON', 'VERB'] eng=NOUN
- (11×) Camuka: gold=['OTHER'] eng=NOUN
- (9×) Şira: gold=['OTHER'] eng=PROPN
- (8×) olan: gold=['ADJ', 'VERB'] eng=NOUN
- (8×) kendisine: gold=['PRON'] eng=NOUN
- (8×) ise: gold=['ADV', 'NOMINAL', 'VERB'] eng=CONJ
- (8×) Sohan: gold=['OTHER'] eng=PROPN
- (7×) ilk: gold=['ADJ', 'ADV', 'NOMINAL'] eng=UNKNOWN
- (7×) olarak: gold=['VERB'] eng=CONV
- (6×) Onon: gold=['OTHER'] eng=PROPN
- (6×) üvey: gold=['ADJ', 'VERB'] eng=NOUN
- (6×) adlı: gold=['NOMINAL'] eng=ADJ
- (6×) at: gold=['NOMINAL', 'VERB'] eng=UNKNOWN
- (6×) Bughurçi: gold=['OTHER'] eng=PROPN
- (6×) ona: gold=['ADJ', 'NUM', 'PRON', 'VERB'] eng=NOUN
- (5×) göçebe: gold=['ADJ'] eng=NOUN
- (5×) başka: gold=['ADJ', 'OTHER'] eng=NOUN
- (5×) biri: gold=['PRON'] eng=NOUN
- (5×) ok: gold=['NOMINAL'] eng=UNKNOWN
- (5×) Cuci: gold=['OTHER'] eng=PROPN
- (5×) Sorhan: gold=['OTHER'] eng=PROPN
- (5×) Sangum: gold=['OTHER'] eng=PROPN
- (4×) getirerek: gold=['VERB'] eng=CONV
