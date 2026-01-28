from __future__ import annotations

import re
from typing import Dict, List, Tuple

# Matches imports anywhere in a line (so "package A { import B; }" works),
# but ignores lines that start with // (after whitespace).
IMPORT_RE = re.compile(
    r"""
    ^(?!\s*//)                 # line must NOT start with optional whitespace then //
    .*?                        # allow anything before 'import' (e.g., "package A {")
    \bimport\b                 # whole word 'import' (won't match 'important')
    \s+                        # at least one space
    (                          # capture the target
        '(?:[^'\\]|\\.)*'      # single-quoted string
        |
        [A-Za-z_][\w.:/-]*     # bare token (e.g. B::)
    )
    """,
    re.VERBOSE,
)

PACKAGE_START_RE = re.compile(
    r"""
    (?m)^(?!\s*//)\s*          # not a line comment
    (?:\w+\s+)*                # optional modifiers like 'library'
    \bpackage\b\s+
    (                          # capture package name
        '(?:[^'\\]|\\.)*'
        |
        [A-Za-z_][\w.:/-]*
    )
    """,
    re.VERBOSE,
)

VIEW_START_RE = re.compile(
    r"""
    ^(?!\s*//)\s*              # not a line comment
    \bview\b\s+
    (                          # capture view name
        '(?:[^'\\]|\\.)*'
        |
        [A-Za-z_][\w.:/-]*
    )
    \s*\{                      # views are blocks
    """,
    re.VERBOSE,
)

INNER_PACKAGE_OPEN_RE = re.compile(
    r"""
    ^(?!\s*//)\s*
    (?:\w+\s+)*                # optional modifiers
    \bpackage\b\s+
    (                          # capture package name
        '(?:[^'\\]|\\.)*'
        |
        [A-Za-z_][\w.:/-]*
    )
    \s*\{                      # only track nested packages that open a block
    """,
    re.VERBOSE,
)


def strip_line_comments(text: str) -> str:
    """Remove // comments (line-level) from an entire file's text."""
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def _normalize_qualified_name(name: str) -> str:
    """
    Normalize captured names:
    - strip surrounding single quotes already handled elsewhere
    - remove a trailing '::' (common in patterns like A::*)
    """
    return re.sub(r"::\s*$", "", name)


def _strip_quotes_if_needed(token: str) -> str:
    """Remove surrounding single quotes if token is a single-quoted string; keep content as-is."""
    if len(token) >= 2 and token[0] == "'" and token[-1] == "'":
        return token[1:-1]
    return token


def _top_level_of_qualified_name(name: str) -> str:
    """If name is 'A::B::C', return 'A'. Otherwise return name."""
    return name.split("::", 1)[0]


def _find_matching_brace(text: str, open_brace_index: int) -> int:
    """Return index of matching '}' for the '{' at open_brace_index, or -1 if not found."""
    depth = 0
    i = open_brace_index
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _brace_depth_prefix(text: str) -> List[int]:
    """
    Return prefix brace depth at each character index.
    depth[i] is the brace depth *before* processing text[i].
    """
    depth = [0] * (len(text) + 1)
    d = 0
    for i, ch in enumerate(text):
        depth[i] = d
        if ch == "{":
            d += 1
        elif ch == "}":
            d = max(0, d - 1)
    depth[len(text)] = d
    return depth


def extract_top_level_packages_with_text(text: str) -> List[Tuple[str, str]]:
    """
    Extract ONLY top-level packages and store their full declaration text.
    Nested packages are left inside the parent's captured text and are NOT returned
    as separate entries.
    """
    results: List[Tuple[str, str]] = []
    depths = _brace_depth_prefix(text)

    for m in PACKAGE_START_RE.finditer(text):
        # Only accept packages that start at top-level brace depth
        if depths[m.start()] != 0:
            continue

        raw_name = m.group(1)
        name = _normalize_qualified_name(_strip_quotes_if_needed(raw_name))

        # Find token after name: ';' or '{'
        j = m.end()
        n = len(text)
        while j < n and text[j].isspace():
            j += 1
        if j >= n:
            continue

        if text[j] == ";":
            end = j + 1
            while end < n and text[end] != "\n":
                end += 1
            results.append((name, text[m.start() : end]))

        elif text[j] == "{":
            close = _find_matching_brace(text, j)
            if close == -1:
                results.append((name, text[m.start() :]))
                continue
            end = close + 1

            # include trailing ';' if present
            k = end
            while k < n and text[k].isspace():
                k += 1
            if k < n and text[k] == ";":
                end = k + 1

            results.append((name, text[m.start() : end]))

        else:
            end = j
            while end < n and text[end] != "\n":
                end += 1
            results.append((name, text[m.start() : end]))

    return results


def collect_views_from_top_level_package_text(
    package_name: str, package_full_text: str
) -> List[str]:
    """
    Collect fully-qualified view names from within a *top-level* package text block.

    Example result:
      Flashlight_StarterModel::Views1::flashlightPartsTree
    """
    clean_lines = [line.split("//", 1)[0] for line in package_full_text.splitlines()]

    views: List[str] = []

    depth = 0
    # stack entries: (nested_package_name, enter_depth_after_open_brace)
    stack: List[tuple[str, int]] = []

    for raw_line in clean_lines:
        line = raw_line

        # pop stack if we've exited nested package blocks
        while stack and depth < stack[-1][1]:
            stack.pop()

        # detect nested package openings: package X {
        m_pkg = INNER_PACKAGE_OPEN_RE.search(line)
        if m_pkg:
            inner = _normalize_qualified_name(_strip_quotes_if_needed(m_pkg.group(1)))

            # Skip the outermost package declaration if it appears inside its own text
            if inner != package_name:
                stack.append((inner, depth + 1))

        # detect view openings: view Y {
        m_view = VIEW_START_RE.search(line)
        if m_view:
            view_name = _normalize_qualified_name(_strip_quotes_if_needed(m_view.group(1)))
            prefix = [package_name] + [p for p, _ in stack]
            views.append("::".join(prefix + [view_name]))

        depth += line.count("{") - line.count("}")

    return views


def collect_all_views(package_text: Dict[str, str]) -> List[str]:
    """Collect all fully-qualified view names across all top-level packages."""
    all_views: List[str] = []
    for pkg, txt in package_text.items():
        all_views.extend(collect_views_from_top_level_package_text(pkg, txt))

    # de-dup while preserving order
    seen = set()
    ordered: List[str] = []
    for v in all_views:
        if v not in seen:
            seen.add(v)
            ordered.append(v)
    return ordered


def parse_imports_from_package_text(
    pkg_name: str,
    pkg_full_text: str,
) -> List[str]:
    """
    Return list of imported TOP-LEVEL package names (e.g. import A::B::C -> "A").
    """
    imports: List[str] = []
    for raw_line in pkg_full_text.splitlines():
        line = raw_line.split("//", 1)[0]
        m_imp = IMPORT_RE.search(line)
        if not m_imp:
            continue
        imp_full = _normalize_qualified_name(_strip_quotes_if_needed(m_imp.group(1)))
        imp_top = _top_level_of_qualified_name(imp_full)

        # ignore self-imports at top-level
        if imp_top == pkg_name:
            continue

        imports.append(imp_top)
    return imports
