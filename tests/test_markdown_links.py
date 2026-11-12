"""Regression tests for offline Markdown reference validation."""

from pathlib import Path

from scripts.check_markdown_links import broken_links, destinations


def test_extracts_local_links_and_skips_fenced_examples() -> None:
    """Literal examples in fenced code must not become file requirements."""
    markdown = (
        "[study](../docs/study.md#methods)\n"
        "![plot](../images/plot.png)\n"
        "[source]: <../sources/table.csv>\n"
        "```markdown\n[example](missing.md)\n```\n"
    )
    assert [url for _, url in destinations(markdown)] == [
        "../docs/study.md#methods",
        "../images/plot.png",
        "../sources/table.csv",
    ]


def test_detects_missing_parent_and_allows_existing_and_external(tmp_path: Path) -> None:
    """Detect the exact parent-traversal regression from PR #125."""
    root = tmp_path
    document = root / "results" / "case" / "request.md"
    document.parent.mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "docs" / "source.md").write_text("# Source\n", encoding="utf-8")
    document.write_text(
        "[bad](../docs/source.md)\n"
        "[good](../../docs/source.md#details)\n"
        "[external](https://example.org/data)\n"
        "[section](#local)\n",
        encoding="utf-8",
    )
    assert broken_links(document, root) == [
        "results/case/request.md:1: ../docs/source.md"
    ]


def test_rejects_links_that_escape_repository(tmp_path: Path) -> None:
    """A local link cannot silently point outside the checked repository."""
    document = tmp_path / "README.md"
    document.write_text("[outside](../private.md)\n", encoding="utf-8")
    assert broken_links(document, tmp_path) == ["README.md:1: ../private.md"]
