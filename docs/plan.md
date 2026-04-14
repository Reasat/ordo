# ORDO — Mondo source ingest plan

This document is the canonical reference for the ORDO preprocessing pipeline: upstream source, versioning, identifier scheme, ROBOT preprocessing, and YAML field mappings.

## Upstream source

- **Publisher:** Orphadata ([orphadata.com](https://www.orphadata.com/)).
- **Format:** OWL (`ORDO_en_X.X.owl` or aggregated `ordo_orphanet.owl` from Orphadata ORDO product).
- **Authentication:** None for public OWL downloads.
- **Official vs mirrors:** The acquire step must use Orphadata-published OWL only — not third-party repacks.

## Versioning

- Orphadata publishes versioned OWL files (e.g. `ORDO_en_4.8.owl`).
- **`scripts/acquire.py`** resolves the latest file name by scraping the Orphadata ORDO page (`resolve_latest_url()`), so weekly CI tracks the current release without hardcoding a minor version in the repo.
- **`project.Makefile`** sets `ORDO_URL` (default: `http://www.orphadata.org/data/ORDO/ordo_orphanet.owl`). For `make mirror`, an empty or default URL can defer to `acquire.py` resolution when that workflow is used; pin with `ORDO_URL=https://.../ORDO_en_4.9.owl` when needed.
- The emitted YAML **`version`** field comes from `owl:versionInfo` on the ontology header after ROBOT preprocessing (see `scripts/transform.py` → `extract_ontology_document`).

## Identifier scheme (CURIEs)

- **Namespace:** `http://www.orpha.net/ORDO/Orphanet_<digits>`
- **CURIE prefix:** `Orphanet:` (declared in `linkml/mondo_source_schema.yaml`).
- **Example:** `Orphanet:365` for disorder class IRIs.

## Pipeline shape (OWL source)

1. **`make mirror`** — Download raw OWL to `tmp/ordo_raw.owl`, merge + `odk:normalize` → `tmp/mirror-ordo.owl`.
2. **ROBOT component** (`project.Makefile` → `tmp/transformed-ordo.owl`) — remove imports; rename with `config/property-map.sssom.tsv`; SPARQL updates (`fix-complex-reification-ordo.ru`, `ordo-flatten-replacements.ru`, `exact_syn_from_label.ru`, `fix_xref_prefixes.ru`); property allowlist `config/properties.txt`; ontology/version IRI annotation.
3. **`scripts/transform.py`** — rdflib read of `tmp/transformed-ordo.owl` → `ordo.yaml`.
4. **Validate** — `linkml.validator.cli` against `linkml/mondo_source_schema.yaml`, target class `OntologyDocument`.
5. **`scripts/verify.py`** — Structural checks on `ordo.yaml` (duplicate IDs, labels, parent resolution).
6. **`linkml-owl`** — `ordo.yaml` → top-level **`ordo.owl`** (release OWL artefact).

Intermediate: `tmp/transformed-ordo.owl` is ROBOT-only and gitignored. Release artefacts: **`ordo.yaml`**, **`ordo.owl`**.

## Field mappings (OWL → YAML)

| Source | Slot / notes |
|--------|----------------|
| `rdfs:label` on `owl:Ontology` | `title`; optional `dcterms:title` |
| `owl:versionInfo` | `version` |
| `owl:Class` + Orphanet numeric IRI | term `id` / `label` |
| `obo:IAO_0000115` | `definition` |
| `oboInOwl:hasExactSynonym` (and related/narrow/broad) | synonym lists as inlined `Synonym` objects |
| `rdfs:subClassOf` (class targets) | `parents` (excluded terms and parents filtered — see below) |
| `BFO:0000050` restrictions | `part_of` |
| RO material-basis restrictions | `has_material_basis_in_*` when present |
| `oboInOwl:hasDbXref` + `skos:notation` ORPHA codes | merged into `skos_exact_match` (no `hasDbXref` in output) |
| `skos:exactMatch` / related / broad / narrow | respective `skos_*_match` slots |
| `owl:deprecated` | `deprecated` (plain `"true"` literals handled in SPARQL and Python) |

## Exclusions and hierarchy

- **Excluded subtree:** Direct children of `Orphanet:C010` (“genetic material”) are dropped (gene / locus–type artefacts, not diseases). Parent collection skips edges into excluded classes so no retained term points at an excluded parent.
- **Inclusion:** All `owl:Class` terms with Orphanet numeric IRIs and a non-empty `rdfs:label` are candidates, except the excluded subtree. Grouping classes without an ORPHA code in `skos:notation` remain valid parents (see `docs/pipeline_incidents.md`).

## QC and reports

- **`make reports`** — `robot measure` (extended JSON) on final `ordo.owl`; `sparql/count_classes_by_top_level.sparql` on mirror, transformed, and final OWL (`reports/`).

## CI and release

- **Docker:** `obolibrary/odkfull:v1.6` — `make dependencies && make all`.
- **Triggers:** See `.github/workflows/release.yml` — `workflow_dispatch`, weekly cron, push to `main` on pipeline paths.
- **Assets:** `ordo.yaml`, `ordo.owl` attached to GitHub Releases.

## Schema maintenance

- **`SCHEMA_URL` in `Makefile`:** Placeholder until a shared schema URL is published; the working schema is **`linkml/mondo_source_schema.yaml`** in this repository.

## Related docs

| File | Purpose |
|------|---------|
| [`docs/release_notes.md`](release_notes.md) | Stats and verification summary per release |
| [`docs/pipeline_incidents.md`](pipeline_incidents.md) | Incidents, root causes, resolutions |
| [`docs/refactor_report.md`](refactor_report.md) | Historical refactor changelog (v0.3.1 → v0.4.0) |
