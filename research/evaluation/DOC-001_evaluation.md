# Evaluation Benchmark: DOC-001 (Resignation and Voluntary Termination Policy)

## 1. Run Summary
- **Document Code:** DOC-001
- **Source File:** `docs/Resignation and Voluntary Termination.pdf` (135,289 bytes)
- **Pipeline Invocation:** `POST /v1/documents/upload-and-extract`
- **Document ID:** `62d78dfa-4795-4496-8014-945a428bc9a8`
- **Execution Duration:** 2,549 ms
- **Raw Claims Extracted:** 65
- **Layer 6 Gate Outcome:** 
  - Approved / Verified: 29
  - Queued for Review: 1
  - Rejected: 35
  - Average Trust Score: 0.5435
- **Conflicts Detected:** 11 (including temporal revision history clashing)
- **Output Artifact:** `research/extraction-results/DOC-001_output.json`

---

## 2. Benchmark & Issue Tracking Table

| Document | Extracted Triple / Issue | Ground-Truth Original Clause | Observed Behavior | Expected Behavior | Category |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DOC-001** | `Staff` -> `not` -> `use vacation or compensatory time to extend notice` | *"Staff may not use vacation or compensatory time to extend the notice period."* | **Approved** (Conf: High) | **Accept** | Clean Rule Extraction |
| **DOC-001** | `Supervisors` -> `contact` -> `Office of HR on receiving request to rescind` | *"Supervisors should contact the Office of Human Resources upon receiving a request to rescind a resignation."* | **Approved** (Conf: High) | **Accept** | Clean Rule Extraction |
| **DOC-001** | `Longer periods` -> `has_validity_rule` -> `negotiated at dept discretion` | *"Longer periods may be appropriate for certain positions, and alternative notice arrangements may be negotiated..."* | **Approved** | **Accept** | Clean Rule Extraction |
| **DOC-001** | `Subject: 'Page 1'` -> `A minimum two-week written notice is standard for support positions` | *"A minimum two-week written notice is standard for support positions."* | **Rejected** (Generic subject 'Page 1' failed grounding check) | **Accept / Extract** with Subject: `"Support positions"` -> `minimum_notice` -> `2 weeks` | Subject Normalization Failure |
| **DOC-001** | `Subject: 'Page 1'` -> `A minimum four-week written notice is standard for A and P positions` | *"A minimum four-week written notice is standard for administrative and professional (A&P)..."* | **Rejected** (Generic subject 'Page 1' failed grounding check) | **Accept / Extract** with Subject: `"Administrative and Professional positions"` -> `minimum_notice` -> `4 weeks` | Subject Normalization Failure |
| **DOC-001** | `Subject: 'For procedural questions, contact the O Responsibilities'` -> `ffice of Human Resources .` | *"For procedural questions, contact the Office of Human Resources."* | **Approved (Verified)** as a valid claim | **Reject or Review** (Malformed split word fragment: `"O"` + `"ffice"`) | Multi-column Whitespace Splitting |
| **DOC-001** | `Subject: 'Position or Office Respons'` -> `ibilities` | *"Position or Office Responsibilities"* | **Approved (Verified)** as a valid claim | **Reject** (Header split fragment: `"Respons"` + `"ibilities"`) | Multi-column Whitespace Splitting |
| **DOC-001** | `Subject: '3'` -> `Return all college property.` | *"3. Return all college property."* (Item in checklist) | **Approved (Verified)** with Subject = `'3'` | **Flag for Review** (Subject should be `"Employee"`, not the bullet number `'3'`) | List Parsing Anomaly |
| **DOC-001** | `Subject: 'Supervisor 1'` -> `Acknowledge in writing receipt...` | *"Supervisor: 1. Acknowledge in writing receipt and acceptance..."* | **Approved (Verified)** with Subject = `'Supervisor 1'` | **Accept** with Subject cleanly normalized to `"Supervisor"` | List Parsing Anomaly |
| **DOC-001** | `Subject: 'Page 2'` -> `has_unmapped_table_cell` (disposition: EMPTY) | Blank cells in sign-off table | **Rejected** by Layer 6 Validation Gate | **Reject / Filter early** (skip non-assertive table blanks before claim stage) | Noise Clutter |
| **DOC-001** | Revision table date conflicts (`03/01/2009` vs `12/11/2013` vs `07/23/2021`) | Policy history table showing revision timestamps | 11 conflicts generated (`INCOMPATIBLE_NUMERIC_VALUE`) | **Filter / Temporal Chain** (Historical revision metadata should not flag active policy contradictions) | False-Positive Conflict Clashing |

---

## 3. Analysis & Key Takeaways

1. **Gate Defense Effectiveness:**
   - Layer 6 correctly rejected 35 malformed or ungrounded claims (such as empty table cell placeholders and generic `'Page 1'` claims).
   - However, because the extractor fell back to assigning `'Page 1'` as the subject for core policy rules (2-week and 4-week notice periods), those **critical governing rules were rejected** instead of being rescued.

2. **Column Layout Parser Sensitivity:**
   - Multi-column table boundaries in `universal_file_parser.py` caused word breaks across vertical whitespace (e.g., `"Office"` split into `"O"` and `"ffice"`).
   - These malformed fragments slipped through the verification gate because they possessed high lexical similarity to the raw text characters, even though syntactically nonsensical.

3. **Temporal Policy History Clashes:**
   - Document revision history tables triggered 11 numeric/date conflicts against each other. Version metadata should be isolated from operational policy assertions.
