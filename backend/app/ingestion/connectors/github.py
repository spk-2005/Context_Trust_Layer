from app.ingestion.base import BaseConnector, RawDocumentPayload


class GitHubConnector(BaseConnector):
    async def fetch_document(self, external_id: str) -> RawDocumentPayload:
        return RawDocumentPayload(
            title=f"GitHub Item {external_id}",
            content="",
            source_type="github",
            external_id=external_id,
            document_type="markdown",
        )
