# Mondo source ingest pipeline.
#
# Pipeline:
#   make mirror     — download the raw source OWL
#   make build      — mirror + ROBOT preprocessing + transform + validate + LinkML OWL
#   make reports    — generate QC reports
#   make all        — build + reports
#
# Requires: ROBOT (≥ 1.9), uv for Python.

# ── Source identity (override per source) ─────────────────────────────────────
SOURCE      ?= ordo

# ── Shared variables ──────────────────────────────────────────────────────────
ROBOT       ?= robot
CONFIG_DIR  := config
SCRIPTS_DIR := scripts
SPARQL_DIR  := sparql
TMP_DIR     := tmp
PLUGINS_DIR := $(TMP_DIR)/plugins
SCHEMA      := linkml/mondo_source_schema.yaml
SCHEMA_URL  ?= https://raw.githubusercontent.com/TODO/mondo-source-schema/main/linkml/mondo_source_schema.yaml
URIBASE     := http://purl.obolibrary.org/obo
TODAY       ?= $(shell date +%Y-%m-%d)
MIR         ?= true

# Derived paths (generic, based on SOURCE)
RAW_OWL         := $(TMP_DIR)/$(SOURCE)_raw.owl
MIRROR_OWL      := $(TMP_DIR)/mirror-$(SOURCE).owl
OUTPUT_OWL      := $(TMP_DIR)/transformed-$(SOURCE).owl
OUTPUT_OWL_LINKML := $(SOURCE).owl
YAML_OUT        := $(SOURCE).yaml

# ── Phony targets ─────────────────────────────────────────────────────────────
.PHONY: all build clean mirror robot-plugins reports dependencies help update-schema verify

# ── Generic targets ───────────────────────────────────────────────────────────

all: build reports

mirror: $(RAW_OWL)

robot-plugins:
	mkdir -p $(PLUGINS_DIR)
	if [ -d /tools/robot-plugins ]; then cp /tools/robot-plugins/*.jar $(PLUGINS_DIR)/; fi
	if [ -d plugins ] && ls plugins/*.jar >/dev/null 2>&1; then cp plugins/*.jar $(PLUGINS_DIR)/; fi

dependencies:
	pip install --quiet --break-system-packages linkml-owl==0.5.0 \
		"linkml @ git+https://github.com/linkml/linkml.git@main#subdirectory=packages/linkml" \
		"linkml-runtime @ git+https://github.com/linkml/linkml.git@main#subdirectory=packages/linkml_runtime"

# Mirror: merge + normalize
$(MIRROR_OWL): $(RAW_OWL) | robot-plugins
	export ROBOT_PLUGINS_DIRECTORY=$(PLUGINS_DIR) && \
	$(ROBOT) merge -i $(RAW_OWL) \
		odk:normalize --add-source true \
		-o $@
	@echo "Built $@"

build: $(OUTPUT_OWL) | dependencies
	python $(SCRIPTS_DIR)/transform.py --input $(OUTPUT_OWL) --schema $(SCHEMA) --output $(YAML_OUT)
	python -m linkml.validator.cli --schema $(SCHEMA) --target-class OntologyDocument $(YAML_OUT)
	python $(SCRIPTS_DIR)/verify.py --yaml $(YAML_OUT)
	python -m linkml_owl.dumpers.owl_dumper --schema $(SCHEMA) -o $(OUTPUT_OWL_LINKML) $(YAML_OUT)
	@echo "Build complete: $(YAML_OUT), $(OUTPUT_OWL) (ROBOT), $(OUTPUT_OWL_LINKML) (LinkML)"

verify:
	python $(SCRIPTS_DIR)/verify.py --yaml $(YAML_OUT)

PREFIXES_METRICS=--prefix 'OMIM: http://omim.org/entry/' \
	--prefix 'CHR: http://purl.obolibrary.org/obo/CHR_' \
	--prefix 'UMLS: http://linkedlifedata.com/resource/umls/id/' \
	--prefix 'HGNC: https://www.genenames.org/data/gene-symbol-report/\#!/hgnc_id/' \
	--prefix 'biolink: https://w3id.org/biolink/vocab/'

reports:
	mkdir -p reports
	$(ROBOT) measure $(PREFIXES_METRICS) -i $(OUTPUT_OWL_LINKML) --format json --metrics extended --output reports/metrics.json
	$(ROBOT) query -i $(MIRROR_OWL) --query $(SPARQL_DIR)/count_classes_by_top_level.sparql reports/mirror-top-level-counts.tsv
	$(ROBOT) query -i $(OUTPUT_OWL) --query $(SPARQL_DIR)/count_classes_by_top_level.sparql reports/transformed-top-level-counts.tsv
	$(ROBOT) query -i $(OUTPUT_OWL_LINKML) --query $(SPARQL_DIR)/count_classes_by_top_level.sparql reports/top-level-counts.tsv

clean:
	rm -f $(OUTPUT_OWL) $(OUTPUT_OWL_LINKML) $(YAML_OUT)
	rm -rf $(TMP_DIR)
	rm -rf reports

$(TMP_DIR):
	mkdir -p $(TMP_DIR)

update-schema:
	wget $(SCHEMA_URL) -O $(SCHEMA)
	@echo "Updated schema from $(SCHEMA_URL)"

help:
	@echo "$$data"

define data
Usage: [IMAGE=(odklite|odkfull)] [ODK_DEBUG=yes] sh odk.sh make [(MIR)=(false|true)] command

----------------------------------------
	Command reference
----------------------------------------
Core commands:
* all:			Run the entire pipeline (build + reports).
* build:		Run the entire release pipeline. Use make MIR=false build to avoid re-downloading.
* verify:		Run structural checks on $(YAML_OUT) (also runs at end of build).
* mirror:		Just obtain the raw source.
* reports:		Create reports from built artifacts.
* clean:		Delete all temporary files and reports.
* help:			Print usage information.

Dependency management:
* robot-plugins:	Install ROBOT plugins from ODK container or local plugins/ directory.
* dependencies:		Install Python dependencies not part of the ODK container.

endef
export data

# ── Include source-specific rules ─────────────────────────────────────────────
include project.Makefile
