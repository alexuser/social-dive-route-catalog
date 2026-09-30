#!/bin/zsh
set -euo pipefail

if (( $# != 3 )); then
  print -u2 "usage: $0 INPUT_JSON PRIVATE_KEY_PEM OUTPUT_ENVELOPE_JSON"
  exit 64
fi

input_json=$1
private_key=$2
output_json=$3
work_dir=$(mktemp -d "${TMPDIR:-/private/tmp}/social-dive-catalog-signature.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT
signature_file="$work_dir/signature"
snapshot="$work_dir/catalog.json"
cp "$input_json" "$snapshot"
chmod 400 "$snapshot"

python3 "${0:A:h}/validate_catalog.py" "$snapshot" >/dev/null
openssl pkeyutl -sign -rawin -inkey "$private_key" -in "$snapshot" -out "$signature_file"
payload_base64=$(openssl base64 -A -in "$snapshot")
signature_base64=$(openssl base64 -A -in "$signature_file")

jq -n \
  --arg algorithm "Ed25519" \
  --arg payload "$payload_base64" \
  --arg signature "$signature_base64" \
  '{algorithm: $algorithm, payload: $payload, signature: $signature}' \
  >"$output_json"
