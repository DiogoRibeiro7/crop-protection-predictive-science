"""Validate repository-local Markdown links without fetching remote resources.

Usage: python scripts/check_markdown_links.py [paths ...]
With no paths, all tracked Markdown documents are checked.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
INLINE_LINK = re.compile(r"\[[^\]\n]+\]\((<[^>]+>|[^\s)]+)(?:\s+['\"][^)]*['\"])?\)")
REFERENCE_DEFINITION = re.compile(r"^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)", re.MULTILINE)
FENCE = re.compile(r"^\s*(```|~~~)")


def destinations(markdown: str) -> list[tuple[int, str]]:
    """Extract simple inline and reference destinations outside fenced code."""
    clean_lines: list[str] = []
    fence_marker: str | None = None
    for line in markdown.splitlines(keepends=True):
        match = FENCE.match(line)
        if match:
            marker = match.group(1)[:3]
            if fence_marker is None:
                fence_marker = marker
            elif fence_marker == marker:
                fence_marker = None
            clean_lines.append("\n")
        else:
            clean_lines.append(line if fence_marker is None else "\n")
    clean = "".join(clean_lines)
    found = [
        (clean.count("\n", 0, match.start()) + 1, match.group(1).strip("<>"))
        for pattern in (INLINE_LINK, REFERENCE_DEFINITION)
        for match in pattern.finditer(clean)
    ]
    return sorted(found)


def broken_links(document: Path, root: Path) -> list[str]:
    """Return diagnostics for missing or escaping local destinations."""
    failures: list[str] = []
    for line, destination in destinations(document.read_text(encoding="utf-8")):
        parsed = urlsplit(destination)
        if parsed.scheme or parsed.netloc or destination.startswith(("#", "//")):
            continue
        target_path = unquote(parsed.path)
        if not target_path:
            continue
        if target_path.startswith("/"):
            target = root / target_path.lstrip("/")
        else:
            target = document.parent / target_path
        resolved = target.resolve()
        if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
            failures.append(f"{document.relative_to(root)}:{line}: {destination}")
    return failures


def tracked_markdown(root: Path) -> list[Path]:
    """Use tracked files so transient outputs do not affect the check."""
    output = subprocess.check_output(["git", "ls-files", "-z", "--", "*.md"], cwd=root)
    return [root / entry.decode("utf-8") for entry in output.split(b"\0") if entry]


def main(argv: list[str] | None = None) -> int:
    """Check selected Markdown files and return a CI-friendly exit status."""
    arguments = sys.argv[1:] if argv is None else argv
    documents = [ROOT / arg for arg in arguments] if arguments else tracked_markdown(ROOT)
    failures = [failure for doc in documents for failure in broken_links(doc, ROOT)]
    for failure in failures:
        print(failure, file=sys.stderr)
    print(f"Checked {len(documents)} Markdown documents; {len(failures)} broken local links")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
