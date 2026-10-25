# ADR-0001: Separate engineering logic from CAD API

Status: Accepted as architectural direction, 2026-10-14

## Decision
Define dimensioned and parameterized design intent in a CAD-neutral Python core. Keep Fusion API calls in adapter modules.

## Rationale
Reuse geometry rules across furniture types, allow high-coverage unit tests, and prevent Fusion API assumptions from contaminating calculations.

## Implications
CAD-dependent geometry validation remains required. AI must return structured specs rather than arbitrary executable CAD code.
