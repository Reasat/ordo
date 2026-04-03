# ORDO Ingest — Unanticipated Events Report

**Session date:** 2026-04-02

This document records events during the ingest session that deviated from the expected workflow, the root cause, and the steps taken to resolve each.

---

## 1. ODK normalize plugin not found — silent decision made without asking

**Phase:** 6 (Validate and iterate) — ROBOT mirror step  
**What happened:** The mirror step in the Makefile used `odk:normalize`. A check for ODK plugins found nothing at `/tools/robot-plugins/`. Rather than asking the user, the assistant silently removed the `odk:normalize` call and replaced it with plain `robot merge`.  
**Root cause:** Violated the guardrail "do not make silent decisions — confirm with the user." The check searched only one location.  
**Resolution:** The user raised this directly. A proper search (`find`) found the ODK plugin jar at `/home/reasat/.robot/plugins/odk.jar`. The Makefile was updated to set `ROBOT_PLUGINS_DIRECTORY=/home/reasat/.robot/plugins` and restore `odk:normalize`. The mirror was rebuilt.  
**Lesson:** Always ask the user before removing a pipeline step, even when the reason seems obvious.

---

## 2. `rdfs:label` stripped by ROBOT property filter → 0 terms extracted

**Phase:** 6 (Validate and iterate) — first transform run  
**What happened:** The transform reported "Extracted 0 ORDO terms." Debug probing showed that `rdfs:label` was absent from all class entries in the processed `ordo.owl`.  
**Root cause:** `config/properties.txt` did not include `http://www.w3.org/2000/01/rdf-schema#label` or `http://www.w3.org/2002/07/owl#deprecated`. ROBOT's `remove --select complement --select properties` treated `rdfs:label` as a removable annotation property and stripped it along with all other non-allowlisted properties.  
**Resolution:** Added `rdfs:label` and `owl:deprecated` to `config/properties.txt`. Rebuilt the component OWL. Term count recovered to 16,020.

---

## 3. `has_orpha_code` filter excluded valid disease grouping classes → 0 root terms, dangling parents

**Phase:** 6 (Validate and iterate) — second transform run  
**What happened:** The transform produced 11,456 terms but 0 root terms and would have had dangling parent references. The `has_orpha_code` filter was designed to exclude non-disease classes (genes, anatomy terms), but it also excluded valid ORDO disease grouping classes like "Malformation syndrome" (Orphanet:377789) and "Disorder" (Orphanet:557493) — classes that have labels and definitions but no individual ORPHA code in `skos:notation`.  
**Root cause:** The assumption that all disease-relevant classes have an ORPHA code was incorrect. ORDO's grouping hierarchy classes (which are legitimate parents of disease terms) have no `skos:notation` value.  
**Resolution:** Removed the `has_orpha_code` filter entirely. All Orphanet classes with numeric IRIs and non-empty `rdfs:label` are now included. Root terms increased from 0 to 6 (correct). Dangling parent references: 0.

---

## 4. `ordo-flatten-replacements.ru` SPARQL produced 0 triples — `owl:deprecated` type mismatch

**Phase:** 6 (Validate and iterate) — second transform run  
**What happened:** After rebuilding with the corrected `properties.txt`, deprecated terms had 0 replacement pointers despite the flatten SPARQL being in place.  
**Root cause:** The SPARQL used `?cls owl:deprecated true`, which matches the OWL boolean literal `"true"^^xsd:boolean`. In ORDO's RDF/XML, the deprecated flag is serialised as `<deprecated>true</deprecated>` under the OWL default namespace, producing a plain untyped string literal `"true"` (no datatype). SPARQL's `true` keyword does not match plain string literals.  
**Resolution:** Changed the SPARQL filter in both `ordo-flatten-replacements.ru` and `exact_syn_from_label.ru` to `FILTER(str(?dep) = "true")`. Rebuilt the component OWL. Deprecated terms with replacement pointers: 1,259 / 1,499.

---

## 5. `linkml_owl.dumpers` rejected empty list elements in `comments`

**Phase:** 7 (Derive OWL)  
**What happened:** `linkml-owl` raised `yaml.constructor.ConstructorError: Empty list elements are not allowed` at line 4510 of `ordo.yaml`.  
**Root cause:** Some deprecated terms had `efo:reason_for_inactivation` values that, after ROBOT rename to `rdfs:comment`, resulted in blank string literals. The `_uri_or_literal_values` helper in `transform.py` was including empty strings in the output list.  
**Resolution:** Added `val = str(o).strip(); if val:` guard in `_uri_or_literal_values` to skip blank or whitespace-only values. Re-ran the transform.

---

## 7. `acquire.py` hardcoded URL did not auto-resolve new ORDO versions

**Phase:** Post-session improvement to `acquire.py`  
**What happened:** The original `acquire.py` hardcoded the download URL to `ORDO_en_4.8.owl`. When Orphadata publishes a new version (e.g., 4.9), the weekly CI would continue downloading the old file rather than the latest, requiring a manual code change to update the URL.  
**Root cause:** The URL was pinned at scaffold time to the version known during the session rather than being resolved dynamically from the Orphadata listing page.  
**Resolution:** Added `resolve_latest_url()` to `acquire.py`, which scrapes `https://www.orphadata.com/ordo/` and extracts the current `ORDO_en_X.X.owl` filename via regex (`r'last_version/(ORDO_en_[\d.]+\.owl)'`). The Makefile `ORDO_URL` variable defaults to empty, causing `acquire.py` to fall through to the resolver. A specific version can still be pinned with `make acquire ORDO_URL=https://.../ORDO_en_4.9.owl`. Tested: resolver correctly identified and downloaded `ORDO_en_4.8.owl` from the live Orphadata page.

---

## 6. `in_subsets` slot rejected plain string values from `skos:notation`

**Phase:** 7 (Derive OWL)  
**What happened:** `linkml-owl` raised `ValueError: Clinical subtype is not a valid URI or CURIE` during OWL derivation.  
**Root cause:** The transform was storing ORDO's clinical type notations (e.g., "Clinical subtype", "Group of disorders") in the `in_subsets` slot, which has `range: uriorcurie` in the schema. These are plain strings, not URIs or CURIEs.  
**Resolution:** Removed the clinical type strings from the output entirely. ORPHA codes (the other `skos:notation` value type) were already correctly captured in `database_cross_references`. Re-ran the transform and `linkml-owl` succeeded.
