# Public research datasets (original source files)

These files are retained byte-for-byte from public source repositories, with
their published checksums and licences in `manifest.json`. All source data are
unmodified. No candidate identity matching, measurement harmonisation, missing
data imputation, model calibration, or cross-study treatment joining has been
performed.

| Directory | Citation and source | License | What it can support |
| --- | --- | --- | --- |
| `zenodo_wheat_fungicide_6521175/` | Holst (2022), [10.5281/zenodo.6521175](https://doi.org/10.5281/zenodo.6521175) | CC BY 4.0 | 56 wheat field fungicide trials, untreated/treated disease incidence and yield; **field-only** |
| `zenodo_aphid_pesticide_19805135/` | Wang et al. (2026), [10.5281/zenodo.19805135](https://doi.org/10.5281/zenodo.19805135) | CC BY 4.0 | Five experimental worksheets including controlled pesticide/heat tests and field observations; **not fungicide efficacy** |
| `dryad_pathogen_temperature_4mw6m90jv/` | *High temperatures reduce growth, infection, and transmission of a naturally occurring fungal plant pathogen* (2024), [10.5061/dryad.4mw6m90jv](https://doi.org/10.5061/dryad.4mw6m90jv), version 3 | CC0 1.0 | Growth chamber, greenhouse, and field pathogen responses to temperature; **not pesticide discovery** |

## What was imported

- Wheat: the original tab-delimited `basf-wheat-diseases.txt`, with 2,276 data
  rows plus header; other upstream plotting scripts and map are not required for
  ingestion and are not vendored here.
- Aphids: the original `Experiment.xlsx` (five worksheets) and `README.txt`.
- Pathogen temperature: all 13 files in the upstream Dryad version-3 archive,
  including its README, original measurements, and field records.

The Dryad archive does not contain the seven R analysis scripts mentioned in its
README; the repository does not claim to provide those missing scripts.

## Integrity and reproducibility

Run this test offline after installing the project:

```bash
pytest tests/test_external_data.py
```

The test verifies original byte lengths and MD5 (Zenodo) or SHA-256 (Dryad)
against the source-provided manifest. MD5 is retained only as the publisher's
file identity checksum, not as a security guarantee.

The immutable source files must remain separate from future cleaned tables.
This import does **not** satisfy the project’s three-stage *fungicide-candidate*
linkage requirement. The datasets must be evaluated independently before
scientific modelling, especially where dose units, targets, treatments, and
experimental units differ.

## Source awaiting direct access

Meng (2021), [10.17632/97bfppx7c2.1](https://doi.org/10.17632/97bfppx7c2.1),
contains laboratory and field data on fungicides against *Colletotrichum
fructicola* and is published under CC BY 4.0. The public Mendeley API returned
HTTP 401 during this extraction, so none of its files were downloaded or
represented as locally available. Revisit this source when an authorized direct
download is possible. Do not substitute fabricated values or copy summary
figures as raw observations.
