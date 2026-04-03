# ORDO — Orphanet Rare Disease Ontology ingest. See docs/plan.md.
#
# Pipeline:
#   make acquire      — download latest ORDO OWL (no auth needed)
#   make build        — ROBOT preprocessing → ordo.owl
#   make build-release — build + transform → validate → LinkML OWL
#
# Requires: ROBOT (≥ 1.9), obolibrary/odkfull Docker image for CI, uv for Python.

ROBOT       ?= robot
# Local plugin path — overridden to /tools/robot-plugins inside obolibrary/odkfull Docker (CI).
ROBOT_PLUGINS_DIRECTORY ?= /home/reasat/.robot/plugins
PYTHON      ?= python3
UV_RUN      ?= uv run --no-sync
CONFIG_DIR  := config
SCRIPTS_DIR := scripts
SPARQL_DIR  := sparql
TMP_DIR     := tmp
OUTPUT_OWL  := ordo.owl
OUTPUT_OWL_LINKML := ordo_from_linkml.owl
MIRROR_OWL  := $(TMP_DIR)/mirror-ordo.owl
RAW_OWL     := $(TMP_DIR)/ordo_raw.owl
YAML_OUT    := ordo.yaml
SCHEMA      := linkml/mondo_source_schema.yaml

# Override to pin a specific version: make acquire ORDO_URL=https://.../ORDO_en_4.9.owl
ORDO_URL    ?=
URIBASE     := http://purl.obolibrary.org/obo
TODAY       ?= $(shell date +%Y-%m-%d)

.PHONY: all build build-release clean acquire resolve-version

all: build

$(TMP_DIR):
	mkdir -p $(TMP_DIR)

# Download latest ORDO OWL (version auto-resolved; override with ORDO_URL=...)
$(RAW_OWL): | $(TMP_DIR)
	$(UV_RUN) python $(SCRIPTS_DIR)/acquire.py --output $@ $(if $(ORDO_URL),--url $(ORDO_URL),)
	@echo "Downloaded: $@"

acquire: $(RAW_OWL)

resolve-version: $(RAW_OWL)
	$(UV_RUN) python $(SCRIPTS_DIR)/resolve_version.py --input $(RAW_OWL)

# Mirror: merge + normalize
$(MIRROR_OWL): $(RAW_OWL) | $(TMP_DIR)
	ROBOT_PLUGINS_DIRECTORY=$(ROBOT_PLUGINS_DIRECTORY) \
	$(ROBOT) merge -i $(RAW_OWL) \
		odk:normalize --add-source true \
		-o $@
	@echo "Built $@"

# ORDO component: rename properties, fix reification, flatten replacements, add exact synonyms, filter
$(OUTPUT_OWL): $(MIRROR_OWL) \
		$(CONFIG_DIR)/property-map.sssom.tsv $(CONFIG_DIR)/properties.txt \
		$(SPARQL_DIR)/fix-complex-reification-ordo.ru \
		$(SPARQL_DIR)/ordo-flatten-replacements.ru \
		$(SPARQL_DIR)/exact_syn_from_label.ru
	$(ROBOT) remove -i $(MIRROR_OWL) --select imports \
		rename --mappings $(CONFIG_DIR)/property-map.sssom.tsv \
			--allow-missing-entities true --allow-duplicates true \
		query \
			--update $(SPARQL_DIR)/fix-complex-reification-ordo.ru \
			--update $(SPARQL_DIR)/ordo-flatten-replacements.ru \
			--update $(SPARQL_DIR)/exact_syn_from_label.ru \
		remove -T $(CONFIG_DIR)/properties.txt --select complement --select properties --trim true \
		annotate \
			--ontology-iri $(URIBASE)/mondo/sources/ordo.owl \
			--version-iri $(URIBASE)/mondo/sources/$(TODAY)/ordo.owl \
		-o $@
	@echo "Built $@"

build: $(OUTPUT_OWL)
	@echo "Build complete: $(OUTPUT_OWL)"

# ROBOT component + LinkML transform + validate + data2owl
build-release: build
	$(UV_RUN) python $(SCRIPTS_DIR)/transform.py --input $(OUTPUT_OWL) --schema $(SCHEMA) --output $(YAML_OUT)
	$(UV_RUN) python -m linkml.validator.cli --schema $(SCHEMA) --target-class OntologyDocument $(YAML_OUT)
	$(UV_RUN) python -m linkml_owl.dumpers.owl_dumper --schema $(SCHEMA) -o $(OUTPUT_OWL_LINKML) $(YAML_OUT)
	@echo "Build complete: $(YAML_OUT), $(OUTPUT_OWL) (ROBOT), $(OUTPUT_OWL_LINKML) (LinkML)"

clean:
	rm -f $(OUTPUT_OWL) $(OUTPUT_OWL_LINKML) $(YAML_OUT)
	rm -rf $(TMP_DIR)
