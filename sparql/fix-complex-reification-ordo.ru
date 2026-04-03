PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX oboInOwl: <http://www.geneontology.org/formats/oboInOwl#>

# ORDO annotates oboInOwl:hasDbXref assertions with owl:Axiom reification blocks
# (using obo:ECO_0000218 to record mapping type). These blocks cause issues when
# ROBOT processes the ontology. This update removes the Axiom blocks entirely,
# retaining the plain hasDbXref triples on the classes themselves.

DELETE {
    ?ax ?p ?v .
}
WHERE {
    ?ax rdf:type owl:Axiom ;
        owl:annotatedProperty oboInOwl:hasDbXref ;
        ?p ?v .
}
