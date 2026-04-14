#!/usr/bin/env python3
"""
Serialize ORDO component OWL → schema-conformant YAML.

Expects the output of the ROBOT component build (rename, reification fix, exact-syn-from-label,
property strip). Reads rdfs:label, obo:IAO_0000115 (was efo:definition),
oboInOwl:hasExactSynonym (was efo:alternative_term), rdfs:subClassOf, skos:notation,
oboInOwl:hasDbXref, BFO:0000050 restrictions, and owl:deprecated directly.

Includes all Orphanet numeric class IRIs with a non-empty label, except direct children of
Orphanet:C010 (genetic material subtree). Xrefs and ORPHA notations merge into skos_exact_match.

Input:  tmp/transformed-ordo.owl (ROBOT component output)
Output: ordo.yaml  (conforms to linkml/mondo_source_schema.yaml)

Usage:
    python scripts/transform.py \\
        --input tmp/transformed-ordo.owl \\
        --schema linkml/mondo_source_schema.yaml \\
        --output ordo.yaml
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml
from rdflib import OWL, RDF, RDFS, BNode, Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, Namespace, SKOS

# ── Namespaces ────────────────────────────────────────────────────────────────

OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")
OBO = Namespace("http://purl.obolibrary.org/obo/")
MONDO = Namespace("http://purl.obolibrary.org/obo/mondo#")

ORDO_IRI_PREFIX = "http://www.orpha.net/ORDO/Orphanet_"
ORDO_CURIE_PREFIX = "Orphanet:"

DEFINITION = OBO["IAO_0000115"]
BFO_0000050 = OBO["BFO_0000050"]
OWL_DEPRECATED_PROP = OWL.deprecated

# Matches the Orphanet code notation value (e.g. "ORPHA:284963")
ORPHA_CODE_RE = re.compile(r"^ORPHA:\d+$")


# ── IRI helpers ───────────────────────────────────────────────────────────────

def is_ordo_disease_iri(iri: str) -> bool:
    """True for IRIs like http://www.orpha.net/ORDO/Orphanet_<digits>."""
    if not iri.startswith(ORDO_IRI_PREFIX):
        return False
    suffix = iri[len(ORDO_IRI_PREFIX):]
    return suffix.isdigit()


# Non-disease classification roots whose children should be excluded (e.g. gene types)
EXCLUDED_PARENTS = {
    ORDO_IRI_PREFIX + "C010",  # genetic material (gene with protein product, non coding RNA, etc.)
}


def is_child_of_excluded(g: Graph, subj: URIRef) -> bool:
    """True if any rdfs:subClassOf target is in the excluded parent set."""
    for o in g.objects(subj, RDFS.subClassOf):
        if isinstance(o, URIRef) and str(o) in EXCLUDED_PARENTS:
            return True
    return False


def iri_to_curie(iri: str) -> str:
    if iri.startswith(ORDO_IRI_PREFIX):
        return ORDO_CURIE_PREFIX + iri[len(ORDO_IRI_PREFIX):]
    return iri


def _literal_values(g: Graph, subj: URIRef, pred) -> list[str]:
    out = [str(o) for o in g.objects(subj, pred) if isinstance(o, Literal)]
    return sorted(set(out)) if out else []


def _uri_values(g: Graph, subj: URIRef, pred) -> list[str]:
    out = [str(o) for o in g.objects(subj, pred) if isinstance(o, URIRef)]
    return sorted(out) if out else []


def _uri_or_literal_values(g: Graph, subj: URIRef, pred) -> list[str]:
    out: list[str] = []
    for o in g.objects(subj, pred):
        if isinstance(o, (Literal, URIRef)):
            val = str(o).strip()
            if val:
                out.append(val)
    return sorted(set(out)) if out else []


# ── Graph traversal ─────────────────────────────────────────────────────────

def get_direct_ordo_parents(g: Graph, subj: URIRef, excluded_iris: set[str]) -> list[str]:
    """Return CURIEs of direct rdfs:subClassOf targets that are ORDO disease IRIs."""
    parents = []
    for o in g.objects(subj, RDFS.subClassOf):
        if isinstance(o, URIRef) and is_ordo_disease_iri(str(o)) and str(o) not in excluded_iris:
            parents.append(iri_to_curie(str(o)))
    return sorted(parents)


def get_bfo_part_of_targets(g: Graph, subj: URIRef) -> list[str]:
    """Return CURIEs of BFO:0000050 (part_of) restriction targets."""
    targets = []
    for o in g.objects(subj, RDFS.subClassOf):
        if not isinstance(o, BNode):
            continue
        on_prop = g.value(o, OWL.onProperty)
        some_values = g.value(o, OWL.someValuesFrom)
        if on_prop == BFO_0000050 and some_values and isinstance(some_values, URIRef):
            if is_ordo_disease_iri(str(some_values)):
                targets.append(iri_to_curie(str(some_values)))
    return sorted(targets)


def extract_ontology_document(g: Graph) -> dict:
    doc: dict = {}
    for ont in g.subjects(RDF.type, OWL.Ontology):
        if not isinstance(ont, URIRef):
            continue
        lbl = g.value(ont, RDFS.label)
        if lbl:
            doc["title"] = str(lbl)
        ver = g.value(ont, OWL.versionInfo)
        if ver:
            doc["version"] = str(ver)
        dct = g.value(ont, DCTERMS.title)
        if dct:
            doc["dcterms_title"] = str(dct)
        comments = _literal_values(g, ont, RDFS.comment)
        if comments:
            doc["comments"] = comments
        break

    if "title" not in doc:
        doc["title"] = "ORDO"
    if "version" not in doc:
        doc["version"] = "unknown"
    return doc


