import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from validate_catalog import ContractError, checksum, decode_document
from migrate_catalog import migrate

ROOT = Path(__file__).resolve().parents[1]


class SignCatalogTests(unittest.TestCase):
    def test_migration_is_exact_bounded_and_unsigned(self):
        original = (ROOT / 'catalog-v1.json').read_bytes()
        migrated = decode_document(migrate(original))
        self.assertEqual(len(migrated['routes']), 7)
        self.assertEqual(checksum(migrated['routes'][0]),
                         '4166d52acecf66f6ea93c56f7e95e46b46a902edbc3743b8dc816c1fc6bb2581')
        self.assertEqual(migrated['routes'][0]['category'], 'fictional-demo')
        self.assertTrue(all(r['category'] == 'source-linked-draft' for r in migrated['routes'][1:]))
        with self.assertRaises(ContractError):
            migrate(original + b'\n')

    def test_shared_golden_contract(self):
        fixtures = json.loads((ROOT / 'contract/route-record-v2-fixtures.json').read_text())
        for case in fixtures['cases']:
            with self.subTest(case=case['name']):
                payload = case['payload'].encode()
                if case['valid']:
                    document = decode_document(payload)
                    self.assertEqual([checksum(r) for r in document['routes']], case['checksums'])
                else:
                    with self.assertRaisesRegex(ContractError, '^' + case['error'] + '$'):
                        decode_document(payload)

    def test_nonfinite_and_oversized_payloads_fail(self):
        for payload in [b'{"schema": NaN}', b' ' * 700_001]:
            with self.assertRaises(ContractError):
                decode_document(payload)

    def test_invalid_metadata_stops_before_signing(self):
        document = json.loads((ROOT / 'catalog-v1.json').read_text())
        document['routes'][0]['provenance'] = ''
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            source = tmp / 'invalid.json'
            source.write_text(json.dumps(document))
            marker = tmp / 'crypto-called'
            stub = tmp / 'openssl'
            stub.write_text('#!/bin/sh\ntouch "$CRYPTO_MARKER"\nexit 0\n')
            stub.chmod(0o700)
            output = tmp / 'signed.json'
            env = {**os.environ, 'PATH': f'{tmp}:' + os.environ['PATH'], 'CRYPTO_MARKER': str(marker)}
            result = subprocess.run(
                ['/bin/zsh', '-f', str(ROOT / 'tools/sign_catalog.sh'), str(source), str(tmp / 'unused-key'), str(output)],
                env=env, capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(marker.exists(), 'Invalid metadata reached cryptographic signing')
            self.assertFalse(output.exists(), 'Invalid metadata created an output envelope')

    def test_invalid_v2_samples_stop_before_signing(self):
        fixtures = json.loads((ROOT / 'contract/route-record-v2-fixtures.json').read_text())
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            marker = tmp / 'crypto-called'
            stub = tmp / 'openssl'
            stub.write_text('#!/bin/sh\ntouch "$CRYPTO_MARKER"\nexit 91\n')
            stub.chmod(0o700)
            env = {**os.environ, 'PATH': f'{tmp}:' + os.environ['PATH'], 'CRYPTO_MARKER': str(marker)}
            for case in fixtures['cases']:
                if case['valid']:
                    continue
                with self.subTest(case=case['name']):
                    source = tmp / 'invalid.json'
                    source.write_text(case['payload'])
                    output = tmp / 'signed.json'
                    result = subprocess.run(
                        ['/bin/zsh', '-f', str(ROOT / 'tools/sign_catalog.sh'), str(source),
                         str(tmp / 'unused-key'), str(output)], env=env, capture_output=True, text=True,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('Catalog rejected:', result.stderr)
                    self.assertFalse(marker.exists())
                    self.assertFalse(output.exists())

    def test_valid_snapshot_is_signed_with_disposable_key(self):
        import base64
        fixture = json.loads((ROOT / 'contract/route-record-v2-fixtures.json').read_text())['cases'][0]
        with tempfile.TemporaryDirectory() as name:
            tmp = Path(name)
            source, key, public, envelope = [tmp / n for n in ['input.json', 'test.pem', 'public.pem', 'signed.json']]
            source.write_text(fixture['payload'])
            subprocess.run(['openssl', 'genpkey', '-algorithm', 'Ed25519', '-out', str(key)], check=True,
                           capture_output=True)
            subprocess.run(['/bin/zsh', '-f', str(ROOT / 'tools/sign_catalog.sh'), str(source), str(key), str(envelope)],
                           check=True, capture_output=True)
            signed = json.loads(envelope.read_text())
            self.assertEqual(signed['algorithm'], 'Ed25519')
            self.assertEqual(base64.b64decode(signed['payload']), source.read_bytes())
            signature = tmp / 'signature'
            signature.write_bytes(base64.b64decode(signed['signature']))
            subprocess.run(['openssl', 'pkey', '-in', str(key), '-pubout', '-out', str(public)], check=True,
                           capture_output=True)
            subprocess.run(['openssl', 'pkeyutl', '-verify', '-rawin', '-pubin', '-inkey', str(public),
                            '-in', str(source), '-sigfile', str(signature)], check=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
