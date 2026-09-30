#!/usr/bin/env python3
"""Offline semantic gate for social-dive-route-catalog@2. No network or keys."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

CATALOG_SCHEMA = 'social-dive-route-catalog@2'
RECORD_SCHEMA = 'social-dive-route-record@2'
MAX_PAYLOAD_BYTES = 700_000


class ContractError(ValueError):
    pass


def require(condition, code):
    if not condition:
        raise ContractError(code)


def text(value, maximum):
    return (isinstance(value, str) and bool(value.strip()) and value == value.strip()
            and len(value.encode('utf-8')) <= maximum
            and all(ord(c) >= 32 and ord(c) != 127 for c in value))


def source_url(value):
    if not text(value, 2048) or not value.isascii() or any(c.isspace() for c in value):
        return False
    if re.search(r'%(?![0-9A-Fa-f]{2})', value):
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ''
        return (value.startswith('https://') and parsed.scheme == 'https'
                and parsed.username is None and parsed.password is None
                and parsed.port is None and parsed.netloc.lower() == host
                and not parsed.fragment and '#' not in value
                and re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?', host) is not None
                and '.' in host and '..' not in host
                and not all(c.isdigit() or c == '.' for c in host))
    except ValueError:
        return False


def number(value):
    return isinstance(value, (int, Decimal)) and not isinstance(value, bool) and Decimal(value).is_finite()


def validate_record(record):
    require(isinstance(record, dict) and record.get('schema') == RECORD_SCHEMA, 'document')
    require(isinstance(record.get('id'), str)
            and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,127}', record['id']) is not None, 'metadata')
    for key, maximum in [('name', 100), ('site', 160), ('provenance', 1000), ('limitations', 2000)]:
        require(text(record.get(key), maximum), 'metadata')
    aliases = record.get('aliases')
    require(isinstance(aliases, list) and len(aliases) <= 20
            and all(text(alias, 100) for alias in aliases)
            and len(set(aliases)) == len(aliases), 'metadata')
    category = record.get('category')
    require(category in ('fictional-demo', 'source-linked-draft'), 'category')
    require('sourceURL' in record, 'source-url')
    require(record['sourceURL'] is None if category == 'fictional-demo'
            else source_url(record['sourceURL']), 'source-url')
    profile = record.get('profile')
    require(isinstance(profile, list) and 2 <= len(profile) <= 256, 'profile')
    previous = -1
    maximum_depth = Decimal(0)
    for point in profile:
        require(isinstance(point, dict), 'profile')
        seconds = point.get('elapsedSeconds')
        depth = point.get('depthMeters')
        require(number(seconds), 'profile')
        require(Decimal(seconds) == Decimal(seconds).to_integral_value(), 'time-precision')
        require(previous < seconds <= 18_000 and seconds >= 0, 'profile')
        require(number(depth) and 0 <= depth <= Decimal('152.4'), 'profile')
        require(Decimal(depth) == Decimal(depth).quantize(Decimal('0.000001')), 'depth-precision')
        previous = seconds
        maximum_depth = max(maximum_depth, depth)
    require(profile[0]['elapsedSeconds'] == 0 and profile[0]['depthMeters'] == 0
            and profile[-1]['depthMeters'] > 0 and maximum_depth >= Decimal('0.3048'), 'profile')
    return record


def validate_document(document):
    require(isinstance(document, dict) and document.get('schema') == CATALOG_SCHEMA, 'document')
    routes = document.get('routes')
    require(isinstance(routes, list) and 1 <= len(routes) <= 500, 'document')
    for record in routes:
        validate_record(record)
    require(len({r['id'] for r in routes}) == len(routes), 'document')
    return document


def unique_object(pairs):
    # Keys are already JSON-unescaped here; reject ambiguity before dict collapse.
    result = {}
    for key, value in pairs:
        require(key not in result, 'document')
        result[key] = value
    return result


def decode_document(payload):
    require(len(payload) <= MAX_PAYLOAD_BYTES, 'document')
    try:
        document = json.loads(payload, parse_float=Decimal, object_pairs_hook=unique_object,
                              parse_constant=lambda _: (_ for _ in ()).throw(ContractError('profile')))
    except (ValueError, UnicodeError) as error:
        if isinstance(error, ContractError):
            raise
        raise ContractError('document') from error
    return validate_document(document)


def canonical_decimal(value):
    return format(Decimal(value).normalize(), 'f') if value else '0'


def checksum(record):
    validate_record(record)
    fields = [RECORD_SCHEMA, record['id'], record['name'], str(len(record['aliases'])),
              *record['aliases'], record['site'], record['provenance'], record['sourceURL'] or '',
              record['limitations'], record['category'], str(len(record['profile']))]
    for point in record['profile']:
        fields += [str(int(point['elapsedSeconds'])), canonical_decimal(point['depthMeters'])]
    data = b''.join(str(len(value.encode('utf-8'))).encode() + b':' + value.encode('utf-8') for value in fields)
    return hashlib.sha256(data).hexdigest()


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: validate_catalog.py INPUT_JSON')
    try:
        document = decode_document(Path(sys.argv[1]).read_bytes())
    except (OSError, ContractError) as error:
        raise SystemExit(f'Catalog rejected: {error}') from error
    print(f'Validated {len(document["routes"])} unreviewed route records ({CATALOG_SCHEMA})')


if __name__ == '__main__':
    main()
