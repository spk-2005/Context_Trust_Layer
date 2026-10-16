import io
import sys
from pathlib import Path
import pypdf

# Add backend to sys.path
sys.path.insert(0, 'B:/Context_Layer_Ai/backend')

from app.ingestion.universal_file_parser import UniversalFileParser

pdf_path = Path('B:/Context_Layer_Ai/docs/SAMPLE LETTER.pdf')
raw_bytes = pdf_path.read_bytes()

parsed = UniversalFileParser.parse_structured(
    filename='SAMPLE LETTER.pdf',
    raw_bytes=raw_bytes,
    doc_title='Sample Appointment Letter'
)

print(f'Parsed Title: {parsed.title}')
print(f'Extraction Quality: {parsed.extraction_quality}')
print(f'Is Scanned: {parsed.is_scanned}')
print(f'Page Count: {len(parsed.pages)}')
print(f'Total Block Count: {len(parsed.blocks)}')
print(f'Full Text Length: {len(parsed.full_text)}')
print(f'Warnings: {parsed.warnings}')

for i, p in enumerate(parsed.pages):
    print(f'Page {p.page_number}: chars={p.char_count}, scanned={p.is_scanned_image}, blocks={len(p.blocks)}')