from __future__ import annotations
import json
import unittest

from ctt_viewer import create_app
import os
from importlib import reload
import ctt_viewer.config as config_mod


class AppRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_index(self):
        rv = self.client.get('/')
        self.assertEqual(rv.status_code, 200)
        self.assertIn('text/html', rv.content_type)

    def test_healthz(self):
        rv = self.client.get('/healthz')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertEqual(data.get('status'), 'ok')
        # Request ID header propagated
        self.assertTrue(rv.headers.get('X-Request-ID'))

    def test_books(self):
        rv = self.client.get('/api/books')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertIsInstance(data, list)
        self.assertTrue(any(item.get('code') == 'GEN' for item in data))

    def test_books_chapters(self):
        rv = self.client.get('/api/books/chapters')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertIsInstance(data, list)
        gen = next((x for x in data if x.get('code') == 'GEN'), None)
        self.assertIsNotNone(gen)
        self.assertGreaterEqual(gen.get('chapters', 0), 1)

    def test_tf_status(self):
        rv = self.client.get('/api/tf/status')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertIn('has_local_bhsa', data)
        self.assertIn('has_gloss', data)

    def test_version(self):
        rv = self.client.get('/api/version')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertIn('version', data)

    def test_json_gzip_compression(self):
        # 새 앱을 만들어 압축 설정을 강제
        os.environ['ENABLE_COMPRESSION'] = '1'
        os.environ['COMPRESS_MIN_SIZE'] = '1'
        # BaseConfig는 import 시 환경을 읽지만, apply_env_overrides가 런타임에 반영함
        app2 = create_app()
        client2 = app2.test_client()
        rv = client2.get('/api/types?source=ctt', headers={'Accept-Encoding': 'gzip'})
        self.assertEqual(rv.status_code, 200)
        enc = rv.headers.get('Content-Encoding', '')
        self.assertEqual(enc, 'gzip')

    def test_weak_etag_for_compressed_and_304(self):
        import os as _os
        _os.environ['ENABLE_COMPRESSION'] = '1'
        _os.environ['COMPRESS_MIN_SIZE'] = '1'
        _os.environ['WEAK_ETAG_FOR_COMPRESSED'] = '1'
        app3 = create_app()
        c3 = app3.test_client()
        # First request to get weak ETag
        rv1 = c3.get('/api/types?source=ctt', headers={'Accept-Encoding':'gzip'})
        self.assertEqual(rv1.status_code, 200)
        enc1 = rv1.headers.get('Content-Encoding','')
        self.assertEqual(enc1, 'gzip')
        et1 = rv1.headers.get('ETag','')
        self.assertTrue(et1.startswith('W/'))
        # Second request with If-None-Match should return 304
        rv2 = c3.get('/api/types?source=ctt', headers={'Accept-Encoding':'gzip','If-None-Match': et1})
        self.assertEqual(rv2.status_code, 304)
        vary = rv1.headers.get('Vary', '')
        self.assertIn('Accept-Encoding', vary)

    def test_nocache_query_bypasses_304_and_sets_ttl_zero(self):
        # First: warm ETag
        app = create_app()
        c = app.test_client()
        rv1 = c.get('/api/types?source=ctt')
        self.assertEqual(rv1.status_code, 200)
        et = rv1.headers.get('ETag','')
        self.assertTrue(et)
        # With If-None-Match normally 304
        rv2 = c.get('/api/types?source=ctt', headers={'If-None-Match': et})
        self.assertEqual(rv2.status_code, 304)
        # With nocache=1 should return 200 and max-age=0
        rv3 = c.get('/api/types?source=ctt&nocache=1', headers={'If-None-Match': et})
        self.assertEqual(rv3.status_code, 200)
        cc = rv3.headers.get('Cache-Control','')
        self.assertIn('max-age=0', cc)

    def test_openapi_yaml(self):
        rv = self.client.get('/openapi.yaml')
        self.assertEqual(rv.status_code, 200)
        text = rv.get_data(as_text=True)
        self.assertIn('openapi: 3.0', text)

    def test_api_docs(self):
        rv = self.client.get('/api/docs')
        self.assertEqual(rv.status_code, 200)
        self.assertIn('text/html', rv.content_type)

    def test_gloss_status(self):
        rv = self.client.get('/api/gloss/status')
        self.assertEqual(rv.status_code, 200)
        # JSON parse to ensure valid payload with etag path
        _ = json.loads(rv.get_data(as_text=True))

    def test_tree_ctt_genesis_1(self):
        # Use CTT source to avoid TF dependency
        rv = self.client.get('/api/tree?book=genesis&chapter=1&source=ctt&lite=1')
        self.assertEqual(rv.status_code, 200)
        data = rv.get_json()
        self.assertEqual(data.get('source'), 'ctt')
        self.assertIsInstance(data.get('children'), list)
        self.assertGreater(len(data.get('children')), 0)
        # Lite 모드 캐시 max-age 기본값(600) 확인
        cc = rv.headers.get('Cache-Control', '')
        self.assertIn('max-age=600', cc)

    def test_tree_ctt_full_cache_ttl(self):
        rv = self.client.get('/api/tree?book=genesis&chapter=1&source=ctt&lite=0')
        self.assertEqual(rv.status_code, 200)
        cc = rv.headers.get('Cache-Control', '')
        # 상세 모드 기본 TTL(120)
        self.assertIn('max-age=120', cc)

    def test_404_json(self):
        rv = self.client.get('/no-such-path-xyz')
        self.assertEqual(rv.status_code, 404)
        self.assertIn('application/json', rv.content_type)
        data = rv.get_json()
        self.assertEqual(data.get('error'), 'not_found')

    def test_405_json(self):
        rv = self.client.post('/api/books')  # only GET allowed
        self.assertEqual(rv.status_code, 405)
        data = rv.get_json()
        self.assertEqual(data.get('error'), 'method_not_allowed')


if __name__ == '__main__':
    unittest.main()
