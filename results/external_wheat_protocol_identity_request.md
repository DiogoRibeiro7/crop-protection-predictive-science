# Original-source request: wheat trial and plot identities

Source: [10.5281/zenodo.6521175](https://zenodo.org/records/6521175); checksum-verified local TSV: `zenodo_wheat_fungicide_6521175/basf-wheat-diseases.txt`.

## Verified discrepancies (not reconciliations)

- Publisher title: **56 trials**.
- Raw file: **76 `TrialId` codes**, **65 recorded geocode-years**, **56 recorded geocodes**.
- Codes above geocode-year groups: **11**; geocode-years above geocodes: **9**. These counts do not establish physical trial identities.
- Shared geocode-year example: BULGARIA (43.3, 25.0) in 2019 contains codes `31`, `32`, `33`, `34`.
- Across-year example: FRANCE (48.0, 1.8) has 2017 (8, 10), 2018 (23), 2019 (46).

## Documents to request from BASF / the Zenodo depositor

1. The authoritative definition of a published *trial* and a machine-readable `TrialId` to physical trial/site/field/plot crosswalk, covering all 76 codes and explaining the advertised 56.
2. Trial layouts, randomized treatment allocation, experimental units, block and plot replicate IDs; specifically explain codes sharing a rounded geocode and year.
3. Whether experiments at the same rounded geocode in different years are physically and statistically distinct; provide the unrounded location or site identifiers if releasable.
4. Full fungicide product/active-substance, dose and application dictionary, with `Treatment` code mapping and control definition.
5. Assessment protocol by `Organism`/`Parameter`: timing, unit, missing-value coding, repeated measurement links and yield basis.
6. The original protocol/data dictionary and, if available, documentation of the published `obs` R object. The public R scripts inspected so far only load, summarize and map the data.

## Decision boundary

The current `trial_level_treatment_effect` decision remains `requires_protocol`; no treatment-effect analysis is authorized by a numerical 56/56 match. No researchers have been contacted.
