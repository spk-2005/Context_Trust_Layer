from app.ingestion.base import BaseConnector, RawDocumentPayload


class SlackConnector(BaseConnector):
    async def fetch_document(self, external_id: str) -> RawDocumentPayload:
        return RawDocumentPayload(
            title=f"Slack Message {external_id}",
            content="",
            source_type="slack",
            external_id=external_id,
            document_type="message",
        )
