import unittest
import uuid
from app.normalization.normalizer import DocumentNormalizer
from app.ingestion.document_ingestion import DocumentIngestionService


class TestDocumentNormalization(unittest.TestCase):
    def setUp(self):
        self.normalizer = DocumentNormalizer()

    def test_clean_text_unicode_and_whitespace(self):
        # Text with messy carriage returns, multiple spaces, tabs, and excess blank lines
        raw_text = "  Hello \t  World!  \r\n\r\n\r\n\r\nThis is   a test.   \n\nAnother line.  "
        cleaned = self.normalizer.clean_text(raw_text)

        self.assertNotIn("\r", cleaned)
        self.assertNotIn("   ", cleaned)
        self.assertEqual(
            cleaned,
            "Hello World!\n\nThis is a test.\n\nAnother line."
        )

    def test_parse_sections_with_markdown_headers(self):
        raw_text = (
            "# Section One\n"
            "This is the first paragraph.\n\n"
            "## Subsection 1.1\n"
            "Here is more detailed information.\n\n"
            "# Section Two\n"
            "Final conclusion."
        )
        normalized = self.normalizer.normalize(
            document_id=uuid.uuid4(),
            document_version_id=uuid.uuid4(),
            title="Policy Doc",
            raw_text=raw_text,
            extra_metadata={"category": "HR"}
        )

        self.assertEqual(len(normalized.sections), 3)
        self.assertEqual(normalized.sections[0].title, "Section One")
        self.assertEqual(normalized.sections[0].level, 1)
        self.assertIn("This is the first paragraph.", normalized.sections[0].content)

        self.assertEqual(normalized.sections[1].title, "Subsection 1.1")
        self.assertEqual(normalized.sections[1].level, 2)
        self.assertIn("Here is more detailed information.", normalized.sections[1].content)

        self.assertEqual(normalized.sections[2].title, "Section Two")
        self.assertEqual(normalized.sections[2].level, 1)
        self.assertIn("Final conclusion.", normalized.sections[2].content)

        self.assertGreater(normalized.total_characters, 0)
        self.assertGreater(normalized.total_words, 0)
        self.assertEqual(normalized.metadata["category"], "HR")

    def test_parse_sections_without_headers(self):
        raw_text = "Just a plain simple document with no markdown headers."
        sections = self.normalizer.parse_sections(raw_text)

        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].title, "General")
        self.assertEqual(sections[0].content, raw_text)
        self.assertEqual(sections[0].start_char_offset, 0)
        self.assertEqual(sections[0].end_char_offset, len(raw_text))

    def test_calculate_content_hash(self):
        content_a = "Some document content"
        content_b = "Some document content"
        content_c = "Different content"

        hash_a = DocumentIngestionService.calculate_hash(content_a)
        hash_b = DocumentIngestionService.calculate_hash(content_b)
        hash_c = DocumentIngestionService.calculate_hash(content_c)

        self.assertEqual(hash_a, hash_b)
        self.assertNotEqual(hash_a, hash_c)
        self.assertEqual(len(hash_a), 64)  # SHA-256 hex string length


if __name__ == "__main__":
    unittest.main()
