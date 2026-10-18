# Sprint AD-4: Claim Diff Audit & Suppression Reason Ledger
**Audit Timestamp**: `2026-10-18T05:45:00Z`  
**Corpus Version**: `validation_50_v2` (21 Active English Documents)  

## 1. Executive Summary: Pre- vs Post-AD-3 Claims

- **Total Active Retained Claims**: `1019`
- **Total Suppressed / Removed Claims Audited**: `467`
- **Confirmed False Positives (Clean Noise Removal)**: `260` (55.7%)
- **Potential False Negatives (Requires Refined Head-Noun Normalization)**: `207`

### Suppression Reason Code Breakdown

| Reason Code | Count | Description |
|---|---|---|
| `PHANTOM_SUBJECT` | 20 | Synthetic 'Governance Policy' fallback with 0 grounding in evidence |
| `NARRATIVE_FRAGMENT` | 433 | Run-on narrative clause (>10 words or relative pronoun ending) |
| `UNGROUNDED_SUBJECT` | 9 | Subordinate conjunction or conversational pronoun ('Because we...', 'Then, they') |
| `NON_POLICY_CONTENT` | 0 | Third-party audit overview, marketing preamble, or informational description |
| `PROCEDURAL_CONTENT` | 5 | Step-by-step UI navigational clicks |

## 2. Document-by-Document Suppression Audit

| Doc ID | Filename | Active Claims | Suppressed Claims | Confirmed FPs | Flagged for Refinement |
|---|---|---|---|---|---|
| `DOC-051` | Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf | 11 | 4 | 4 | 0 |
| `DOC-052` | Food and Drug Administration CFR Title 21 Part 11 - Microsoft Compliance _ Microsoft Learn.pdf | 7 | 4 | 4 | 0 |
| `DOC-053` | Good Clinical, Laboratory, and Manufacturing Practices (GxP) - Microsoft Compliance _ Microsoft Learn.pdf | 3 | 5 | 4 | 1 |
| `DOC-054` | Health Data Hosting (HDS) France - Microsoft Compliance _ Microsoft Learn.pdf | 3 | 6 | 5 | 1 |
| `DOC-055` | Health Information Trust Alliance (HITRUST) Common Security Framework (CSF) - Microsoft Compliance _ Microsoft Learn.pdf | 3 | 5 | 5 | 0 |
| `DOC-056` | Health Insurance Portability and Accountability Act (HIPAA) & Health Information Technology for Economic and Clinical Health (HITECH) Act - Microsoft Compliance _ Microsoft Learn.pdf | 3 | 5 | 4 | 1 |
| `DOC-057` | Invoice-Terms-and-Conditions_EN-CH.pdf | 8 | 6 | 2 | 4 |
| `DOC-058` | manage-auto-claim-policies.md | 20 | 6 | 6 | 0 |
| `DOC-059` | manage-user-roles-vl.md | 32 | 20 | 14 | 6 |
| `DOC-060` | Microsoft Store Refund & Return Policy (Surface, Xbox, etc.).pdf | 17 | 0 | 0 | 0 |
| `DOC-061` | PO-Terms-and-Conditions_en-AU.pdf | 130 | 56 | 29 | 27 |
| `DOC-062` | PO-Terms-and-Conditions_en-BD.pdf | 126 | 55 | 27 | 28 |
| `DOC-063` | PO-Terms-and-Conditions_en-BN.pdf | 126 | 55 | 27 | 28 |
| `DOC-064` | PO-Terms-and-Conditions_en-CN.pdf | 129 | 55 | 28 | 27 |
| `DOC-065` | PO-Terms-and-Conditions_en-ID.pdf | 127 | 54 | 28 | 26 |
| `DOC-066` | PO-Terms-and-Conditions_en-IN.pdf | 119 | 58 | 30 | 28 |
| `DOC-067` | PO-Terms-and-Conditions_en-LK.pdf | 126 | 55 | 27 | 28 |
| `DOC-069` | System and Organization Controls (SOC) 1 Type 2 - Microsoft Compliance _ Microsoft Learn.pdf | 6 | 5 | 4 | 1 |
| `DOC-070` | System and Organization Controls (SOC) 2 Type 2 - Microsoft Compliance _ Microsoft Learn.pdf | 5 | 4 | 4 | 0 |
| `DOC-071` | System and Organization Controls (SOC) 3 - Microsoft Compliance _ Microsoft Learn.pdf | 5 | 6 | 5 | 1 |
| `DOC-072` | volume-licensing-invoices.md | 13 | 3 | 3 | 0 |

## 3. Flagged Items & Refinement Analysis
The audit identified the following suppressed clauses that contained legitimate legal/regulatory actors in their subject phrases. These will receive head-noun normalization to retain the rule without contaminating the subject:

