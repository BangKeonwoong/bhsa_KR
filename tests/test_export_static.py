from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.export_static import export_static


class ExportStaticTest(unittest.TestCase):
    def test_export_static_creates_core_files(self):
        with TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "dist"
            export_static(out_dir, books_filter={"genesis"}, max_chapters=1)

            manifest_path = out_dir / "data" / "manifest.json"
            books_path = out_dir / "data" / "books.json"
            chapters_path = out_dir / "data" / "books-chapters.json"
            self.assertTrue(manifest_path.exists())
            self.assertTrue(books_path.exists())
            self.assertTrue(chapters_path.exists())

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["mode"], "static")
            self.assertTrue(manifest["capabilities"]["embedded_node_details"])
            self.assertIn("genesis", manifest["availability"])

            self.assertTrue((out_dir / "data" / "tree" / "ctt" / "genesis" / "1-lite.json").exists())
            self.assertTrue((out_dir / "data" / "tree" / "ctt" / "genesis" / "1-full.json").exists())
            self.assertTrue((out_dir / "data" / "versions" / "knt" / "genesis" / "1.json").exists())
            self.assertTrue((out_dir / "literal-index.json").exists())

            literal_index = json.loads((out_dir / "literal-index.json").read_text(encoding="utf-8"))
            self.assertEqual(literal_index["meta"]["book_count"], 39)
            self.assertIn("Genesis", literal_index["books"])
            self.assertIn("1", literal_index["books"]["Genesis"])
            self.assertIn("1", literal_index["books"]["Genesis"]["1"])
            first_clause = literal_index["books"]["Genesis"]["1"]["1"][0]
            self.assertEqual(first_clause["clauseType"], "xQtX")
            self.assertEqual(first_clause["koreanLiteral"], "태초에 하나님이 하늘들과 땅을 이미 창조하셨다")

    def test_static_assets_use_relative_docs_paths(self):
        with TemporaryDirectory() as tmp_dir:
            out_dir = Path(tmp_dir) / "dist"
            export_static(out_dir, books_filter={"genesis"}, max_chapters=1)

            index_html = (out_dir / "index.html").read_text(encoding="utf-8")
            api_docs_html = (out_dir / "api-docs.html").read_text(encoding="utf-8")
            data_client_js = (out_dir / "data-client.js").read_text(encoding="utf-8")

            self.assertIn("./api-docs.html", index_html)
            self.assertIn('spec-url="./openapi.yaml"', api_docs_html)
            self.assertIn("new URL('./api/tree'", data_client_js)


if __name__ == "__main__":
    unittest.main()
