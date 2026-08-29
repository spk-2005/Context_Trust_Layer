from app.ingestion.base import BaseConnector, RawDocumentPayload


class ConfluenceConnector(BaseConnector):
    async def fetch_document(self, external_id: str) -> RawDocumentPayload:
        return RawDocumentPayload(
            title=f"Confluence Page {external_id}",
            content="",
            source_type="confluence",
            external_id=external_id,
            document_type="wiki_page",
        )
