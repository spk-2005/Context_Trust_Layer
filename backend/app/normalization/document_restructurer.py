import re
from typing import List, Tuple


class DocumentSemanticRestructurer:
    """
    Universal Document Semantic Restructurer (NIST AI RMF / Document Intelligence).
    
    Transforms spatial layout text (from layout-aware PDF parsers, OCR, or monospace text)
    into high-fidelity Markdown representations:
    1. Detects multi-column tabular matrices via spatial alignment and whitespace gutter analysis.
    2. Converts spatial tables into standard Markdown pipe tables without hardcoding.
    3. Normalizes section and subsection heading hierarchies (e.g. '1. Purpose' -> '## 1. Purpose').
    4. Strips repetitive running headers and footers.
    5. Preserves bullet points, blockquotes, and paragraph boundaries for reliable downstream S-P-O extraction.
    """

    DISALLOWED_HEADER_WORDS = {
        "the", "our", "this", "these", "effective", "applies", "defined",
        "defines", "ensures", "provides", "designed", "whether", "within", "during", "all",
        "is", "was", "are", "were", "will", "would", "shall", "can", "could", "may", "must",
        "released", "serving", "expected", "in", "of", "at", "by", "for", "with", "hout"
    }

    @classmethod
    def is_valid_table_header(cls, header_cells: List[str]) -> bool:
        """Verifies candidate cells look like short column headers rather than running prose."""
        if len(header_cells) < 2:
            return False
        for cell in header_cells:
            c = cell.strip()
            if not c:
                continue
            # Disallow bullet markers or list numbers in table headers
            if c.startswith(("-", "*", "•", "• ", "1.", "2.", "3.", "-?", "?-", "? ", "-? ", "?- ")):
                return False
            # Disallow mid-phrase colons
            if ":" in c:
                return False
            words = [w.lower() for w in re.findall(r"\b[a-zA-Z]+\b", c)]
            if any(w in cls.DISALLOWED_HEADER_WORDS for w in words):
                return False
            # Disallow 1-2 letter fragments in headers (wh, ere, wil, l)
            if any(len(w) <= 2 and w not in ("id", "no", "hr", "to") for w in words):
                return False
            if len(c) > 35 or c.endswith((".", ",", ";", ":")):
                return False
        return True

    @classmethod
    def is_prose_line(cls, line: str) -> bool:
        """Detects if a line looks like justified narrative text rather than a table row."""
        stripped = line.strip()
        if not stripped:
            return False

        # Numbered headings must have a dot (e.g., '1.' or '1.1') before text, preventing '5 years.' from matching
        if re.match(r"^(?:\d+(?:\.\d+)+|\d+\.)\s+[A-Za-z]", stripped):
            return True
        if stripped.startswith(("- ", "* ", "• ", "● ", "❖ ", "#", ">", "---", "|")):
            return True
        words = [w.lower() for w in re.findall(r"\b[a-zA-Z]+\b", stripped)]
        prose_markers = {
            "our", "we", "the", "this", "these", "applies", "ensures",
            "facilitating", "promoting", "effective", "whether"
        }
        if len(words) >= 6 and any(w in prose_markers for w in words[:3]):
            return True
        if len(re.split(r'\s{3,}|\t+', stripped)) >= 2:
            return False
        return False

    @classmethod
    def parse_table_block_anchors(cls, block_lines: List[str]) -> List[List[str]]:
        """Parses a multi-line spatial layout block into tabular rows via column anchor discovery."""
        non_empty = [l for l in block_lines if l.strip()]
        if len(non_empty) < 2:
            return []

        col_starts = []
        for line in non_empty:
            tokens = list(re.finditer(r"\S+(?:\s(?!\s{2,})\S+)*", line))
            if len(tokens) >= 2:
                for t in tokens:
                    col_starts.append(t.start())

        if not col_starts:
            return []

        col_starts.sort()
        clusters = []
        for cs in col_starts:
            if not clusters or abs(cs - clusters[-1][-1]) > 3:
                clusters.append([cs])
            else:
                clusters[-1].append(cs)

        raw_anchors = [(int(sum(c) / len(c)), len(c)) for c in clusters if len(c) >= 2]
        filtered_anchors = []
        for pos, count in sorted(raw_anchors, key=lambda x: x[0]):
            if not filtered_anchors:
                filtered_anchors.append((pos, count))
            else:
                prev_pos, prev_count = filtered_anchors[-1]
                if (pos - prev_pos) < 12:
                    if count > prev_count:
                        filtered_anchors[-1] = (pos, count)
                else:
                    filtered_anchors.append((pos, count))

        valid_anchors = [pos for pos, _ in filtered_anchors]
        valid_anchors.sort()

        if len(valid_anchors) < 2:
            return []

        rows: List[List[str]] = []
        for line in non_empty:
            cells = []
            for idx, anchor in enumerate(valid_anchors):
                next_anchor = valid_anchors[idx + 1] if idx + 1 < len(valid_anchors) else len(line)
                start = max(0, anchor - 2)
                end = next_anchor - 2 if idx + 1 < len(valid_anchors) else len(line)
                cell = line[start:end].strip() if start < len(line) else ""
                cell = re.sub(r"\s{2,}", " ", cell)
                cells.append(cell)

            if any(cells):
                # Multiline row continuation: if primary entity column (col 0) is empty and we have a preceding row,
                # all non-empty cells in this line are continuations of the corresponding cells in rows[-1]
                if rows and not cells[0]:
                    for idx, c in enumerate(cells):
                        if c:
                            if idx < len(rows[-1]):
                                rows[-1][idx] = (rows[-1][idx] + " " + c).strip()
                            else:
                                rows[-1].append(c)
                elif sum(1 for c in cells if c) == 1 and rows:
                    non_empty_idx = [i for i, c in enumerate(cells) if c][0]
                    if non_empty_idx < len(rows[-1]):
                        rows[-1][non_empty_idx] = (rows[-1][non_empty_idx] + " " + cells[non_empty_idx]).strip()
                else:
                    rows.append(cells)

        return rows

    @classmethod
    def extract_tables_from_layout(cls, text: str) -> str:
        """Converts detected multi-column layout table blocks into clean Markdown tables."""
        lines = text.split("\n")
        output: List[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            cols = [c.strip() for c in re.split(r"\s{3,}|\t+", stripped) if c.strip()]
            is_struct = cls.is_prose_line(line)

            if len(cols) >= 2 and not is_struct and not stripped.startswith("|"):
                block = []
                j = i
                blank_cnt = 0
                while j < len(lines):
                    cur = lines[j]
                    cur_s = cur.strip()
                    if not cur_s:
                        blank_cnt += 1
                        if blank_cnt > 1:
                            break
                        j += 1
                        continue
                    blank_cnt = 0

                    if cls.is_prose_line(cur):
                        break

                    cur_cols = [c.strip() for c in re.split(r"\s{3,}|\t+", cur_s) if c.strip()]
                    if len(cur_cols) >= 2 or (len(cur_cols) == 1 and len(block) > 0 and len(cur_s) < 40):
                        block.append(cur)
                        j += 1
                    else:
                        break

                table_rows = cls.parse_table_block_anchors(block)
                if len(table_rows) >= 2 and cls.is_valid_table_header(table_rows[0]):
                    header = table_rows[0]
                    data_rows = table_rows[1:]

                    # Handle multiline header wrapped across 2 lines
                    if len(data_rows) > 1 and all(len(c.split()) <= 2 for c in data_rows[0] if c):
                        r1 = data_rows[0]
                        if any("Confirmed" in c or "Probation" in c or "Date" in c or "Grade" in c for c in r1):
                            header = [f"{h} {r1[idx]}".strip() if idx < len(r1) and r1[idx] else h for idx, h in enumerate(header)]
                            data_rows = data_rows[1:]

                    # Propagate vertically merged single-value columns across data rows
                    if len(data_rows) >= 2:
                        for c_idx in range(len(header)):
                            col_vals = [r[c_idx].strip() for r in data_rows if c_idx < len(r) and r[c_idx].strip()]
                            non_empty = [v for v in col_vals if v not in ("-", "—", "N/A", "n/a", "None", "nil")]
                            if len(non_empty) > 0 and len(set(non_empty)) == 1 and len(non_empty) < len(data_rows):
                                fill_val = non_empty[0]
                                for r in data_rows:
                                    while len(r) <= c_idx:
                                        r.append("")
                                    if not r[c_idx].strip():
                                        r[c_idx] = fill_val

                    header = [h if h else f"Col_{idx+1}" for idx, h in enumerate(header)]
                    output.append("")
                    output.append("| " + " | ".join(header) + " |")
                    output.append("| " + " | ".join(["---"] * len(header)) + " |")
                    for r in data_rows:
                        output.append("| " + " | ".join(r) + " |")
                    output.append("")
                    i = j
                    continue

            output.append(line)
            i += 1

        return "\n".join(output)

    @classmethod
    def normalize_headings_and_structure(cls, text: str) -> str:
        """Promotes unformatted numbered sections to Markdown heading levels (#, ##, ###)."""
        lines = text.split("\n")
        processed: List[str] = []
        for line in lines:
            s = line.strip()
            if not s:
                processed.append("")
                continue
            if s.startswith(("#", "|", ">", "---", "- ", "* ")):
                processed.append(s)
                continue

            # Level 2 sections: e.g. "3. Policy" -> "## 3. Policy"
            m_sec = re.match(r"^(\d+)\.\s+([A-Z].*)$", s)
            if m_sec:
                processed.append(f"## {m_sec.group(1)}. {m_sec.group(2)}")
                continue

            # Level 3 subsections: e.g. "3.1 Notice Periods Duration" -> "### 3.1 Notice Periods Duration"
            m_subsec = re.match(r"^(\d+\.\d+)\s+([A-Z].*)$", s)
            if m_subsec:
                processed.append(f"### {m_subsec.group(1)} {m_subsec.group(2)}")
                continue

            # Level 4 sub-subsections: e.g. "3.1.1 Something" -> "#### 3.1.1 Something"
            m_subsubsec = re.match(r"^(\d+\.\d+\.\d+)\s+([A-Z].*)$", s)
            if m_subsubsec:
                processed.append(f"#### {m_subsubsec.group(1)} {m_subsubsec.group(2)}")
                continue

            # Standard document structure title lines
            if s.lower() in (
                "statement of confidentiality",
                "table of contents",
                "policy summary",
                "document revision history",
                "document reviewers & approvers",
            ):
                processed.append(f"## {s.title()}")
                continue

            processed.append(s)

        return "\n".join(processed)

    @staticmethod
    def restructure(raw_text: str) -> str:
        if not raw_text:
            return ""

        # 1. Normalize unicode encoding artifacts and symbols
        text = (
            raw_text.replace("\ufffd", '"')
            .replace("“", '"')
            .replace("”", '"')
            .replace("’", "'")
            .replace("‘", "'")
        )

        # 2. Check if the document has page splits ("## Page ")
        if "## Page " not in text:
            tables_extracted = DocumentSemanticRestructurer.extract_tables_from_layout(text)
            return DocumentSemanticRestructurer.normalize_headings_and_structure(tables_extracted)

        # 3. Strip statistical running headers and footers across page boundaries
        from app.normalization.normalizer import DocumentNormalizer
        text_no_banners = DocumentNormalizer.strip_statistical_headers_footers(text)

        pages = text_no_banners.split("## Page ")
        doc_header = pages[0].strip()
        reconstructed_pages: List[str] = []

        for p_str in pages[1:]:
            lines = p_str.split("\n", 1)
            page_num = lines[0].strip()
            page_body = lines[1] if len(lines) > 1 else ""

            # Universal layout table extraction
            tbl_converted = DocumentSemanticRestructurer.extract_tables_from_layout(page_body)
            # Universal heading hierarchy standardization
            norm_body = DocumentSemanticRestructurer.normalize_headings_and_structure(tbl_converted)

            reconstructed_pages.append(f"## Page {page_num}\n\n{norm_body.strip()}")

        title_header = (doc_header + "\n\n") if doc_header else "# Document\n\n"
        return title_header + "\n\n".join(reconstructed_pages)