def extract_terms(g: Graph) -> list[dict]:
    """
    Extract ORDO disease classes from the component graph.

    Drops direct children of the non-disease root Orphanet:C010; all other Orphanet
    numeric classes with a label are included (including grouping classes without ORPHA codes).
    """
    candidate_iris: set[str] = {
        str(s)
        for s in g.subjects(RDF.type, OWL.Class)
        if isinstance(s, URIRef) and is_ordo_disease_iri(str(s))
    }

    # Build set of IRIs to exclude (children of non-disease roots like C010)
    excluded_iris: set[str] = {
        iri for iri in candidate_iris
        if is_child_of_excluded(g, URIRef(iri))
    }

    terms: list[dict] = []

    for iri in sorted(candidate_iris - excluded_iris):
        subj = URIRef(iri)

        curie = iri_to_curie(iri)

        # ── Label ──────────────────────────────────────────────────────────────
        label_node = g.value(subj, RDFS.label)
        if label_node is None:
            continue
        label = str(label_node)

        # ── Deprecated ─────────────────────────────────────────────────────────
        dep_node = g.value(subj, OWL_DEPRECATED_PROP)
        is_deprecated = dep_node is not None and str(dep_node).strip().lower() == "true"

        # ── Definition (efo:definition renamed → obo:IAO_0000115 by ROBOT) ─────
        defn_node = g.value(subj, DEFINITION)
        definition = str(defn_node) if defn_node else None

        # ── Exact synonyms (efo:alternative_term renamed → oboInOwl:hasExactSynonym) ──
        exact_syns: list[str] = [
            str(o)
            for o in g.objects(subj, OBOINOWL.hasExactSynonym)
            if isinstance(o, Literal)
        ]

        # ── Parents (direct is-a) ──────────────────────────────────────────────
        parent_curies = get_direct_ordo_parents(g, subj, excluded_iris)

        # ── BFO part-of cross-classification ──────────────────────────────────
        part_of_targets = get_bfo_part_of_targets(g, subj)

        # ── Root detection ────────────────────────────────────────────────────
        has_thing_parent = OWL.Thing in g.objects(subj, RDFS.subClassOf)
        is_root = has_thing_parent or len(parent_curies) == 0

        # ── Assemble term dict ─────────────────────────────────────────────────
        term: dict = {"id": curie, "label": label}
        if is_deprecated:
            term["deprecated"] = True
        if definition:
            term["definition"] = definition
        if exact_syns:
            term["exact_synonyms"] = [{"synonym_text": s} for s in sorted(set(exact_syns))]
        if not is_root:
            term["parents"] = parent_curies
        if part_of_targets:
            term["part_of"] = part_of_targets

        # ── Optional annotation slots ──────────────────────────────────────────
        for key, pred in (
            ("related_synonyms", OBOINOWL.hasRelatedSynonym),
            ("narrow_synonyms", OBOINOWL.hasNarrowSynonym),
            ("broad_synonyms", OBOINOWL.hasBroadSynonym),
        ):
            vals = _literal_values(g, subj, pred)
            if vals:
                term[key] = [{"synonym_text": s} for s in vals]

        # Collect xrefs and ORPHA notation codes → merge into skos:exactMatch
        xrefs = _uri_or_literal_values(g, subj, OBOINOWL.hasDbXref)
        notations = _uri_or_literal_values(g, subj, SKOS.notation)
        orpha_codes = [n for n in notations if ORPHA_CODE_RE.match(n)]
        all_xrefs = sorted(set(xrefs + orpha_codes))

        for key, pred in (
            ("skos_exact_match", SKOS.exactMatch),
            ("skos_broad_match", SKOS.broadMatch),
            ("skos_narrow_match", SKOS.narrowMatch),
            ("skos_related_match", SKOS.relatedMatch),
        ):
            vals = _uri_or_literal_values(g, subj, pred)
            if vals:
                term[key] = vals

        # Merge xrefs into skos:exactMatch
        if all_xrefs:
            existing = term.get("skos_exact_match", [])
            term["skos_exact_match"] = sorted(set(existing + all_xrefs))

        terms.append(term)

    return terms


# ── Main ──────────────────────────────────────────────────────────────────────

def transform(input_path: Path, output_path: Path) -> None:
    print(f"Parsing component OWL: {input_path}", file=sys.stderr)
    g = Graph()
    g.parse(str(input_path))

    doc = extract_ontology_document(g)
    terms = extract_terms(g)

    active = sum(1 for t in terms if not t.get("deprecated"))
    deprecated = sum(1 for t in terms if t.get("deprecated"))
    print(f"Extracted {len(terms)} ORDO terms ({active} active, {deprecated} deprecated)", file=sys.stderr)

    doc["terms"] = terms

    # Use a dumper that quotes all strings to avoid linkml-owl parsing issues
    # with values containing commas, colons, etc.
    class QuotedDumper(yaml.Dumper):
        pass

    QuotedDumper.add_representer(
        str,
        lambda dumper, data: dumper.represent_scalar("tag:yaml.org,2002:str", data, style="'")
        if any(c in data for c in ",:{}")
        else dumper.represent_scalar("tag:yaml.org,2002:str", data),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        yaml.dump(doc, fh, Dumper=QuotedDumper, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"Written: {output_path}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serialize ORDO component OWL → schema YAML")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if not args.schema.exists():
        print(f"Error: schema file not found: {args.schema}", file=sys.stderr)
        sys.exit(1)

    transform(args.input, args.output)


if __name__ == "__main__":
    main()
