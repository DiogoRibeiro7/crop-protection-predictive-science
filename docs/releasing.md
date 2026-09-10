# Release runbook

This repository uses a permanent manual release workflow in `.github/workflows/release.yml`.
Releases are created only from the current `main` commit after that exact commit has passed push CI.

## 1. Prepare release metadata

Before merging a release-preparation PR, update all release-facing metadata to the same version:

- `pyproject.toml` → `[project].version`
- `src/crop_protection_ps/__init__.py` → `__version__`
- `CITATION.cff` → `version` and `date-released`
- `.zenodo.json` → `version`
- `CHANGELOG.md` → add a heading for the release version

Do not regenerate `poetry.lock` solely because the project version changed. Regenerate it only when
the dependency graph changes.

The normal test suite contains a release-metadata consistency test, so version drift should fail CI
before the release workflow is ever dispatched.

## 2. Merge only after pull-request CI passes

The release-preparation PR must pass the complete CI contract, including:

- `quality`
- Python 3.11, 3.12 and 3.13 tests
- `package-artifact`
- `scientific-smoke`
- `container-scientific`

After the PR is merged, wait for the push-triggered CI run on `main` to complete successfully.
The reusable release workflow refuses to release a `main` commit without a successful push CI run.

## 3. Capture the exact release commit

Copy the full 40-character SHA of the current `main` commit after its push CI is green.

Do not dispatch the release workflow with a branch name, abbreviated SHA, previous release commit, or
feature-branch commit. The workflow intentionally requires the requested SHA to equal current
`main`.

## 4. Dispatch the release workflow

In GitHub Actions, open the `Release` workflow and choose **Run workflow**.

Provide:

- `version`: semantic version without the `v` prefix, for example `1.2.0`
- `target_sha`: the full green `main` commit SHA
- `prerelease`: `true` only for an intentional prerelease

The workflow then:

1. validates the version format and exact release target;
2. confirms a successful push CI exists for that SHA;
3. verifies version agreement across package, citation, Zenodo and changelog metadata;
4. runs `poetry check --lock`;
5. builds wheel and source distribution;
6. installs the wheel in a clean environment and runs the installed CLI outside the repository;
7. creates `SHA256SUMS`;
8. creates an annotated `v<version>` tag if it does not already exist;
9. refuses to move an existing tag to another commit;
10. creates the GitHub Release or repairs its managed assets if a previous publication was partial;
11. downloads the published assets and verifies that their SHA-256 hashes match the locally built
    files from the same workflow run.

## 5. Verify the published release

After the workflow succeeds, verify all of the following in GitHub:

- the annotated tag `v<version>` resolves to the requested `target_sha`;
- the GitHub Release is not a draft;
- prerelease state matches the dispatch input;
- the wheel is present;
- the source distribution is present;
- `SHA256SUMS` is present.

The release workflow is designed to be safely rerunnable. If the tag already exists at the exact
requested commit, it is preserved. If the release exists, the workflow replaces the managed wheel,
sdist and checksum assets from the newly verified build and validates them again.

## 6. Zenodo

The repository contains both `CITATION.cff` and `.zenodo.json`.

`.zenodo.json` carries the archive metadata used by the GitHub–Zenodo integration, including the
author ORCID. `CITATION.cff` remains the repository citation metadata used by GitHub and other
citation-aware tools.

After a release is archived by Zenodo, verify the deposited version, author, ORCID, title and licence
before treating the DOI metadata as final.

## Scientific release boundary

A software release does not reopen the empirical model-selection programme. The scientific stopping
rules in `ROADMAP.md` remain in force. New release work may package, document or reproduce existing
evidence, but new prospectively promoted Bipolaris candidates require new independent evidence or one
of the explicitly recorded reopening conditions.
