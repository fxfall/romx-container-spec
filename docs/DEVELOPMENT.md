# ROMX 0.2.0 Development Policy

**Status: active development, not frozen.** This document governs changes to
the ROMX 0.2.0 standard on `main`.

## Container-only scope

ROMX standardizes serialized bytes, registries, validation, failure isolation,
and mutable-data commit semantics. It does not standardize library APIs, VFS
adapters, temporary files, database or network access, emulator selection,
user interfaces, or host save-directory policy.

A proposed feature belongs in the container standard only when its byte
representation, validation, and recovery behavior can be specified without
depending on one frontend, library, emulator, or operating system.

## Implementation review

Every normative rule must have a practical implementation path. Reviewers must
be able to describe:

- bounded parsing with checked integer arithmetic;
- streaming or random-access reads without loading the complete payload;
- preservation of the entrypoint's native first byte at absolute offset zero;
- deterministic validation and failure isolation;
- mutable updates using bounded writes without copying immutable payload data;
- strict separation between valid-container parsing and unverified salvage;
- explicit handling of unknown registry values.

The implementation path demonstrates feasibility; it does not make a specific
implementation normative.

## Version boundary

ROMX 0.2.0 uses footer wire version `2` and metadata schema version `0.2.0`.
Readers must validate the wire version before interpreting the footer or any
region.

Because the format is not frozen, an incompatible change to byte semantics,
field semantics, or validity rules may require a new wire version. Unknown wire
versions must not be interpreted as version `2`.

Stable compatibility begins only when the project explicitly freezes the
0.2.0 specification and publishes matching conformance fixtures.
