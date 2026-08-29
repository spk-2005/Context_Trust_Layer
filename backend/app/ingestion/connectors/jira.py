from app.ingestion.base import BaseConnector, RawDocumentPayload


class JiraConnector(BaseConnector):
    async def fetch_document(self, external_id: str) -> RawDocumentPayload:
        return RawDocumentPayload(
            title=f"Jira Issue {external_id}",
            content="",
            source_type="jira",
            external_id=external_id,
            document_type="issue",
        )
