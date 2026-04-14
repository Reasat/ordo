# ORDO Ingest — Release Notes

**ORDO version:** 4.8  
**Build date:** 2026-04-02

---

## Ontology statistics

| Metric | Count |
|---|---|
| Total terms | 16,020 |
| Active terms | 14,521 |
| Deprecated terms | 1,499 |
| Active with definitions (`obo:IAO_0000115`) | 6,891 (69%) |
| Active with exact synonyms | 9,957 (100%) |
| Root terms | 6 |
| Deprecated with replacement pointer (`skos:exactMatch` or `skos:relatedMatch`) | 1,259 / 1,499 |
| Deprecated without replacement | 240 |
| Dangling parent references | 0 |
| BFO:0000050 (part-of) cross-classification links | present on majority of active terms |

## Phase 9 verification

- `python scripts/verify.py --yaml ordo.yaml` — PASS (duplicate IDs, labels, parent resolution).
- `linkml-validate` — run as part of `make build` (target class `OntologyDocument`).
