# Route record contract 2

The app and producer share the byte-identical `route-record-v2-fixtures.json`.
Each fixture stores an exact JSON payload string so binary floating-point
re-encoding cannot change its decimal geometry. Every valid case includes a
canonical record checksum; invalid cases include
the expected rejection category. Run the producer suite with
`python3 -m unittest discover -s tests -v`.

Documents use `social-dive-route-catalog@2`, contain 1–500 unique records, and
are limited to 700,000 UTF-8 bytes before signing (the app caps envelopes at
1,000,000 bytes). Each record declares `social-dive-route-record@2` and has:

- `id`: 1–128 lowercase ASCII letters, digits, or hyphens, starting with a letter/digit.
- `name`, `site`, `provenance`, `limitations`: nonblank, trimmed strings, limited
  to 100, 160, 1,000, and 2,000 UTF-8 bytes. ASCII controls are forbidden.
- `aliases`: at most 20 distinct, nonblank strings of at most 100 UTF-8 bytes.
- `category`: `fictional-demo` or `source-linked-draft`. A fictional record has
  an explicit null `sourceURL`; a source-linked record requires an HTTPS URL.
- `sourceURL`: at most 2,048 ASCII bytes, a dotted DNS host, and no credentials,
  port, fragment, spaces, malformed percent escapes, or numeric IP literal.
  This link is attribution, never an instruction to fetch or trust its content.
- `profile`: 2–256 ordered points with integer `elapsedSeconds` in 0–18,000 and
  decimal `depthMeters` in 0–152.4 with at most six fractional digits. Times
  strictly increase. The first point is (0, 0), maximum depth is at least
  0.3048 m, and the last point remains submerged for generated ascent.

Subsecond input is rejected as `time-precision`; it is never rounded into the
same second. Depth precision beyond six decimal places is rejected. The app
keeps Decimal depths and integer seconds in the source record and local draft;
27.432 m yields a 90 ft summary without a truncated meter intermediate.

Canonical identity is SHA-256 over UTF-8 fields, each prefixed by its decimal
byte count followed by `:`. Field order: record schema, id, name, alias count,
aliases in order, site, provenance, source URL (empty for null), limitations,
category, point count, then each point's integer seconds and non-exponential
decimal meters without insignificant zeroes. Identity covers the original
record, including provenance; edited local geometry remains separate.

A valid signature authenticates bytes, not navigation, dive safety, a verified
log, or review. Every import remains an unreviewed local draft. Fictional
records belong in a separate demo section, outside ordinary site discovery.

## Legacy migration

The existing `catalog-v1.json` and signed envelope stay unchanged. The app may
read the previously published v1 payload only after signature verification and
an exact SHA-256 match to
`003229169d561d876660679ae828dbdaca181d38dd9e3fbc9a4be801016d76e8`.
Its seven known IDs have an explicit category map. Migration converts minutes
to exact whole seconds and removes only the known binary floating-point tails
within 0.000000001 m before checking the new contract. Arbitrary or modified
v1 payloads are rejected, even if signed. The producer now signs only v2;
publishing a new production catalog is a separate reviewed action.
