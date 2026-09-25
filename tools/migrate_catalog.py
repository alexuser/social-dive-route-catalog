#!/usr/bin/env python3
"""Convert only the frozen public v1 source into an unsigned v2 review file."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
import sys

from validate_catalog import CATALOG_SCHEMA, RECORD_SCHEMA, ContractError, canonical_decimal, decode_document

LEGACY_SHA256 = '003229169d561d876660679ae828dbdaca181d38dd9e3fbc9a4be801016d76e8'
CATEGORIES = {
    'the-road': 'fictional-demo',
    'monterey-breakwater-wall': 'source-linked-draft',
    'monterey-metridium-fields-pipeline': 'source-linked-draft',
    'point-lobos-whalers-cove-inner-loop': 'source-linked-draft',
    'point-lobos-middle-reef-sand-channel': 'source-linked-draft',
    'point-lobos-hole-in-the-wall': 'source-linked-draft',
    'point-lobos-bluefish-secret-pass': 'source-linked-draft',
}


def exact_json(value):
    if isinstance(value, Decimal):
        return canonical_decimal(value)
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k) + ':' + exact_json(v) for k, v in sorted(value.items())) + '}'
    if isinstance(value, list):
        return '[' + ','.join(exact_json(v) for v in value) + ']'
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def migrate(payload):
    if hashlib.sha256(payload).hexdigest() != LEGACY_SHA256:
        raise ContractError('Only the frozen published v1 payload can migrate')
    document = json.loads(payload, parse_float=Decimal)
    document['schema'] = CATALOG_SCHEMA
    for record in document['routes']:
        record['schema'] = RECORD_SCHEMA
        record['category'] = CATEGORIES[record['id']]
        for point in record['profile']:
            seconds = Decimal(point.pop('minute')) * 60
            if seconds != seconds.to_integral_value() or not 0 <= seconds <= 18_000:
                raise ContractError('time-precision')
            point['elapsedSeconds'] = int(seconds)
            depth = Decimal(point['depthMeters'])
            exact_depth = depth.quantize(Decimal('0.000001'))
            if abs(depth - exact_depth) > Decimal('0.000000001'):
                raise ContractError('depth-precision')
            point['depthMeters'] = exact_depth
    result = (exact_json(document) + '\n').encode('utf-8')
    decode_document(result)
    return result


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: migrate_catalog.py FROZEN_V1_JSON NEW_UNSIGNED_V2_JSON')
    try:
        result = migrate(Path(sys.argv[1]).read_bytes())
        with Path(sys.argv[2]).open('xb') as output:
            output.write(result)
    except (OSError, ContractError) as error:
        raise SystemExit(f'Migration rejected: {error}') from error
    print('Created unsigned v2 review file; no signing or publication performed')


if __name__ == '__main__':
    main()
