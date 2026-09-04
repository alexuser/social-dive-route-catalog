#!/bin/zsh
set -euo pipefail

if (( $# != 3 )); then
  print -u2 "usage: $0 INPUT_JSON PRIVATE_KEY_PEM OUTPUT_ENVELOPE_JSON"
  exit 64
fi

input_json=$1
private_key=$2
output_json=$3
signature_file=$(mktemp "${TMPDIR:-/private/tmp}/social-dive-catalog-signature.XXXXXX")
trap 'rm -f "$signature_file"' EXIT

jq -e '.schema == "social-dive-route-catalog@1" and (.routes | type == "array" and length > 0)' \
  "$input_json" >/dev/null
openssl pkeyutl -sign -rawin -inkey "$private_key" -in "$input_json" -out "$signature_file"
payload_base64=$(openssl base64 -A -in "$input_json")
signature_base64=$(openssl base64 -A -in "$signature_file")

jq -n \
  --arg algorithm "Ed25519" \
  --arg payload "$payload_base64" \
  --arg signature "$signature_base64" \
  '{algorithm: $algorithm, payload: $payload, signature: $signature}' \
  >"$output_json"
