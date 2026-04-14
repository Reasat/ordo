# ordo

Preprocessed [Orphadata](https://www.orphadata.com/) ORDO (Orphanet Rare Disease Ontology) for Mondo ingest — ROBOT preprocessing, LinkML YAML, and LinkML-derived OWL.

## Setup

1. Install dependencies: `uv sync` (or use the ODK Docker image which installs Python deps via `make dependencies`).

## Run

```bash
# OWL pipeline (ROBOT + LinkML inside ODK Docker):
./odk.sh make all              # full pipeline: mirror + build + reports
./odk.sh make MIR=false build  # skip re-downloading raw OWL
```

## Outputs

| File | Description |
|------|-------------|
| `ordo.yaml` | Primary artefact for Mondo ingest |
| `ordo.owl` | Final OWL (LinkML-derived; ROBOT intermediate is `tmp/transformed-ordo.owl`) |
| `reports/` | QC metrics and class counts |

## Docs

| Doc | Contents |
|-----|----------|
| [`docs/plan.md`](docs/plan.md) | Pipeline architecture, field mappings, ID scheme |
| [`docs/release_notes.md`](docs/release_notes.md) | Ontology stats and verification results per release |
| [`docs/pipeline_incidents.md`](docs/pipeline_incidents.md) | Pipeline incidents: errors, deviations, resolutions |
