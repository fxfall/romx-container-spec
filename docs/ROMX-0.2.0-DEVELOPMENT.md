# ROMX 0.2.0 Development Policy

**Status: draft and research.** This document governs development on `main`;
it is not a frozen byte-level specification.

## Relationship to ROMX 0.1.x

ROMX 0.1.0 and 0.1.1 are historical standards retained for conformance tests,
regression tests, implementation comparison, and migration research. Their
specifications, schemas, and frozen fixtures remain available on the matching
release branches.

ROMX 0.2.0 is not required to be fully backward-compatible with ROMX 0.1.x.
Development may change:

- footer layout and wire version;
- region count, ordering, addressing, and mutability;
- payload representation, including multi-file or virtual-file-tree models;
- metadata fields, schema rules, and identifier semantics;
- integrity, recovery, and validity rules.

Compatibility readers, importers, or migration tools may be provided, but
supporting 0.1.x files is an implementation feature rather than a normative
0.2.0 format requirement.

## Version boundary

Until a 0.2.0 footer and schema are specified, tools on `main` that emit wire
version `1` remain ROMX 0.1.x test/reference implementations. They MUST NOT
label those bytes as ROMX 0.2.0.

The final ROMX 0.2.0 format MUST use a distinct wire version. Readers must be
able to distinguish 0.1.x and 0.2.0 before interpreting version-specific
footer fields or regions.

## Historical fixtures

Existing `tests/fixtures/` and `tests/fixtures/writer/` files are immutable
historical 0.1.x test vectors. ROMX 0.2.0 tests must use a separate fixture
namespace and must not rewrite the historical corpus.

No 0.2.0 layout, field, or feature is frozen merely by being discussed or
implemented experimentally on `main`; it becomes normative only when the
0.2.0 specification explicitly marks it as such.
