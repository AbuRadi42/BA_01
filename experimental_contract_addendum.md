# Experimental Contract — Addendum I
## Extension to Pre-Training Predictive Framework

**Author:** Sameh AbuRadi
**Supervisor:** Fabian Geier
**Parent document:** `experimental_contract.md` (frozen before implementation)
**Addendum date:** 2026-04-17
**Status:** Proposed — pending supervisor sign-off

---

## 1. Purpose of This Addendum

This addendum extends the scientific scope of the parent contract to accommodate a theoretical direction identified during implementation. It is issued under the parent contract's §12 Freeze Clause, which permits documented, justified deviations.

The original contract prohibited, as a non-goal under §5, the proposal of a new linguistic theory. This addendum relaxes that restriction along one specific axis — the formulation of a pre-training predictive framework for language model capacity — while leaving every other non-goal intact.

---

## 2. Background and Justification

Phase 1 of the project produced a consistent monotonic gradient (Turkish 56.9%, Arabic 13.9%, English ~1%) across three typologically distinct languages. The result suggested that morphological structure may be predictive of modelling efficiency before any training is carried out. Pursuing this observation requires a light theoretical framework, which the original contract did not permit.

The scope of the study was at one point expanded towards nine languages spanning the full morphological spectrum plus three structural outliers, with nine grammar engines built and tested (5,079 tests, zero failures). On reflection, and in consultation with the supervisor, it was judged more valuable to first formalise the predictive framework on the three original languages — where the author has native-speaker access and the engines have been audited most thoroughly — than to broaden empirical coverage without a theoretical anchor. The six additional engines and their design specs are retained in the repository as future-work artefacts.

---

## 3. Scope Extension

The project is now permitted to:

- Define contributing factors that characterise a language's morphological information storage (beginning with feature-bundle cardinality and a proposed second factor, **Morphological Contextual Arity**, denoting the maximum number of grammatical categories a single word form simultaneously encodes).
- Formulate a composite pre-training capacity index as a function of those factors.
- Validate the framework ordinally against the Phase 1 results — i.e. the predicted ranking across English, Arabic, and Turkish should match the observed efficiency gradient.
- Coin terminology where existing linguistic indices (notably Greenberg's Index of Synthesis) do not capture the specific quantity being measured; new terms must be defined formally and differentiated from prior art.

All theoretical claims introduced under this addendum remain subject to the parent contract's §11 Interpretation Rules.

---

## 4. Constraints That Remain Unchanged

Every other provision of the parent contract continues to apply without modification. In particular:

- §3 Definition of learning cost.
- §5 remaining non-goals — claims of language superiority, generalisation to all languages, IIT validation, production deployment.
- §7 Parity and Fairness Rules (within-language and cross-language).
- §9 Success Criteria.
- §10 Primary and Secondary Research Questions, with the theoretical framework treated as directly supporting the Secondary Question.
- §11 Interpretation Rules.
- §12 Freeze Clause — this addendum is itself frozen upon signature.

---

## 5. Out of Scope for the Addendum

- Any claim that the framework generalises beyond the three languages formally validated in this study.
- Predictive guarantees at scales larger than the Phase 1 mini experiment.
- Replacement or revision of any engine, result, or metric already reported under the parent contract.

---

## 6. Sign-off

Addendum accepted on: __________________

Signature (Author): __________________

Signature (Supervisor): __________________

---

**End of Addendum I**
