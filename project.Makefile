# ORDO — Orphanet Rare Disease Ontology source-specific rules.

ORDO_URL ?= http://www.orphadata.org/data/ORDO/ordo_orphanet.owl

ifeq ($(MIR),true)
$(RAW_OWL): | $(TMP_DIR)
	wget $(ORDO_URL) -O $@
	@echo "Downloaded: $@"
endif

# ORDO component: rename properties, fix reification, flatten replacements, add exact synonyms, fix xref prefixes, filter
$(OUTPUT_OWL): $(MIRROR_OWL) \
		$(CONFIG_DIR)/property-map.sssom.tsv \
		$(CONFIG_DIR)/properties.txt \
		$(SPARQL_DIR)/fix-complex-reification-ordo.ru \
		$(SPARQL_DIR)/ordo-flatten-replacements.ru \
		$(SPARQL_DIR)/exact_syn_from_label.ru \
		$(SPARQL_DIR)/fix_xref_prefixes.ru
	$(ROBOT) remove -i $(MIRROR_OWL) --select imports \
		rename --mappings $(CONFIG_DIR)/property-map.sssom.tsv \
			--allow-missing-entities true --allow-duplicates true \
		query \
			--update $(SPARQL_DIR)/fix-complex-reification-ordo.ru \
			--update $(SPARQL_DIR)/ordo-flatten-replacements.ru \
			--update $(SPARQL_DIR)/exact_syn_from_label.ru \
			--update $(SPARQL_DIR)/fix_xref_prefixes.ru \
		remove -T $(CONFIG_DIR)/properties.txt --select complement --select properties --trim true \
		annotate \
			--ontology-iri $(URIBASE)/mondo/sources/$(SOURCE).owl \
			--version-iri $(URIBASE)/mondo/sources/$(TODAY)/$(SOURCE).owl \
		-o $@
	@echo "Build complete: $@"
