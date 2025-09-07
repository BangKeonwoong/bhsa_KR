from __future__ import annotations
import json
import unittest

from ctt_viewer import create_app


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
