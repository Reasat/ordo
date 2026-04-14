# ORDO Pipeline Refactoring Report

This report describes all systematic changes made to the ORDO ingest pipeline. @Reasat its probably best to let your agent also read this and directly apply all of this to your skill.

## 1. Build system: Makefile split and generalization

### What changed
- The monolithic `Makefile` was split into a **generic `Makefile`** and an **ORDO-specific `project.Makefile`** (included via `include project.Makefile`).
- All hardcoded `ordo` references in file paths are now derived from a `SOURCE` variable (`?= ordo`), making the pipeline reusable for other source ontologies.
- The old `acquire` / `build` / `build-release` targets were consolidated: `all` now runs `build` (which includes the full pipeline from ROBOT through linkml-owl) followed by `reports`.
- The `UV_RUN ?= uv run --no-sync` wrapper was removed. All Python commands now run directly (bare `python`), **since the pipeline runs inside the ODK Docker container** where dependencies are pre-installed.
- A `dependencies` target was added to install `linkml-owl==0.5.0` plus bleeding-edge `linkml` and `linkml-runtime` from the `linkml/linkml` monorepo on GitHub (required to fix an inlining bug in linkml-runtime — see Section 5).
- A `robot-plugins` target now copies ROBOT plugin JARs from `/tools/robot-plugins/` (inside the ODK container) or a local `plugins/` directory into `tmp/plugins/`, and exports `ROBOT_PLUGINS_DIRECTORY` before running ROBOT. The old hardcoded path `/home/reasat/.robot/plugins` was removed.
- An `update-schema` target was added to download the schema from a configurable `SCHEMA_URL`.
- A `reports` target was added that runs `robot measure` (extended metrics as JSON) and `count_classes_by_top_level.sparql` across mirror, transformed, and final OWL.
- A `help` target prints usage information.
- `MIR ?= true` controls whether the download step runs (use `make MIR=false build` to skip re-downloading).

### What moved to `project.Makefile`
- The `ORDO_URL` variable and the `wget` download rule for `$(RAW_OWL)`.
- The full ROBOT preprocessing chain for `$(OUTPUT_OWL)` (rename, SPARQL updates, property filtering, annotation).

### New file: `odk.sh`
- Docker wrapper script for running the pipeline inside `obolibrary/odkfull`. Usage: `./odk.sh make all`.

## 2. Schema changes (`mondo_source_schema.yaml` v0.3.1 → v0.4.0)

### Slots removed from `OntologyTerm`
| Slot | Reason |
|------|--------|
| `database_cross_references` | Xrefs are now merged into `skos_exact_match` during transform |
| `obo_has_close_synonym` | Not needed for Mondo ingest |
| `comments` | Not needed in output OWL |
| `see_also` | Not needed in output OWL |
| `descriptions` | Not needed in output OWL |
| `mondo_generated` | Replaced by `SynonymTypeEnum.generated` |
| `mondo_generated_from_label` | Replaced by `SynonymTypeEnum.generated_from_label` |
| `mondo_omim_included` | Replaced by `SynonymTypeEnum.omim_included` |
| `mondo_omim_formerly` | Replaced by `SynonymTypeEnum.omim_formerly` |
| `mondo_abbreviation` | Replaced by `SynonymTypeEnum.abbreviation` |
| `is_root` | Internal to the transform; should not appear in output OWL |

Also removed from `OntologyDocument`: `comments`, `descriptions`.

### Slots renamed (human-readable names)
| Old | New | URI (unchanged) |
|-----|-----|-----------------|
| `ro_0004001` | `has_material_basis_in_germline_mutation_in` | `RO:0004001` |
| `ro_0004003` | `has_material_basis_in_somatic_mutation_in` | `RO:0004003` |
| `ro_0004004` | `has_material_basis_in` | `RO:0004004` |
| `bfo_0000050` | `part_of` | `BFO:0000050` |
| `bfo_0000051` | `has_part` | `BFO:0000051` |

### OWL interpretation changes
| Slot | Before | After | Why |
|------|--------|-------|-----|
| RO/BFO slots | `range: uriorcurie`, `owl: AnnotationAssertion` | `range: OntologyTerm`, `owl: ObjectSomeValuesFrom` | These are object properties; output must be existential restrictions (`SubClassOf(... some ...)`) not bare triples |
| `deprecated` | `ifabsent: "false"` | no `ifabsent` | Prevents `owl:deprecated false` from appearing on every non-deprecated term |

