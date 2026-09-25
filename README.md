# Social Dive route catalog

Signed, downloadable route-planning drafts for the Social Dive Planner iOS beta.

These files are not dive plans, surveyed navigation, verified diver logs, current-condition reports, or decompression schedules. Never use them to execute a real dive. Each imported route remains an unreviewed local draft and must be checked against training, current site rules, conditions, and trusted planning software.

The current published v1 files remain unchanged. Updated clients support the
[version 2 record contract](contract/README.md), with shared golden fixtures and
an exact-payload migration for the existing v1 publication. Signing only proves
authenticity; all route records and imports remain unreviewed planning inputs.

To sign a reviewed update without committing the private key:

```sh
python3 tools/validate_catalog.py reviewed-catalog-v2.json
./tools/sign_catalog.sh reviewed-catalog-v2.json /secure/path/ed25519-private.pem catalog-v2.signed.json
```

For an offline starting point, convert the frozen publication into a new
unsigned file, then review any edits before signing:

```sh
python3 tools/migrate_catalog.py catalog-v1.json reviewed-catalog-v2.json
```

The migration refuses changed v1 bytes or an existing output file. It neither
changes the published catalog nor accesses a signing key.

The signer validates an immutable input snapshot before accessing the key.
Malformed metadata, unsafe source links, fractional seconds, unsupported
precision, and out-of-range geometry fail closed. No production key or
signature is needed for the offline test suite:

```sh
python3 -m unittest discover -s tests -v
```
