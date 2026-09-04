# Social Dive route catalog

Signed, downloadable route-planning drafts for the Social Dive Planner iOS beta.

These files are not dive plans, surveyed navigation, verified diver logs, current-condition reports, or decompression schedules. Never use them to execute a real dive. Each imported route remains an unreviewed local draft and must be checked against training, current site rules, conditions, and trusted planning software.

The app accepts `catalog-v1.signed.json` only when its Ed25519 signature validates against the public key compiled into the app. It otherwise keeps its bundled offline catalog.

To sign a reviewed update without committing the private key:

```sh
./tools/sign_catalog.sh catalog-v1.json /secure/path/ed25519-private.pem catalog-v1.signed.json
```