### New: `Synonym` class and `SynonymTypeEnum`
- **`Synonym`** class with `synonym_text` (required string) and `synonym_type` (optional `SynonymTypeEnum`).
- **`SynonymTypeEnum`** with values: `omim_included` (`MONDO:omim_included`), `generated_from_label` (`MONDO:GENERATED_FROM_LABEL`), `generated` (`MONDO:GENERATED`), `omim_formerly` (`MONDO:omim_formerly`), `abbreviation` (`MONDO:ABBREVIATION`). Each has a `meaning` CURIE for OWL rendering.
- Synonym slots (`exact_synonyms`, `related_synonyms`, `narrow_synonyms`, `broad_synonyms`) now have `range: Synonym` and `inlined_as_list: true`.
- OWL rendering uses `owl.template` (Jinja) on `slot_usage` within `OntologyTerm` instead of `owl: AnnotationAssertion`. This is necessary because linkml-owl's `AnnotationAssertion` mode cannot reach into inlined objects. The templates iterate over each synonym and emit OFN `AnnotationAssertion(...)` with conditional `Annotation(oboInOwl:hasSynonymType <IRI>)` axiom annotations. A `replace('"', '\\"')` filter escapes embedded double-quotes in synonym text to produce valid OFN.

## 3. Transform changes (`scripts/transform.py`)

### Xrefs → `skos_exact_match`
- `oboInOwl:hasDbXref` values and `skos:notation` ORPHA codes are now collected and merged into `skos_exact_match` instead of being output as `database_cross_references`. This was requested because `hasDbXref` should not appear in the final OWL.

### `is_root` no longer emitted
- The `is_root` field is still computed internally (to decide whether a term has parents), but is no longer written to the YAML output or the schema.

### Non-disease term exclusion
- Terms that are direct children of `Orphanet_C010` ("genetic material") are now excluded. These are gene/locus type classifications (`gene with protein product`, `non coding RNA`, `disorder-associated locus`) that were incorrectly appearing as disease classes.
- The exclusion set is also applied when collecting parents, so no disease term will reference an excluded term via `rdfs:subClassOf`.

### Synonym structure
- Synonyms are now emitted as objects (`{"synonym_text": "..."}`) instead of plain strings, conforming to the new `Synonym` class in the schema. This is so we can add additional metadata such as "abbreviation" etc to the model.

### YAML quoting
- A custom YAML dumper quotes strings containing `,`, `:`, `{`, or `}` to prevent downstream parsing issues.

## 4. New SPARQL files

### `sparql/fix_xref_prefixes.ru`
Ported from `mondo-ingest`. Normalizes invalid CURIE prefixes in `oboInOwl:hasDbXref` values:
- `ICD-11:` → `ICD11:`
- `ICD-10:` → `ICD10:`
- `MeSH:` → `MESH:`
- `OMIM:PS` → `OMIMPS:`
- Strips non-breaking spaces (U+00A0)

This runs during the ROBOT preprocessing step (added to both `project.Makefile` and the SPARQL query list).

### `sparql/count_classes_by_top_level.sparql`
Counts descendant classes under the three ORDO top-level terms (`Orphanet:557493` Disorder, `Orphanet:557492` Group of disorders, `Orphanet:557494` Subtype of a disorder) using `rdfs:subClassOf+`. Used by the `reports` target.

## 5. Known issues / technical debt

### linkml-runtime inlining bug
There is a bug in `linkml_runtime`'s `_normalize_inlined` (in `yamlutils.py`) where values containing commas in `inlined_as_list` slots cause a `ValueError` during key parsing. The workaround is to install `linkml-runtime` from the `main` branch of `linkml/linkml` (monorepo at `packages/linkml_runtime`). A minimal reproducer is in `bug-report/`. This should be filed against `linkml/linkml`.

### `SCHEMA_URL` placeholder
The `update-schema` target uses a placeholder URL (`https://raw.githubusercontent.com/TODO/mondo-source-schema/main/...`). This needs to be updated once the schema has a canonical home.

### Output file naming
- The ROBOT-processed OWL is now at `tmp/transformed-ordo.owl` (was `ordo.owl`).
- The final LinkML-generated OWL is now the top-level `ordo.owl` (was `ordo_from_linkml.owl`).

## 6. New reports

The `reports/` directory now contains:
- `metrics.json` — ROBOT extended ontology metrics for the final OWL
- `mirror-top-level-counts.tsv` — class counts under top-level terms in the mirrored OWL
- `transformed-top-level-counts.tsv` — same for ROBOT-processed OWL
- `top-level-counts.tsv` — same for the final LinkML-generated OWL

# MISSING

`MIRROR_OWL` and `OUTPUT_OWL` should probably both be moved to project.Makefile.. The reason is that many projects dont actually have an OWL intermediate / OWL source - (eg, your ICD pipeline using the API). Maybe this is something that we do on a case by case basis? 
