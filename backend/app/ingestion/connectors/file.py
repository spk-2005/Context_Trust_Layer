from app.ingestion.base import BaseConnector, RawDocumentPayload


class FileConnector(BaseConnector):
    async def fetch_document(self, external_id: str) -> RawDocumentPayload:
        return RawDocumentPayload(
            title=f"File {external_id}",
            content="",
            source_type="file_upload",
            external_id=external_id,
            document_type="document",
        )
