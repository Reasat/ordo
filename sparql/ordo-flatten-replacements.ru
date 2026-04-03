PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX ORDO: <http://www.orpha.net/ORDO/>

# Orphanet_C056 (moved_to): the deprecated class has been merged into or renamed to
# the target — treat as exact replacement → skos:exactMatch.
INSERT {
    ?cls skos:exactMatch ?replacement .
}
WHERE {
    ?cls owl:deprecated ?dep .
    FILTER(str(?dep) = "true")
    ?cls rdfs:subClassOf ?restriction .
    ?restriction owl:onProperty ORDO:Orphanet_C056 ;
                 owl:someValuesFrom ?replacement .
    FILTER(isIRI(?replacement))
}
;

# Orphanet_C057 (referred_to): the deprecated class should be considered replaced by
# the target, but the mapping is a suggestion → skos:relatedMatch (oboInOwl:consider).
INSERT {
    ?cls skos:relatedMatch ?replacement .
}
WHERE {
    ?cls owl:deprecated ?dep .
    FILTER(str(?dep) = "true")
    ?cls rdfs:subClassOf ?restriction .
    ?restriction owl:onProperty ORDO:Orphanet_C057 ;
                 owl:someValuesFrom ?replacement .
    FILTER(isIRI(?replacement))
}
