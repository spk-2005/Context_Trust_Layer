"""Backward compatibility shim for Slack connector."""
from app.ingestion.base import BaseConnector, RawDocumentPayload
from app.ingestion.connectors.slack_connector import SlackConnector

__all__ = ["SlackConnector", "BaseConnector", "RawDocumentPayload"]
