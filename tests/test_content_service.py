from __future__ import annotations

import unittest

from parser.content_service import (
    build_books_chapters_data,
    build_books_data,
    build_capabilities_data,
    build_tree_data,
    build_version_chapter_data,
)


def _find_first_tokenized(node):
    if not node:
        return None
    if isinstance(node, dict) and node.get("tokens"):
        return node
    for child in (node.get("children") or []):
        found = _find_first_tokenized(child)
        if found:
            return found
    return None


class ContentServiceTest(unittest.TestCase):
    def test_build_books_data_contains_genesis(self):
        books = build_books_data()
        self.assertIsInstance(books, list)
        self.assertTrue(any(item.get("code") == "GEN" and item.get("book") == "genesis" for item in books))

    def test_build_books_chapters_data_contains_genesis(self):
        items = build_books_chapters_data()
        genesis = next((item for item in items if item.get("code") == "GEN"), None)
        self.assertIsNotNone(genesis)
        self.assertGreaterEqual(genesis.get("chapters", 0), 1)

    def test_build_capabilities_data_shape(self):
        capabilities = build_capabilities_data()
        self.assertIn("has_local_bhsa", capabilities)
        self.assertIn("has_gloss", capabilities)
        self.assertIn("ready", capabilities)
        self.assertIn("warming", capabilities)
        self.assertIn("phase", capabilities)
        self.assertIn("message", capabilities)

    def test_build_tree_data_ctt_lite_and_full(self):
        lite_tree = build_tree_data("genesis", 1, "ctt", True)
        full_tree = build_tree_data("genesis", 1, "ctt", False)
        self.assertEqual(lite_tree.get("source"), "ctt")
        self.assertEqual(full_tree.get("source"), "ctt")
        self.assertIsNone(_find_first_tokenized(lite_tree))
        self.assertIsNotNone(_find_first_tokenized(full_tree))

    def test_build_version_chapter_data_knt(self):
        chapter = build_version_chapter_data("knt", "genesis", 1)
        self.assertIsNotNone(chapter)
        self.assertEqual(chapter["version"], "knt")
        self.assertEqual(chapter["book_label"], "GEN")
        self.assertIsInstance(chapter["verses"], list)
        self.assertTrue(chapter["verses"])


if __name__ == "__main__":
    unittest.main()
