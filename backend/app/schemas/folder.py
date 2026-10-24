import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class FolderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Folder name")
    parent_id: Optional[uuid.UUID] = Field(None, description="Parent folder ID, null for root")
    icon: Optional[str] = Field("folder", max_length=50)
    color: Optional[str] = Field("#3B82F6", max_length=50)


class FolderCreate(FolderBase):
    pass


class FolderUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    icon: Optional[str] = Field(None, max_length=50)
    color: Optional[str] = Field(None, max_length=50)


class FolderMove(BaseModel):
    new_parent_id: Optional[uuid.UUID] = Field(None, description="Target parent ID, null to move to root")


class DocumentMoveRequest(BaseModel):
    destination_folder_id: uuid.UUID = Field(..., description="Target destination folder ID")


class FolderResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    name: str
    depth: int
    is_system: bool
    folder_type: str
    icon: Optional[str] = None
    color: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    direct_documents_count: int = 0
    direct_subfolders_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class FolderTreeNode(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    name: str
    depth: int
    is_system: bool
    folder_type: str
    icon: Optional[str] = None
    color: Optional[str] = None
    direct_documents_count: int = 0
    direct_subfolders_count: int = 0
    children: List["FolderTreeNode"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class FolderMetricsScope(BaseModel):
    is_recursive: bool = True
    evaluated_versions: str = "current_only"
    notice: str = "Metrics and conflicts evaluated within this folder/subtree only. Global policies outside this folder still apply."


class FolderDocumentProcessingState(BaseModel):
    completed: int = 0
    processing: int = 0
    queued: int = 0
    failed: int = 0


class FolderDocumentStageOutcomes(BaseModel):
    parsing_passed: int = 0
    parsing_failed: int = 0
    extraction_passed: int = 0
    extraction_failed: int = 0


class FolderDocumentMetrics(BaseModel):
    total: int = 0
    by_processing_state: FolderDocumentProcessingState = Field(default_factory=FolderDocumentProcessingState)
    by_stage_outcome: FolderDocumentStageOutcomes = Field(default_factory=FolderDocumentStageOutcomes)


class FolderClaimVerificationTiers(BaseModel):
    human_certified: int = 0
    automated_verified_only: int = 0
    awaiting_review: int = 0
    rejected: int = 0


class FolderClaimMetrics(BaseModel):
    total_in_scope: int = 0
    by_verification_tier: FolderClaimVerificationTiers = Field(default_factory=FolderClaimVerificationTiers)


class FolderMetricsResponse(BaseModel):
    folder_id: uuid.UUID
    folder_name: str
    scope: FolderMetricsScope = Field(default_factory=FolderMetricsScope)
    documents: FolderDocumentMetrics = Field(default_factory=FolderDocumentMetrics)
    claims: FolderClaimMetrics = Field(default_factory=FolderClaimMetrics)
    conflicts_detected_in_scope: int = 0
