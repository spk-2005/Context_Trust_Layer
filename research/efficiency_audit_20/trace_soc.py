import re

ev = 'Applicability In-scope services Help, Search Content Service, SharePoint Online (including OneDrive, Microsoft 365 Backup, Project Online, Viva Topics, and Viva Connections), Tasks Business Scenario Service, Viva Insights (including Personal Insights), Whiteboard, and Windows 365 GCC High Bing Teams (including ObjectStore), Customer Lockbox, Exchange Online, Exchange Online Protection, Loki, M365 Usage Reports, Microsoft Defender for Cloud Apps (App Governance), Microsoft Defender for Office 365 (including Advanced Hunting, Attack Simulation and Training, and One Cyber endpoint protection), Microsoft Forms, Microsoft Planner, Microsoft Priva, Microsoft Purview (including Auditing, Communication Compliance, Compliance Manager, Data Lifecycle Management, Records Manager, Data Loss Prevention, eDiscovery, Information Protection, Unified Feedback Platform, Insider Risk Management, Data Classification Services, Exact Data Match, and ML Inference), Microsoft Teams, Office Collaboration, Office for the Web (formerly called "Office Online"), OneNote Services, Outlook Web Application, PowerPoint Online Document Service, Service Encryption with Customer Key, Query Annotation Service, Real Time Channel, SharePoint Online (including OneDrive, Microsoft 365 Backup, Project Online, Viva Topics, and Viva Connections), Tasks Business Scenario Service, Viva Insights (including Personal Insights), and Whiteboard Customers can download the Microsoft 365 SOC 1 Type 2 Reports for Central and Microservices via the Service Trust Portal .'
sent_lower = ev.lower()

has_return_ctx = bool(re.search(r"\b(?:returns?|refunds?|cancellations?)\b", sent_lower)) and not any(p in sent_lower for p in ("exchange online", "windows 365", "office 365", "soc 1", "soc 2"))
has_window = bool(re.search(r"\b(?:return\s+window|\d+\s+days\b|within\s+\d+\s+days)\b", sent_lower))

print("has_return_ctx:", has_return_ctx)
print("has_window:", has_window)
