"""ValidationReport ORM model — validation result record.

Purpose: Represent a validation result from rules engine execution.

Responsibility: Store validation outcome, status, user message, and technical context.
No business logic; pure data definition aligned with migration 005.

Ownership: models layer (leaf)
Consumers: ValidationRepository, DraftService, ValidationService, LangGraph workflow, API middleware

Reference: migration 005_add_validation_history.py, Backend Module Architecture §2.8
"""

from typing import Optional, Any, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .draft import Draft


class ValidationReport(Base):
    """Validation report entity — recorded validation result.

    Attributes:
        id: UUID primary key (String(36), immutable report identifier).
        draft_id: Foreign key to drafts.id (parent draft, NOT NULL).
        validation_type: Type of validation performed (String(100), NOT NULL).
            Examples: structural, semantic, compliance, pr-readiness, terraform-format
        status: Result status (String(20), NOT NULL).
            Values: PASS, FAIL, WARNING
        rule_id: Optional internal rule identifier (String(255), nullable).
            For traceability and audit logging (not user-facing).
        message: User-safe result message (Text, NOT NULL).
            Describes outcome in human-readable format.
            Never exposes internal/technical details.
        internal_context: Optional technical context for debugging (JSON, nullable).
            Contains technical details, rule violations, error traces.
            Never sent to user; for logging/debugging only.
        created_at: UTC timestamp when validation was recorded (NOT NULL).

    Relationships:
        draft: Many-to-one reverse relationship to Draft (owned by Draft.validation_reports).

    Constraints:
        - Primary key: id
        - Foreign key: draft_id → drafts.id (ON DELETE CASCADE)
        - Not null: id, draft_id, validation_type, status, message, created_at

    Status Values:
        - PASS: Validation passed all checks
        - FAIL: Validation failed; blocks PR creation
        - WARNING: Validation has concerns but does not block PR

    Validation Types:
        - structural: File/job structure validity (e.g., Terraform syntax)
        - semantic: Business rule compliance (e.g., required fields present)
        - compliance: Organizational/governance rules (e.g., naming conventions)
        - pr-readiness: Pre-PR checks (e.g., no blocked issues)
        - terraform-format: Terraform formatting validation
        - glue-job-config: Glue job configuration validation

    Message Guidelines:
        - User-safe: No exception traces, internal paths, secrets
        - Actionable: Describes what failed and how to fix
        - Concise: One-line summary for UI display
        - Language: Plain English, no technical jargon

    Internal Context Format (JSON):
        {
            "rule_id": "TR-001",
            "error_type": "SyntaxError",
            "error_trace": "...",
            "violations": [
                {"path": "saptcc/glue.tf", "line": 42, "reason": "..."}
            ],
            "metadata": {...}
        }

    Immutability:
        - ValidationReport entries immutable once created
        - No updates permitted; only creation and deletion
        - Deletion only via cascade when draft is deleted

    Audit Trail:
        - created_at provides timestamp for audit
        - All validations recorded; never deleted explicitly
        - Cascade deletion preserves draft history when draft is deleted

    Reference: migration 005_add_validation_history.py
    """

    __tablename__ = "validation_reports"

    # Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="UUID primary key (report identifier)",
    )

    # Foreign Key
    draft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drafts.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owning draft (foreign key to drafts.id)",
    )

    # Validation Metadata
    validation_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Type of validation (structural/semantic/compliance/etc.)",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Result status (PASS/FAIL/WARNING)",
    )

    # Traceability
    rule_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Internal rule identifier (not user-facing)",
    )

    # User-Facing Message
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="User-safe message describing result (never exposes internals)",
    )

    # Technical Context
    internal_context: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Technical context for logging/debugging (not sent to user)",
    )

    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="When this validation was recorded (UTC)",
    )

    # Relationship
    draft: Mapped["Draft"] = relationship(
        "Draft",
        back_populates="validation_reports",
        lazy="select",
        comment="Owning draft (many-to-one reverse from Draft.validation_reports)",
    )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<ValidationReport id={self.id!r} draft_id={self.draft_id!r} status={self.status!r}>"