- **[DOC-053]**: Sentence: *"They also recommend activities and controls that customers using in-scope Microsoft cloud services can establish to maintain control over GxP computer"*
  - **Raw Subject Matched**: `They also recommend activities and controls that customers using in-scope Micros`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-054]**: Sentence: *"Hosting of health data is regulated under French law by the French Public Health Code (Article L.1111-8), which stipulates that any healthcare organiz"*
  - **Raw Subject Matched**: `Hosting of health data is regulated under French law by the French Public Health`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-056]**: Sentence: *"Because we offer hyperscale, multitenant services that are standardized for all our customers, we must operate in a consistent manner."*
  - **Raw Subject Matched**: `Because we offer hyperscale, multitenant services that are standardized for all `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-057]**: Sentence: *"Among other things, Vendor remains fully responsible for, where relevant, reporting and paying value added tax and other applicable taxes as though th"*
  - **Raw Subject Matched**: `Among other things, Vendor remains fully responsible for, where relevant, report`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-057]**: Sentence: *"shall within 48 hours from the moment that the signed e-invoice has become available to Vendor, signal any apparent errors in such e-invoice to Micros"*
  - **Raw Subject Matched**: `shall within 48 hours from the moment that the signed e-invoice has become avail`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-057]**: Sentence: *"(1) All of the stipulations under Section 5 (Tax compliance and responsibility) above apply equally to the presumed self-billing relationship; and (2)"*
  - **Raw Subject Matched**: `(1) All of the stipulations under Section 5 (Tax compliance and responsibility) `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-057]**: Sentence: *"Microsoft and Vendor agree that the scope of this Invoicing Agreement shall apply only to the invoices issued by Vendor or Vendor’s affiliate to the M"*
  - **Raw Subject Matched**: `Microsoft and Vendor agree that the scope of this Invoicing Agreement`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-059]**: Sentence: *"> [!NOTE] > If you’re an EA or EAS customer, you can use the [Billing Role Assignments API](/rest/api/billing/billing-role-assignments?view=rest-billi"*
  - **Raw Subject Matched**: `> [!NOTE] > If you’re an EA or EAS customer, you`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-059]**: Sentence: *"Can perform all actions granted to other VL roles, except for viewing invoices.<br/><br/>If you're an EA or EAS customer, the Administrator can view i"*
  - **Raw Subject Matched**: `Can perform all actions granted to other VL roles, except for viewing invoices.<`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-059]**: Sentence: *"If you're an EA or EAS customer, when you update the Notice Contact, you don’t get the VL Administrator role, and must ask an existing VL Administrato"*
  - **Raw Subject Matched**: `If you're an EA or EAS customer, when you update the Notice Contact, you don’t g`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-059]**: Sentence: *"Non-EA and non-EAS customers only: Users receive a welcome email from microsoft-noreply\@microsoft.com with the subject line "Action required: Sign in"*
  - **Raw Subject Matched**: `Non-EA and non-EAS customers only: Users receive a welcome email from microsoft-`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-059]**: Sentence: *"## Import roles in volume licensing agreements (EA and EAS customers only) If you’re a VL Administrator for an EA or EAS agreement, you can copy the V"*
  - **Raw Subject Matched**: `## Import roles in volume licensing agreements (EA and EAS customers only) If yo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-059]**: Sentence: *"## Apply admin permissions to all license IDs under a parent program If you're the Primary Contact (non-EA and non-EAS customers only), Notices Contac"*
  - **Raw Subject Matched**: `## Apply admin permissions to all license IDs under a parent program If you're t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"If the law requires Microsoft to withhold taxes or other regulatory charges from payments to Supplier, Microsoft may withhold those amounts and pay th"*
  - **Raw Subject Matched**: `If the law requires Microsoft to withhold taxes or other regulatory charges from`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"If Microsoft inspects or tests at Supplier’s premises, Supplier, without additional charge, will provide all reasonable facilities and assistance for "*
  - **Raw Subject Matched**: `If Microsoft inspects or tests at Supplier’s premises, Supplier, without additio`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"If, after Microsoft’s request, Supplier fails to promptly replace or correct a defective item within the delivery schedule, Microsoft may, at its sole"*
  - **Raw Subject Matched**: `If, after Microsoft’s request, Supplier fails to promptly replace or correct a d`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"At a minimum, Supplier must, at all times: (1) back up, archive and maintain duplicate or redundant systems that: (i) are located at a secure physical"*
  - **Raw Subject Matched**: `At a minimum, Supplier must, at all times: (1) back up, archive and maintain dup`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"If the applicable SOW terminates or expires, or if Microsoft requests in writing, Supplier will provide: (1) backup media to Microsoft (as reasonably "*
  - **Raw Subject Matched**: `If the applicable SOW terminates or expires, or if Microsoft requests in writing`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"If any change causes an increase or decrease in the cost of, or the time required for, Supplier’s performance, an equitable adjustment may be made in "*
  - **Raw Subject Matched**: `If any change causes an increase or decrease in the cost of, or the time require`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"All tools, equipment or materials acquired by Supplier for use in providing the Goods and Services, which have been furnished to, paid for by or charg"*
  - **Raw Subject Matched**: `All tools, equipment or materials acquired by Supplier for use in providing the `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"Any AI Training without obtaining such consent is a material breach and Supplier’s limitation of liability in Section 19 will not apply to claims base"*
  - **Raw Subject Matched**: `Any AI Training without obtaining such consent is a material breach and Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"While performing under these PO Terms, Supplier will provide training to its employees on compliance with Anti -Corruption Laws and, upon request by M"*
  - **Raw Subject Matched**: `While performing under these PO Terms, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"Any device, product, website, web-based application, cloud service, software, mobile applications, or content developed or provided by or on behalf of"*
  - **Raw Subject Matched**: `Any device, product, website, web-based application, cloud service, software, mo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"If Supplier subcontracts any Services or Cloud Services to any subcontractor, Supplier will be fully liable to Microsoft for any actions or inactions "*
  - **Raw Subject Matched**: `If Supplier subcontracts any Services or Cloud Services to any subcontractor, Su`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"If Supplier does not comply with this Section 21(b), then in addition to any amounts reimbursed under this Section 21 (Indemnification and Other Remed"*
  - **Raw Subject Matched**: `If Supplier does not comply with this Section 21(b), then in addition to any amo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"If the parties have not entered into a standard Microsoft Non-Disclosure Agreement, then Supplier agrees that during the term of these PO Terms and fo"*
  - **Raw Subject Matched**: `If the parties have not entered into a standard Microsoft Non-Disclosure Agreeme`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"If Supplier has questions regarding what comprises Microsoft Confidential Information, Supplier will consult Microsoft."*
  - **Raw Subject Matched**: `If Supplier has questions regarding what comprises Microsoft Confidential Inform`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"On expiration or termination of these PO Terms or the applicable SOW, or on request by Microsoft or Microsoft’s Affiliate, Supplier will without undue"*
  - **Raw Subject Matched**: `On expiration or termination of these PO Terms or the applicable SOW, or on requ`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"For any Microsoft Confidential Information that Supplier retains after expiration or termination of these PO Terms or the applicable SOW (for example,"*
  - **Raw Subject Matched**: `For any Microsoft Confidential Information that Supplier retains after expiratio`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years after but in no event for a shorter period than required to comply with "*
  - **Raw Subject Matched**: `For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years af`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"If Supplier overcharged Microsoft 5% or more during an audited period, it will immediately refund Microsoft all overpayments plus pay interest at 0.5%"*
  - **Raw Subject Matched**: `If Supplier overcharged Microsoft 5% or more during an audited period, it`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"However, if the audit shows Supplier overcharged Microsoft by 5% or more during such audit period, Supplier will reimburse Microsoft for such expenses"*
  - **Raw Subject Matched**: `However, if the audit shows Supplier overcharged Microsoft by 5% or more during `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"Whenever an actual or potential labor dispute delays or threatens to delay the timely performance of these PO Terms, Supplier will immediately notify "*
  - **Raw Subject Matched**: `Whenever an actual or potential labor dispute delays or threatens to delay the t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"(c) With respect to Personal Data of Data Subjects located in a jurisdiction that requires an International Data Transfer Mechanism, (e.g., the EEA, S"*
  - **Raw Subject Matched**: `(c) With respect to Personal Data of Data Subjects located in a jurisdiction tha`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"If Supplier receives any type of request or inquiry from a governmental, legislative, judicial, law enforcement, or regulatory authority, or faces an "*
  - **Raw Subject Matched**: `If Supplier receives any type of request or inquiry from a governmental, legisla`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"(c) Supplier agrees to be responsible for providing notice to Data Subjects as may be required by applicable Data Protection Law (e.g., GDPR Articles "*
  - **Raw Subject Matched**: `(c) Supplier agrees to be responsible for providing notice to Data Subjects as`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"(b) Supplier agrees that the Personal Data is made available only for the limited and specified purpose(s) set forth in the contract, and that Supplie"*
  - **Raw Subject Matched**: `(b) Supplier agrees that the Personal Data is made available only for the limite`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"In addition to the deletion and return obligations set forth in Section 23 of the PO Terms, for any Microsoft Personal Data that Supplier retains afte"*
  - **Raw Subject Matched**: `In addition to the deletion and return obligations set forth in Section 23 of th`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"OPTION B of Clause 3.1 governs where the parties agree Supplier may use the Subprocessors listed in a statement of work or written agreement signed by"*
  - **Raw Subject Matched**: `OPTION B of Clause 3.1 governs where the parties agree Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-061]**: Sentence: *"Supplier remains responsible for compliance with Clauses 14 to 16 for any data to which it may otherwise be the data controller."*
  - **Raw Subject Matched**: `Supplier remains responsible for compliance with Clauses 14 to 16 for any data t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"If the law requires Microsoft to withhold taxes or other regulatory charges from payments to Supplier, Microsoft may withhold those amounts and pay th"*
  - **Raw Subject Matched**: `If the law requires Microsoft to withhold taxes or other regulatory charges from`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"If Microsoft inspects or tests at Supplier’s premises, Supplier, without additional charge , will provide all reasonable facilities and assistance for"*
  - **Raw Subject Matched**: `If Microsoft inspects or tests at Supplier’s premises, Supplier, without additio`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"If, after Microsoft’s request, Supplier fails to promptly replace or correct a defective item within the delivery schedule, Microsoft may, at its sole"*
  - **Raw Subject Matched**: `If, after Microsoft’s request, Supplier fails to promptly replace or correct a d`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"At a minimum, Supplier must, at all times: (1) back up, archive and maintain duplicate or redundant systems that: (i) are located at a secure physical"*
  - **Raw Subject Matched**: `At a minimum, Supplier must, at all times: (1) back up, archive and maintain dup`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"If the applicable SOW terminates or expires, or if Microsoft requests in writing, Supplier will provide: (1) backup media to Microsoft (as reasonably "*
  - **Raw Subject Matched**: `If the applicable SOW terminates or expires, or if Microsoft requests in writing`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"If any change causes an increase or decrease in the cost of, or the time required for, Supplier’s performance, an equitable adjustment may be made in "*
  - **Raw Subject Matched**: `If any change causes an increase or decrease in the cost of, or the time require`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"If Supplier uses any Supplier or third-party IP in any Good or Service, Supplier will continue to own Supplier’s IP rights."*
  - **Raw Subject Matched**: `If Supplier uses any Supplier or third-party IP in any Good or Service, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"Any AI Training without obtaining such consent is a material breach and Supplier’s limitation of liability in Section 19 will not apply to claims base"*
  - **Raw Subject Matched**: `Any AI Training without obtaining such consent is a material breach and Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"While performing under these PO Terms, Supplier will provide training to its employees on compliance with Anti -Corruption Laws and, upon request by M"*
  - **Raw Subject Matched**: `While performing under these PO Terms, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"Supplier will, at its expense, implement and maintain appropriate technical and organizational measures to protect Confidential Information, including"*
  - **Raw Subject Matched**: `Supplier will, at its expense, implement and maintain appropriate technical and `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"When Supplier provides Cloud Services : 1) At Supplier’s cost, Supplier will maintain a valid certification under the International Organization for S"*
  - **Raw Subject Matched**: `When Supplier provides Cloud Services : 1) At Supplier’s cost, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"Any device, product, website, web-based application, cloud service, software, mobile applications, or content developed or provided by or on behalf of"*
  - **Raw Subject Matched**: `Any device, product, website, web-based application, cloud service, software, mo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"If Supplier subcontracts any Services or Cloud Services to any subcontractor, Supplier will be fully liable to Microsoft for any actions or inactions "*
  - **Raw Subject Matched**: `If Supplier subcontracts any Services or Cloud Services to any subcontractor, Su`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"If Supplier does not comply with this Section 21(b), then in addition to any amounts reimbursed under this Section 21 (Indemnification a nd Other Reme"*
  - **Raw Subject Matched**: `If Supplier does not comply with this Section 21(b), then in addition to any amo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"If the parties have not entered into a standard Microsoft Non -Disclosure Agreement, then Supplier agrees that during the term of these PO Terms and f"*
  - **Raw Subject Matched**: `If the parties have not entered into a standard Microsoft Non -Disclosure Agreem`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"On expiration or termination of these PO Terms or the applicable SOW, or on request by Microsoft or Microsoft’s Affiliate, Supplier will without undue"*
  - **Raw Subject Matched**: `On expiration or termination of these PO Terms or the applicable SOW, or on requ`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"For any Microsoft Confidential Information that Supplier retains after expira tion or termination of the se PO Terms or the applicable SOW (for exampl"*
  - **Raw Subject Matched**: `For any Microsoft Confidential Information that Supplier retains after expira ti`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years, but in no event for a shorter period than required to comply with Law, "*
  - **Raw Subject Matched**: `For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years, b`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"If Supplier overcharged Microsoft 5% or more during an audited period, it will immediately refund Microsoft all overpayments plus pay interest at 0.5%"*
  - **Raw Subject Matched**: `If Supplier overcharged Microsoft 5% or more during an audited period, it`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"However, if the audit shows Supplier overcharged Microsoft by 5% or more during such audit period, Supplier will reimburse Microsoft for such expenses"*
  - **Raw Subject Matched**: `However, if the audit shows Supplier overcharged Microsoft by 5% or more during `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"Whenever an actual or potential labor dispute delays or threatens to delay the timely performance of these PO Terms, Supplier will immediately notify "*
  - **Raw Subject Matched**: `Whenever an actual or potential labor dispute delays or threatens to delay the t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"(c) With respect to Personal Data of Data Subjects located in a jurisdiction that requires an International Data Transfer Mechanism, (e.g., the EEA, S"*
  - **Raw Subject Matched**: `(c) With respect to Personal Data of Data Subjects located in a jurisdiction tha`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"If Supplier receives any type of request or inquiry from a governmental, legislative, judicial, law enforcement, or regulatory authority, or faces an "*
  - **Raw Subject Matched**: `If Supplier receives any type of request or inquiry from a governmental, legisla`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"(a) Supplier acknowledges and agrees that Supplier is independently responsible for compliance and will comply with applicable Data Protection Law (e."*
  - **Raw Subject Matched**: `(a) Supplier acknowledges and agrees that Supplier is independently responsible `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"(b) Supplier agrees that the Personal Data is made available only for the limited and specified purpose(s) set forth in the contract, and that Supplie"*
  - **Raw Subject Matched**: `(b) Supplier agrees that the Personal Data is made available only for the limite`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"In addition to the deletion and return obligations set forth in Section 23 of the PO Terms, for any Microsoft Personal Data that Supplier retains afte"*
  - **Raw Subject Matched**: `In addition to the deletion and return obligations set forth in Section 23 of th`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"OPTION B of Clause 3.1 governs where the parties agree Supplier may use the Subprocessors listed in a statement of work or written agreement signed by"*
  - **Raw Subject Matched**: `OPTION B of Clause 3.1 governs where the parties agree Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-062]**: Sentence: *"Supplier remains responsible for compliance with Clauses 14 to 16 for any data to which it may otherwise be the data controller."*
  - **Raw Subject Matched**: `Supplier remains responsible for compliance with Clauses 14 to 16 for any data t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"If the law requires Microsoft to withhold taxes or other regulatory charges from payments to Supplier, Microsoft may withhold those amounts and pay th"*
  - **Raw Subject Matched**: `If the law requires Microsoft to withhold taxes or other regulatory charges from`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"If Microsoft inspects or tests at Supplier’s premises, Supplier, without additional charge , will provide all reasonable facilities and assistance for"*
  - **Raw Subject Matched**: `If Microsoft inspects or tests at Supplier’s premises, Supplier, without additio`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"If, after Microsoft’s request, Supplier fails to promptly replace or correct a defective item within the delivery schedule, Microsoft may, at its sole"*
  - **Raw Subject Matched**: `If, after Microsoft’s request, Supplier fails to promptly replace or correct a d`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"At a minimum, Supplier must, at all times: (1) back up, archive and maintain duplicate or redundant systems that: (i) are located at a secure physical"*
  - **Raw Subject Matched**: `At a minimum, Supplier must, at all times: (1) back up, archive and maintain dup`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"If the applicable SOW terminates or expires, or if Microsoft requests in writing, Supplier will provide: (1) backup media to Microsoft (as reasonably "*
  - **Raw Subject Matched**: `If the applicable SOW terminates or expires, or if Microsoft requests in writing`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"If any change causes an increase or decrease in the cost of, or the time required for, Supplier’s performance, an equitable adjustment may be made in "*
  - **Raw Subject Matched**: `If any change causes an increase or decrease in the cost of, or the time require`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"If Supplier uses any Supplier or third-party IP in any Good or Service, Supplier will continue to own Supplier’s IP rights."*
  - **Raw Subject Matched**: `If Supplier uses any Supplier or third-party IP in any Good or Service, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"Any AI Training without obtaining such consent is a material breach and Supplier’s limitation of liability in Section 19 will not apply to claims base"*
  - **Raw Subject Matched**: `Any AI Training without obtaining such consent is a material breach and Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"While performing under these PO Terms, Supplier will provide training to its employees on compliance with Anti -Corruption Laws and, upon request by M"*
  - **Raw Subject Matched**: `While performing under these PO Terms, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"Supplier will, at its expense, implement and maintain appropriate technical and organizational measures to protect Confidential Information, including"*
  - **Raw Subject Matched**: `Supplier will, at its expense, implement and maintain appropriate technical and `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"When Supplier provides Cloud Services : 1) At Supplier’s cost, Supplier will maintain a valid certification under the International Organization for S"*
  - **Raw Subject Matched**: `When Supplier provides Cloud Services : 1) At Supplier’s cost, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"Any device, product, website, web-based application, cloud service, software, mobile applications, or content developed or provided by or on behalf of"*
  - **Raw Subject Matched**: `Any device, product, website, web-based application, cloud service, software, mo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"If Supplier subcontracts any Services or Cloud Services to any subcontractor, Supplier will be fully liable to Microsoft for any actions or inactions "*
  - **Raw Subject Matched**: `If Supplier subcontracts any Services or Cloud Services to any subcontractor, Su`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"If Supplier does not comply with this Section 21(b), then in addition to any amounts reimbursed under this Section 21 (Indemnification a nd Other Reme"*
  - **Raw Subject Matched**: `If Supplier does not comply with this Section 21(b), then in addition to any amo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"If the parties have not entered into a standard Microsoft Non -Disclosure Agreement, then Supplier agrees that during the term of these PO Terms and f"*
  - **Raw Subject Matched**: `If the parties have not entered into a standard Microsoft Non -Disclosure Agreem`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"On expiration or termination of these PO Terms or the applicable SOW, or on request by Microsoft or Microsoft’s Affiliate, Supplier will without undue"*
  - **Raw Subject Matched**: `On expiration or termination of these PO Terms or the applicable SOW, or on requ`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"For any Microsoft Confidential Information that Supplier retains after expira tion or termination of the se PO Terms or the applicable SOW (for exampl"*
  - **Raw Subject Matched**: `For any Microsoft Confidential Information that Supplier retains after expira ti`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years, but in no event for a shorter period than required to comply with Law, "*
  - **Raw Subject Matched**: `For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years, b`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"If Supplier overcharged Microsoft 5% or more during an audited period, it will immediately refund Microsoft all overpayments plus pay interest at 0.5%"*
  - **Raw Subject Matched**: `If Supplier overcharged Microsoft 5% or more during an audited period, it`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"However, if the audit shows Supplier overcharged Microsoft by 5% or more during such audit period, Supplier will reimburse Microsoft for such expenses"*
  - **Raw Subject Matched**: `However, if the audit shows Supplier overcharged Microsoft by 5% or more during `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"Whenever an actual or potential labor dispute delays or threatens to delay the timely performance of these PO Terms, Supplier will immediately notify "*
  - **Raw Subject Matched**: `Whenever an actual or potential labor dispute delays or threatens to delay the t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"(c) With respect to Personal Data of Data Subjects located in a jurisdiction that requires an International Data Transfer Mechanism, (e.g., the EEA, S"*
  - **Raw Subject Matched**: `(c) With respect to Personal Data of Data Subjects located in a jurisdiction tha`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"If Supplier receives any type of request or inquiry from a governmental, legislative, judicial, law enforcement, or regulatory authority, or faces an "*
  - **Raw Subject Matched**: `If Supplier receives any type of request or inquiry from a governmental, legisla`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"(a) Supplier acknowledges and agrees that Supplier is independently responsible for compliance and will comply with applicable Data Protection Law (e."*
  - **Raw Subject Matched**: `(a) Supplier acknowledges and agrees that Supplier is independently responsible `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"(b) Supplier agrees that the Personal Data is made available only for the limited and specified purpose(s) set forth in the contract, and that Supplie"*
  - **Raw Subject Matched**: `(b) Supplier agrees that the Personal Data is made available only for the limite`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"In addition to the deletion and return obligations set forth in Section 23 of the PO Terms, for any Microsoft Personal Data that Supplier retains afte"*
  - **Raw Subject Matched**: `In addition to the deletion and return obligations set forth in Section 23 of th`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"OPTION B of Clause 3.1 governs where the parties agree Supplier may use the Subprocessors listed in a statement of work or written agreement signed by"*
  - **Raw Subject Matched**: `OPTION B of Clause 3.1 governs where the parties agree Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-063]**: Sentence: *"Supplier remains responsible for compliance with Clauses 14 to 16 for any data to which it may otherwise be the data controller."*
  - **Raw Subject Matched**: `Supplier remains responsible for compliance with Clauses 14 to 16 for any data t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"If the law requires Microsoft to withhold taxes or other regulatory charges from payments to Supplier, Microsoft may withhold those amounts and pay th"*
  - **Raw Subject Matched**: `If the law requires Microsoft to withhold taxes or other regulatory charges from`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"If Microsoft inspects or tests at Supplier’s premises, Supplier, without additional charge, will provide all reasonable facilities and assistance for "*
  - **Raw Subject Matched**: `If Microsoft inspects or tests at Supplier’s premises, Supplier, without additio`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"If, after Microsoft’s request, Supplier fails to promptly replace or correct a defective item within the delivery schedule, Microsoft may, at its sole"*
  - **Raw Subject Matched**: `If, after Microsoft’s request, Supplier fails to promptly replace or correct a d`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"At a minimum, Supplier must, at all times: (1) back up, archive and maintain duplicate or redundant systems that: (i) are located at a secure physical"*
  - **Raw Subject Matched**: `At a minimum, Supplier must, at all times: (1) back up, archive and maintain dup`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"If the applicable SOW terminates or expires, or if Microsoft requests in writing, Supplier will provide: (1) backup media to Microsoft (as reasonably "*
  - **Raw Subject Matched**: `If the applicable SOW terminates or expires, or if Microsoft requests in writing`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"If any change causes an increase or decrease in the cost of, or the time required for, Supplier’s performance, an equitable adjustment may be made in "*
  - **Raw Subject Matched**: `If any change causes an increase or decrease in the cost of, or the time require`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"All tools, equipment or materials acquired by Supplier for use in providing the Goods and Services, which have been furnished to, paid for by or charg"*
  - **Raw Subject Matched**: `All tools, equipment or materials acquired by Supplier for use in providing the `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"If Supplier uses any Supplier or third-party IP in any Good or Service, Supplier will continue to own Supplier’s IP rights."*
  - **Raw Subject Matched**: `If Supplier uses any Supplier or third-party IP in any Good or Service, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"Any AI Training without obtaining such consent is a material breach and Supplier’s limitation of liability in Section 19 will not apply to claims base"*
  - **Raw Subject Matched**: `Any AI Training without obtaining such consent is a material breach and Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"While performing under these PO Terms, Supplier will provide training to its employees on compliance with Anti-Corruption Laws and, upon request by Mi"*
  - **Raw Subject Matched**: `While performing under these PO Terms, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"Supplier will, at its expense, implement and maintain appropriate technical and organizational measures to protect Confidential Information, including"*
  - **Raw Subject Matched**: `Supplier will, at its expense, implement and maintain appropriate technical and `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"Any device, product, website, web-based application, cloud service, software, mobile applications, or content developed or provided by or on behalf of"*
  - **Raw Subject Matched**: `Any device, product, website, web-based application, cloud service, software, mo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"If Supplier does not comply with this Section 21(b), then in addition to any amounts reimbursed under this Section 21 (Indemnification and Other Remed"*
  - **Raw Subject Matched**: `If Supplier does not comply with this Section 21(b), then in addition to any amo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"If the parties have not entered into a standard Microsoft Non-Disclosure Agreement, then Supplier agrees that during the term of these PO Terms and fo"*
  - **Raw Subject Matched**: `If the parties have not entered into a standard Microsoft Non-Disclosure Agreeme`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"On expiration or termination of these PO Terms or the applicable SOW, or on request by Microsoft or Microsoft’s Affiliate, Supplier will without undue"*
  - **Raw Subject Matched**: `On expiration or termination of these PO Terms or the applicable SOW, or on requ`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"For any Microsoft Confidential Information that Supplier retains after expiration or termination of these PO Terms or the applicable SOW (for example,"*
  - **Raw Subject Matched**: `For any Microsoft Confidential Information that Supplier retains after expiratio`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years, but in no event for a shorter period than required to comply with Law, "*
  - **Raw Subject Matched**: `For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years, b`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"If Supplier overcharged Microsoft 5% or more during an audited period, it will immediately refund Microsoft all overpayments plus pay interest at 0.5%"*
  - **Raw Subject Matched**: `If Supplier overcharged Microsoft 5% or more during an audited period, it`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"However, if the audit shows Supplier overcharged Microsoft by 5% or more during such audit period, Supplier will reimburse Microsoft for such expenses"*
  - **Raw Subject Matched**: `However, if the audit shows Supplier overcharged Microsoft by 5% or more during `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"Whenever an actual or potential labor dispute delays or threatens to delay the timely performance of these PO Terms, Supplier will immediately notify "*
  - **Raw Subject Matched**: `Whenever an actual or potential labor dispute delays or threatens to delay the t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"If Supplier receives any type of request or inquiry from a governmental, legislative, judicial, law enforcement, or regulatory authority, or faces an "*
  - **Raw Subject Matched**: `If Supplier receives any type of request or inquiry from a governmental, legisla`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"(a) Supplier acknowledges and agrees that Supplier is independently responsible for compliance and will comply with applicable Data Protection Law (e."*
  - **Raw Subject Matched**: `(a) Supplier acknowledges and agrees that Supplier is independently responsible `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"(b) Supplier agrees that the Personal Data is made available only for the limited and specified purpose(s) set forth in the contract, and that Supplie"*
  - **Raw Subject Matched**: `(b) Supplier agrees that the Personal Data is made available only for the limite`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"In addition to the deletion and return obligations set forth in Section 23 of the PO Terms, for any Microsoft Personal Data that Supplier retains afte"*
  - **Raw Subject Matched**: `In addition to the deletion and return obligations set forth in Section 23 of th`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"justification for that retention, and the applicable retention period(s); (B) Supplier will continue to comply with all terms of the PO Terms applicab"*
  - **Raw Subject Matched**: `justification for that retention, and the applicable retention period(s); (B) Su`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"OPTION B of Clause 3.1 governs where the parties agree Supplier may use the Subprocessors listed in a statement of work or written agreement signed by"*
  - **Raw Subject Matched**: `OPTION B of Clause 3.1 governs where the parties agree Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-064]**: Sentence: *"Supplier remains responsible for compliance with Clauses 14 to 16 for any data to which it may otherwise be the data controller."*
  - **Raw Subject Matched**: `Supplier remains responsible for compliance with Clauses 14 to 16 for any data t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"If the law requires Microsoft to withhold taxes or other regulatory charges from payments to Supplier, Microsoft may withhold those amount and pay the"*
  - **Raw Subject Matched**: `If the law requires Microsoft to withhold taxes or other regulatory charges from`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"If Microsoft inspects or tests at Supplier’s premises, Supplier, without additional charge, will provide all reasonable facilities and assistance for "*
  - **Raw Subject Matched**: `If Microsoft inspects or tests at Supplier’s premises, Supplier, without additio`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"If, after Microsoft’s request, Supplier fails to promptly replace or correct a defective item within the delivery schedule, Microsoft may, at its sole"*
  - **Raw Subject Matched**: `If, after Microsoft’s request, Supplier fails to promptly replace or correct a d`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"At a minimum, Supplier must, at all times: (1) back up, archive and maintain duplicate or redundant systems that: (i) are located at a secure physical"*
  - **Raw Subject Matched**: `At a minimum, Supplier must, at all times: (1) back up, archive and maintain dup`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"If the applicable SOW terminates or expires, or if Microsoft requests in writing, Supplier will provide: (1) backup media to Microsoft (as reasonably "*
  - **Raw Subject Matched**: `If the applicable SOW terminates or expires, or if Microsoft requests in writing`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"If any change causes an increase or decrease in the cost of, or the time required for, Supplier’s performance, an equitable adjustment may be made in "*
  - **Raw Subject Matched**: `If any change causes an increase or decrease in the cost of, or the time require`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"All tools, equipment or materials acquired by Supplier for use in providing the Goods and Services, which have been furnished to, paid for by or charg"*
  - **Raw Subject Matched**: `All tools, equipment or materials acquired by Supplier for use in providing the `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"If Supplier uses any Supplier or third-party IP in any Good or Service, Supplier will continue to own Supplier’s IP rights."*
  - **Raw Subject Matched**: `If Supplier uses any Supplier or third-party IP in any Good or Service, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"Any AI Training without obtaining such consent is a material breach and Supplier’s limitation of liability in Section 19 will not apply to claims base"*
  - **Raw Subject Matched**: `Any AI Training without obtaining such consent is a material breach and Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"Supplier will, at its expense, implement and maintain appropriate technical and organizational measures to protect Confidential Information, including"*
  - **Raw Subject Matched**: `Supplier will, at its expense, implement and maintain appropriate technical and `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"Any device, product, website, web -based application, cloud service, software, mobile applications, or content developed or provided by or on behalf o"*
  - **Raw Subject Matched**: `Any device, product, website, web -based application, cloud service, software, m`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"If Supplier does not comply with this Section 21(b), then in addition to any amounts reimbursed under this Section 21 (Indemnification and Other Remed"*
  - **Raw Subject Matched**: `If Supplier does not comply with this Section 21(b), then in addition to any amo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"If the parties have not entered into a standard Microsoft Non-Disclosure Agreement, then Supplier agrees that during the term of these PO Terms and fo"*
  - **Raw Subject Matched**: `If the parties have not entered into a standard Microsoft Non-Disclosure Agreeme`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"On expiration or termination of these PO Terms or the applicable SOW, or on request by Microsoft or Microsoft’s Affiliate, Supplier will without undue"*
  - **Raw Subject Matched**: `On expiration or termination of these PO Terms or the applicable SOW, or on requ`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"For any Microsoft Confidential Information that Supplier retains after expiration or termination of these PO Terms or the applicable SOW (for example,"*
  - **Raw Subject Matched**: `For any Microsoft Confidential Information that Supplier retains after expiratio`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years, but in no event for a shorter period than required to comply with Law, "*
  - **Raw Subject Matched**: `For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years, b`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"If Supplier overcharged Microsoft 5% or more during an audited period, it will immediately refund Microsoft all overpayments plus pay interest at 0.5%"*
  - **Raw Subject Matched**: `If Supplier overcharged Microsoft 5% or more during an audited period, it`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"However, if the audit shows Supplier overcharged Microsoft by 5% or more during such audit period, Supplier will reimburse Microsoft for such expenses"*
  - **Raw Subject Matched**: `However, if the audit shows Supplier overcharged Microsoft by 5% or more during `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"Whenever an actual or potential labor dispute delays or threatens to delay the timely performance of these PO Terms, Supplier will immediately notify "*
  - **Raw Subject Matched**: `Whenever an actual or potential labor dispute delays or threatens to delay the t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"If Supplier receives any type of request or inquiry from a governmental, legislative, judicial, law enforcement, or regulatory authority, or faces an "*
  - **Raw Subject Matched**: `If Supplier receives any type of request or inquiry from a governmental, legisla`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"(a) Supplier acknowledges and agrees that Supplier is independently responsible for compliance and will comply with applicable Data Protection Law (e."*
  - **Raw Subject Matched**: `(a) Supplier acknowledges and agrees that Supplier is independently responsible `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"(b) Supplier agrees that the Personal Data is made available only for the limited and specified purpose(s) set forth in the contract, and that Supplie"*
  - **Raw Subject Matched**: `(b) Supplier agrees that the Personal Data is made available only for the limite`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"In addition to the deletion and return obligations set forth in Section 23 of the PO Terms, for any Microsoft Personal Data that Supplier retains afte"*
  - **Raw Subject Matched**: `In addition to the deletion and return obligations set forth in Section 23 of th`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"justification for that retention, and the applicable retention period(s); (B) Supplier will continue to comply with all terms of the PO Terms applicab"*
  - **Raw Subject Matched**: `justification for that retention, and the applicable retention period(s); (B) Su`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"OPTION B of Clause 3.1 governs where the parties agree Supplier may use the Subprocessors listed in a statement of work or written agreement signed by"*
  - **Raw Subject Matched**: `OPTION B of Clause 3.1 governs where the parties agree Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-065]**: Sentence: *"Supplier remains responsible for compliance with Clauses 14 to 16 for any data to which it may otherwise be the data controller."*
  - **Raw Subject Matched**: `Supplier remains responsible for compliance with Clauses 14 to 16 for any data t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"If the law requires Microsoft to withhold taxes or other regulatory charges from payments to Supplier, Microsoft may withhold those amounts and pay th"*
  - **Raw Subject Matched**: `If the law requires Microsoft to withhold taxes or other regulatory charges from`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"(1) non-compliance with statutory obligations by the Supplier (including but not limited to failure to upload details of sale on the GSTN portal and f"*
  - **Raw Subject Matched**: `(1) non-compliance with statutory obligations by the Supplier (including but not`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"If Microsoft inspects or tests at Supplier’s premises, Supplier, without additional charge, will provide all reasonable facilities and assistance for "*
  - **Raw Subject Matched**: `If Microsoft inspects or tests at Supplier’s premises, Supplier, without additio`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"If, after Microsoft’s request, Supplier fails to promptly replace or correct a defective item within the delivery schedule, Microsoft may, at its sole"*
  - **Raw Subject Matched**: `If, after Microsoft’s request, Supplier fails to promptly replace or correct a d`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"At a minimum, Supplier must, at all times: (1) back up, archive and maintain duplicate or redundant systems that: (i) are located at a secure physical"*
  - **Raw Subject Matched**: `At a minimum, Supplier must, at all times: (1) back up, archive and maintain dup`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"If the applicable SOW terminates or expires, or if Microsoft requests in writing, Supplier will provide:"*
  - **Raw Subject Matched**: `If the applicable SOW terminates or expires, or if Microsoft requests in writing`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"If any change causes an increase or decrease in the cost of, or the time required for, Supplier’s performance, an equitable adjustment may be made in "*
  - **Raw Subject Matched**: `If any change causes an increase or decrease in the cost of, or the time require`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"All tools, equipment or materials acquired by Supplier for use in providing the Goods and Services, which have been furnished to, paid for by or charg"*
  - **Raw Subject Matched**: `All tools, equipment or materials acquired by Supplier for use in providing the `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"While performing under these PO Terms, Supplier will provide training to its employees on compliance with Anti-Corruption Laws and, upon request by Mi"*
  - **Raw Subject Matched**: `While performing under these PO Terms, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"Supplier will, at its expense, implement and maintain appropriate technical and organizational measures to protect Confidential Information, including"*
  - **Raw Subject Matched**: `Supplier will, at its expense, implement and maintain appropriate technical and `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"Any device, product, website, web -based application, cloud service, software, mobile applications, or content developed or provided by or on behalf o"*
  - **Raw Subject Matched**: `Any device, product, website, web -based application, cloud service, software, m`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"If Supplier subcontracts any Services or Cloud Services to any subcontractor, Supplier will be fully liable to Microsoft for any actions or inactions "*
  - **Raw Subject Matched**: `If Supplier subcontracts any Services or Cloud Services to any subcontractor, Su`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"If Supplier does not comply with this Section 21(b), then in addition to any amounts reimbursed under this Section 21 (Indemnification and Other Remed"*
  - **Raw Subject Matched**: `If Supplier does not comply with this Section 21(b), then in addition to any amo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"If the parties have not entered into a standard Microsoft Non-Disclosure Agreement, then Supplier agrees that during the term of these PO Terms and fo"*
  - **Raw Subject Matched**: `If the parties have not entered into a standard Microsoft Non-Disclosure Agreeme`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"On expiration or termination of these PO Terms or the applicable SOW, or on request by Microsoft or Microsoft’s Affiliate, Supplier will without undue"*
  - **Raw Subject Matched**: `On expiration or termination of these PO Terms or the applicable SOW, or on requ`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"For any Microsoft Confidential Information that Supplier retains after expiration or termination of these PO Terms or the applicable SOW (for example,"*
  - **Raw Subject Matched**: `For any Microsoft Confidential Information that Supplier retains after expiratio`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years , but in no event for a shorter period than required to comply with Law,"*
  - **Raw Subject Matched**: `For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years , `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"If Supplier overcharged Microsoft 5% or more during an audited period, it will immediately refund Microsoft all overpayments plus pay interest at 0.5%"*
  - **Raw Subject Matched**: `If Supplier overcharged Microsoft 5% or more during an audited period, it`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"However, if the audit shows Supplier overcharged Microsoft by 5% or more during such audit period, Supplier will reimburse Microsoft for such expenses"*
  - **Raw Subject Matched**: `However, if the audit shows Supplier overcharged Microsoft by 5% or more during `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"Whenever an actual or potential labor dispute delays or threatens to delay the timely performance of these PO Terms, Supplier will immediately notify "*
  - **Raw Subject Matched**: `Whenever an actual or potential labor dispute delays or threatens to delay the t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"(c) With respect to Personal Data of Data Subjects located in a jurisdiction that requires an International Data Transfer Mechanism, (e.g., the EEA, S"*
  - **Raw Subject Matched**: `(c) With respect to Personal Data of Data Subjects located in a jurisdiction tha`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"If Supplier receives any type of request or inquiry from a governmental, legislative, judicial, law enforcement, or regulatory authority, or faces an "*
  - **Raw Subject Matched**: `If Supplier receives any type of request or inquiry from a governmental, legisla`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"(a) Supplier acknowledges and agrees that Supplier is independently responsible for compliance and will comply with applicable Data Protection Law (e."*
  - **Raw Subject Matched**: `(a) Supplier acknowledges and agrees that Supplier is independently responsible `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"(b) Supplier agrees that the Personal Data is made available only for the limited and specified purpose(s) set forth in the contract, and that Supplie"*
  - **Raw Subject Matched**: `(b) Supplier agrees that the Personal Data is made available only for the limite`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"In addition to the deletion and return obligations set forth in Section 23 of the PO Terms, for any Microsoft Personal Data that Supplier retains afte"*
  - **Raw Subject Matched**: `In addition to the deletion and return obligations set forth in Section 23 of th`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"justification for that retention, and the applicable retention period(s); (B) Supplier will continue to comply with all terms of the PO Terms applicab"*
  - **Raw Subject Matched**: `justification for that retention, and the applicable retention period(s); (B) Su`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"OPTION B of Clause 3.1 governs where the parties agree Supplier may use the Subprocessors listed in a statement of work or written agreement signed by"*
  - **Raw Subject Matched**: `OPTION B of Clause 3.1 governs where the parties agree Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-066]**: Sentence: *"Supplier remains responsible for compliance with Clauses 14 to 16 for any data to which it may otherwise be the data controller."*
  - **Raw Subject Matched**: `Supplier remains responsible for compliance with Clauses 14 to 16 for any data t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"If the law requires Microsoft to withhold taxes or other regulatory charges from payments to Supplier, Microsoft may withhold those amounts and pay th"*
  - **Raw Subject Matched**: `If the law requires Microsoft to withhold taxes or other regulatory charges from`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"If Microsoft inspects or tests at Supplier’s premises, Supplier, without additional charge , will provide all reasonable facilities and assistance for"*
  - **Raw Subject Matched**: `If Microsoft inspects or tests at Supplier’s premises, Supplier, without additio`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"If, after Microsoft’s request, Supplier fails to promptly replace or correct a defective item within the delivery schedule, Microsoft may, at its sole"*
  - **Raw Subject Matched**: `If, after Microsoft’s request, Supplier fails to promptly replace or correct a d`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"At a minimum, Supplier must, at all times: (1) back up, archive and maintain duplicate or redundant systems that: (i) are located at a secure physical"*
  - **Raw Subject Matched**: `At a minimum, Supplier must, at all times: (1) back up, archive and maintain dup`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"If the applicable SOW terminates or expires, or if Microsoft requests in writing, Supplier will provide: (1) backup media to Microsoft (as reasonably "*
  - **Raw Subject Matched**: `If the applicable SOW terminates or expires, or if Microsoft requests in writing`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"If any change causes an increase or decrease in the cost of, or the time required for, Supplier’s performance, an equitable adjustment may be made in "*
  - **Raw Subject Matched**: `If any change causes an increase or decrease in the cost of, or the time require`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"If Supplier uses any Supplier or third-party IP in any Good or Service, Supplier will continue to own Supplier’s IP rights."*
  - **Raw Subject Matched**: `If Supplier uses any Supplier or third-party IP in any Good or Service, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"Any AI Training without obtaining such consent is a material breach and Supplier’s limitation of liability in Section 19 will not apply to claims base"*
  - **Raw Subject Matched**: `Any AI Training without obtaining such consent is a material breach and Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"While performing under these PO Terms, Supplier will provide training to its employees on compliance with Anti -Corruption Laws and, upon request by M"*
  - **Raw Subject Matched**: `While performing under these PO Terms, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"Supplier will, at its expense, implement and maintain appropriate technical and organizational measures to protect Confidential Information, including"*
  - **Raw Subject Matched**: `Supplier will, at its expense, implement and maintain appropriate technical and `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"When Supplier provides Cloud Services : 1) At Supplier’s cost, Supplier will maintain a valid certification under the International Organization for S"*
  - **Raw Subject Matched**: `When Supplier provides Cloud Services : 1) At Supplier’s cost, Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"Any device, product, website, web-based application, cloud service, software, mobile applications, or content developed or provided by or on behalf of"*
  - **Raw Subject Matched**: `Any device, product, website, web-based application, cloud service, software, mo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"If Supplier subcontracts any Services or Cloud Services to any subcontractor, Supplier will be fully liable to Microsoft for any actions or inactions "*
  - **Raw Subject Matched**: `If Supplier subcontracts any Services or Cloud Services to any subcontractor, Su`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"If Supplier does not comply with this Section 21(b), then in addition to any amounts reimbursed under this Section 21 (Indemnification a nd Other Reme"*
  - **Raw Subject Matched**: `If Supplier does not comply with this Section 21(b), then in addition to any amo`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"If the parties have not entered into a standard Microsoft Non -Disclosure Agreement, then Supplier agrees that during the term of these PO Terms and f"*
  - **Raw Subject Matched**: `If the parties have not entered into a standard Microsoft Non -Disclosure Agreem`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"On expiration or termination of these PO Terms or the applicable SOW, or on request by Microsoft or Microsoft’s Affiliate, Supplier will without undue"*
  - **Raw Subject Matched**: `On expiration or termination of these PO Terms or the applicable SOW, or on requ`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"For any Microsoft Confidential Information that Supplier retains after expira tion or termination of the se PO Terms or the applicable SOW (for exampl"*
  - **Raw Subject Matched**: `For any Microsoft Confidential Information that Supplier retains after expira ti`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years, but in no event for a shorter period than required to comply with Law, "*
  - **Raw Subject Matched**: `For the longer of (i) 7 years or (ii) the term of these PO Terms plus 4 years, b`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"If Supplier overcharged Microsoft 5% or more during an audited period, it will immediately refund Microsoft all overpayments plus pay interest at 0.5%"*
  - **Raw Subject Matched**: `If Supplier overcharged Microsoft 5% or more during an audited period, it`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"However, if the audit shows Supplier overcharged Microsoft by 5% or more during such audit period, Supplier will reimburse Microsoft for such expenses"*
  - **Raw Subject Matched**: `However, if the audit shows Supplier overcharged Microsoft by 5% or more during `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"Whenever an actual or potential labor dispute delays or threatens to delay the timely performance of these PO Terms, Supplier will immediately notify "*
  - **Raw Subject Matched**: `Whenever an actual or potential labor dispute delays or threatens to delay the t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"(c) With respect to Personal Data of Data Subjects located in a jurisdiction that requires an International Data Transfer Mechanism, (e.g., the EEA, S"*
  - **Raw Subject Matched**: `(c) With respect to Personal Data of Data Subjects located in a jurisdiction tha`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"If Supplier receives any type of request or inquiry from a governmental, legislative, judicial, law enforcement, or regulatory authority, or faces an "*
  - **Raw Subject Matched**: `If Supplier receives any type of request or inquiry from a governmental, legisla`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"(a) Supplier acknowledges and agrees that Supplier is independently responsible for compliance and will comply with applicable Data Protection Law (e."*
  - **Raw Subject Matched**: `(a) Supplier acknowledges and agrees that Supplier is independently responsible `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"(b) Supplier agrees that the Personal Data is made available only for the limited and specified purpose(s) set forth in the contract, and that Supplie"*
  - **Raw Subject Matched**: `(b) Supplier agrees that the Personal Data is made available only for the limite`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"In addition to the deletion and return obligations set forth in Section 23 of the PO Terms, for any Microsoft Personal Data that Supplier retains afte"*
  - **Raw Subject Matched**: `In addition to the deletion and return obligations set forth in Section 23 of th`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"OPTION B of Clause 3.1 governs where the parties agree Supplier may use the Subprocessors listed in a statement of work or written agreement signed by"*
  - **Raw Subject Matched**: `OPTION B of Clause 3.1 governs where the parties agree Supplier`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-067]**: Sentence: *"Supplier remains responsible for compliance with Clauses 14 to 16 for any data to which it may otherwise be the data controller."*
  - **Raw Subject Matched**: `Supplier remains responsible for compliance with Clauses 14 to 16 for any data t`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-069]**: Sentence: *"Applicability In-scope services Help, Search Content Service, SharePoint Online (including OneDrive, Microsoft 365 Backup, Project Online, Viva Topics"*
  - **Raw Subject Matched**: `Applicability In-scope services Help, Search Content Service, SharePoint Online `
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.

- **[DOC-071]**: Sentence: *"ﾉ Expand table Applicability In-scope services Commercial Compliance Manager, Customer Lockbox, Delve, Exchange Online, Exchange Online Protection, Fo"*
  - **Raw Subject Matched**: `ﾉ Expand table Applicability In-scope services Commercial Compliance Manager, Cu`
  - **Target Refinement**: Extract legal actor head-noun (e.g., `Covered entities`), moving the remainder into `conditions`.
