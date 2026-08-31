from enum import Enum


class OrganizationStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserRole(str, Enum):
    ADMIN = "admin"
    DATA_OWNER = "data_owner"
    REVIEWER = "reviewer"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class RecordStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"
    PROCESSING = "processing"
    FAILED = "failed"


class ClaimStatus(str, Enum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    REJECTED = "rejected"
    OUTDATED = "outdated"
    CONFLICTED = "conflicted"
    ACTIVE = "active"
    SUPERSEDED = "superseded"


class ConflictStatus(str, Enum):
    DETECTED = "detected"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ReviewDecision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    OVERRIDE = "override"
    MARK_OUTDATED = "mark_outdated"
    MERGE = "merge"
    ESCALATE = "escalate"
