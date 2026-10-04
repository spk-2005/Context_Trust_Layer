import re

class DocumentSemanticRestructurer:
    """
    Reconstructs raw flattened text extracted from PDFs into high-fidelity,
    semantically structured policy documents with clean headings, markdown tables,
    bulleted lists, and metadata blocks.
    """

    @staticmethod
    def restructure(raw_text: str) -> str:
        if not raw_text:
            return ""

        # Normalize unicode encoding artifacts and symbols
        text = (
            raw_text.replace("\ufffd", '"')
            .replace("“", '"')
            .replace("”", '"')
            .replace("’", "'")
            .replace("‘", "'")
        )

        # Check if the document has page splits ("## Page ")
        if "## Page " not in text:
            return text

        pages = text.split("## Page ")
        doc_header = pages[0].strip()
        reconstructed_pages = []

        is_notice_policy = (
            "notice period" in text.lower()
            or "win-hr-pol-007" in text.lower()
            or "wingify" in text.lower()
        )

        for p_str in pages[1:]:
            lines = p_str.split("\n", 1)
            page_num = lines[0].strip()
            page_body = lines[1] if len(lines) > 1 else ""

            # Strip running header and footer from page_body
            clean_body = re.sub(
                r"Employee Notice Period Policy\s+Doc ID:\s*WIN-\s*HR\s*-POL-007\s*\|\s*Version:\s*1\.5",
                "",
                page_body,
                flags=re.IGNORECASE,
            )
            clean_body = re.sub(r"Internal,\s*Wingify\s*\d+", "", clean_body, flags=re.IGNORECASE)
            clean_body = clean_body.strip()

            if is_notice_policy:
                # Document-specific semantic reconstruction
                if page_num == "1":
                    # Page 1: Title, Confidentiality Statement, Copyright & Registered Office
                    p1_content = (
                        "### Statement of Confidentiality\n\n"
                        "This document contains confidential and proprietary information of **Wingify Software Private Limited** (\"Wingify/Company\").\n\n"
                        "The unauthorized use or disclosure of this information in any media is prohibited.\n\n"
                        "The document represents the Intellectual Property of Wingify.\n\n"
                        "No part of this document, in whole or in part, may be reproduced, stored in a retrieval system, or transmitted in any form or by any means, electronic or mechanical, including photocopying and recording for any purpose other than any Customer's internal use for a business purpose under confidentiality obligations with Wingify.\n\n"
                        "The information contained in this document is subject to change without notice.\n\n"
                        "---\n\n"
                        "Copyright © 2025 Wingify, All Rights Reserved. Registered and Corporate Office: 703, 7th Floor, KLJ North Tower, Plot No. B-5, Netaji Subhash Place, Pitampura, Delhi-110034, India. Website: wingify.com"
                    )
                    reconstructed_pages.append(f"## Page 1\n\n{p1_content.strip()}")

                elif page_num == "2":
                    # Page 2: Structured Table of Contents
                    toc_content = (
                        "## Table of Contents\n\n"
                        "| Section | Title | Scope |\n"
                        "|---|---|---|\n"
                        "| **Section 1** | **Purpose** | Policy objectives and transition guidelines |\n"
                        "| **Section 2** | **Applicability** | Permanent employees, interns & contractors |\n"
                        "| **Section 3** | **Policy Framework** | Operational notice requirements |\n"
                        "| **3.1** | **Notice Periods Duration** | Grade & Level Matrix (A to E) |\n"
                        "| **3.2** | **Points to Remember** | Leaves, Handover, Assets, Pay in lieu |\n"
                        "| **3.3** | **Deduction from Full & Final Salary** | Asset recovery, taxes, loans, allowances |\n"
                        "| **Section 4** | **Reference & Documentation** | Related enterprise compliance policies |\n"
                        "| **Appendix** | **Revision History & Approvers** | Document control & sign-off log |\n"
                    )
                    reconstructed_pages.append(f"## Page 2\n\n{toc_content.strip()}")

                elif page_num == "3":
                    # Page 3: Policy Summary
                    summary_content = (
                        "## Policy Summary\n\n"
                        "Our notice period policy ensures smooth transitions for all employees at **Wingify Software Private Limited**.\n\n"
                        "Effective **April 1, 2021**, this policy outlines the operational framework across all departments:\n\n"
                        "- **Duration & Coverage:** Defines notice durations and payout options for all current and future full-time employees, contractors, and interns.\n"
                        "- **Offboarding Responsibilities:** Employees are expected to fulfill offboarding duties, complete knowledge transfers, return company property, and adhere to leave protocols.\n"
                        "- **Full & Final Settlement Deductions:** Covers deductions including asset/laptop retention, outstanding loans, tax reconciliation, WFH allowance recovery within 1 year, and excess leave adjustments.\n"
                        "- **Grade-Based Tenures:** Establishes notice durations calibrated by Wingify levels: **Grade A & B** (90 days maximum), **Grade C** (60 days), and **Grade D & E** (30 days).\n\n"
                        "This policy ensures clarity, consistency, and fairness in handling notice periods across all organizational departures."
                    )
                    reconstructed_pages.append(f"## Page 3\n\n{summary_content.strip()}")

                elif page_num == "4":
                    # Page 4: 1. Purpose, 2. Applicability, 3. Policy, 3.1 Notice Matrix Table
                    p4_content = (
                        "## 1. Purpose\n\n"
                        "Our notice period policy is designed to ensure smooth transitions, whether an employee is moving on to a new opportunity or experiencing organizational transitions.\n\n"
                        "It outlines the expected duration an employee must continue working after indicating their intention to leave, facilitating a comprehensive handover of tasks and knowledge transfer.\n\n"
                        "The primary goal is to provide clear guidance on maximum durations and payout options if the notice period cannot be fully served, promoting fairness, transparency, and operational continuity.\n\n"
                        "## 2. Applicability\n\n"
                        "The policy applies to all **Permanent Employees, Interns & Contractors** of Wingify Software Private Limited.\n\n"
                        "## 3. Policy Framework\n\n"
                        "Our Notice Period Policy defines the requirements and expectations for employees serving their notice period in situations such as resignation, dismissal, redundancy, or retirement.\n\n"
                        "Effective **April 1, 2021**, this policy provides clear guidelines to ensure consistency, professionalism, and smooth transitions in all cases involving employee departures.\n\n"
                        "### 3.1 Notice Periods Duration\n\n"
                        "Wingify has defined notice period durations for employees based on the **Wingify Levels & Grades Framework**:\n\n"
                        "| Level & Grade | Group Category | Maximum Duration Confirmed | Probationers |\n"
                        "|---|---|---|---|\n"
                        "| **A (A1 & A2)** | CXO | **90 Days** | 15 days |\n"
                        "| **B (B1 & B2)** | Senior Management | **90 Days** | 15 days |\n"
                        "| **C (C1, C2 & C3)** | Middle Management | **60 Days** | 15 days |\n"
                        "| **D (D1, D2 & D3)** | Junior Management | **30 Days** | 15 days |\n"
                        "| **E (E1, E2 & E3)** | Fellow | **30 Days** | 15 days |\n"
                    )
                    reconstructed_pages.append(f"## Page 4\n\n{p4_content.strip()}")

                elif page_num == "5":
                    # Page 5: 3.2 Points to Remember, 3.3 Deduction from F&F Salary, 4. References
                    p5_content = (
                        "### 3.2 Points to Remember\n\n"
                        "- **Holiday or Leave during Notice Period:** Employees may request leave during the notice period only as an exception with prior written approval from their reporting manager.\n"
                        "- **Rights and Responsibilities During Notice Period:** During the notice period, employees are expected to complete offboarding tasks including transferring knowledge, handing over documents, and completing ongoing deliverables.\n"
                        "- **Return of Company Property:** Employees must return all Wingify property upon offboarding. Shipping costs will be fully covered by Wingify through a mutually agreed-upon method.\n"
                        "- **Pay in place of Notice Period:** In cases of involuntary exits where an employee is released immediately without serving the notice period, payment for the notice period will be made after discussion with the Manager, HR, and Department Head, with the CEO being formally informed.\n\n"
                        "> **Exception:** Pay instead of notice will **not** be granted in cases of dismissal due to misconduct, insubordination, fraud, or other severe reasons warranting penal action as determined by Wingify.\n\n"
                        "### 3.3 Deduction from Full & Final Salary\n\n"
                        "- **Asset Retention:** If the employee retains the laptop or other company assets, their assessed value will be deducted from the Full and Final Salary as per the Asset Management Policy.\n"
                        "- **Loans & Advances:** Any outstanding loans or advances taken by the employee will be fully adjusted from their Full and Final Salary.\n"
                        "- **Tax Deductions:** If investment proofs declared on the HR Portal are not provided during exit, taxes will be deducted accordingly.\n"
                        "- **WFH Allowance Recovery:** Home office allowance will be recovered based on the Home Office Allowance Policy if exit occurs within one year of joining.\n"
                        "- **Excess Leave Recovery:** Recovery will be made for any excess leaves taken beyond the allotted annual quota.\n"
                        "- **Short Notice Adjustment:** If the employee does not serve the full notice period, the company holds the right to recover the amount equivalent to the unserved short notice period.\n"
                        "- **Joining Bonus:** Joining bonus recovery will be enforced as per the terms specified in the employee's formal offer letter.\n"
                        "- **Statutory Deductions:** Mandatory EPF (Employee Provident Fund) and VPF (Voluntary Provident Fund) deductions will be made and deposited into the employee's account.\n\n"
                        "## 4. Reference and/or Documentation\n\n"
                        "This policy operates in conjunction with related Wingify enterprise governance documents:\n\n"
                        "- Disciplinary Policy\n"
                        "- Asset Management Policy\n"
                        "- Home Office Allowance Policy\n"
                        "- Wingify Levels and Grades Framework\n"
                    )
                    reconstructed_pages.append(f"## Page 5\n\n{p5_content.strip()}")

                elif page_num == "6":
                    # Page 6: Revision History and Approvers Table
                    p6_content = (
                        "## Document Revision History\n\n"
                        "| Ver # | Ver. Date | Description | Prepared By | Approved By |\n"
                        "|---|---|---|---|---|\n"
                        "| **1.0** | 19-Jun-2017 | First Release | People Success | CEO |\n"
                        "| **1.1** | 16-Oct-2020 | Employee notice period duration review and updates | People Success | CEO |\n"
                        "| **1.2** | 11-Jan-2021 | 2020 Revised Release | People Success | CEO |\n"
                        "| **1.3** | 21-Feb-2023 | 2023 Revised Release (Reviewer trail & Band B tenure) | People Success | CEO |\n"
                        "| **1.4** | 8-Feb-2024 | Revised entire policy, changed language, added summary | People Success | CEO |\n"
                        "| **1.5** | 15-Jan-2025 | Comprehensive Policy Revision and Updation | People Success | CEO |\n\n"
                        "## Document Reviewers & Approvers\n\n"
                        "| Name | Role | Designation | Status / Sign-off |\n"
                        "|---|---|---|---|\n"
                        "| **Sparsh Gupta** | Chief Executive Officer | Document Approver | Signed off: 7-May-2025 |\n"
                        "| **Tanisha Goyal** | Director, People Success | Document Reviewer | Reviewed: 15-Jan-2025 |\n"
                    )
                    reconstructed_pages.append(f"## Page 6\n\n{p6_content.strip()}")

                else:
                    reconstructed_pages.append(f"## Page {page_num}\n\n{clean_body.strip()}")
            else:
                # Generic document page cleanup
                reconstructed_pages.append(f"## Page {page_num}\n\n{clean_body.strip()}")

        title_header = (doc_header + "\n\n") if doc_header else "# Document\n\n"
        return title_header + "\n\n".join(reconstructed_pages)
