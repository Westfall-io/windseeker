# Security Notes

This document records known security advisories detected by automated dependency
scanning tools (e.g. `pip-audit`) and explains their impact, scope, and mitigation
strategy within the **Windseeker** project.

Windseeker takes dependency security seriously. Where vulnerabilities cannot be
immediately resolved due to upstream constraints, they are explicitly documented
and monitored.

---

## Current Known Advisories

### 1. PYSEC-2022-42969 — `py` (version 1.11.0)

**Package:** `py`
**Advisory:** PYSEC-2022-42969
**Status:** No fixed version available upstream
**Affected versions:** All published versions
**Severity:** Low / contextual

#### Description
The `py` package is a legacy support library historically used by parts of the
Python testing ecosystem. The reported advisory has **no patched release** as of
this writing, and the package has seen minimal maintenance activity upstream.

#### Impact on Windseeker
- `py` is **not a direct runtime dependency** of Windseeker
- It may be introduced transitively via optional developer tooling
  (e.g. test or quality-analysis utilities)
- Windseeker does **not expose user-facing functionality** that relies on `py`
  at runtime

#### Mitigation
- `py` is confined to **development / tooling contexts only**
- The vulnerability is **explicitly suppressed in CI audits** until:
  - A patched upstream release becomes available, or
  - The transitive dependency is removed entirely

#### Action Plan
- Monitor upstream `py` project for any new releases
- Remove the dependency if and when tooling no longer requires it

---

### 2. CVE-2025-53000 — `nbconvert` (version 7.16.6)

**Package:** `nbconvert`
**Advisory:** CVE-2025-53000
**Status:** No patched version listed at time of detection
**Severity:** Medium
**Platform scope:** Primarily Windows / export-related workflows

#### Description
The advisory affects `nbconvert`, a Jupyter ecosystem component used for notebook
export and conversion. The vulnerability is associated with certain export flows
and does not affect core notebook execution.

#### Impact on Windseeker
- `nbconvert` is **not a core runtime dependency**
- It is pulled in transitively via optional Jupyter tooling
- Windseeker uses `nbclient` for notebook execution and does not rely on
  `nbconvert` for user-facing operations
- The vulnerability does **not affect Linux-based CI environments** or
  headless execution paths used by Windseeker

#### Mitigation
- Notebook tooling is treated as **optional functionality**
- The advisory is **temporarily suppressed** in automated audits
- Windseeker tracks upstream Jupyter releases and will update once a fixed
  version is published

#### Action Plan
- Periodically re-run audits without suppression to check for patched releases
- Remove suppression as soon as an upstream fix becomes available

---

## CI and Audit Policy

Windseeker employs the following security practices:

- Automated dependency auditing using `pip-audit`
- GitHub Dependency Review for pull requests
- Dependabot for automated dependency updates
- Explicit documentation of any suppressed advisories

Suppressions are **never silent** and are always recorded in this file.

---

## Reporting Security Issues

If you discover a potential security issue in Windseeker:

- Please open a GitHub issue with the label **security**
- Do not disclose sensitive details publicly if exploitation is suspected
- Maintainers will respond promptly and coordinate remediation

---

_Last reviewed: 2026-01-16_
