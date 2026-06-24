# AR engine disagreements vs gold

Gold size: 114 (114 scored, 0 excluded).
Engine accuracy on scored items: 99.1% (113/114).

Categories:
- auto-agreed with reference: 112
- reference was wrong, engine credited: 1
- engine wrong (penalised): 1 (on agree=1, on corrected=0)
- NEEDS-NATIVE-REVIEW items in gold: 0

| word | engine | reference | adjudicated gold | reason | confidence |
|---|---|---|---|---|---|
| الحياة | حيي | ل.ح.# | حيي | engine matched our correction (reference was wrong) -> credited; CAMeL ل.ح.# malformed; root ح-ي-ي is correct (engine right) | high |
| وخاصة | خيص | خ.ص.ص | وخص | engine != reference (reference accepted); engine==CAMeL (strong radicals) | high |
