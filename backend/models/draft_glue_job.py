"""DraftGlueJob ORM model — Glue job configuration within draft workspace.

Purpose: Represent a Glue job configuration staged for creation or modification within a draft.

Responsibility: Store Glue job parameters (worker type, IAM role, S3 paths, database config).
No business logic; pure data definition aligned with migration 003.

Ownership: models layer (leaf)
Consumers: DraftRepository, DraftService, LangGraph workflow, Glue job provisioning service

Reference: migration 003_add_draft_tables.py, Backend Module Architecture §2.8
"""

from typing import TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from .draft import Draft


class DraftGlueJob(Base):
    """Glue job configuration entity — staged job definition in draft workspace.

    Attributes:
        id: UUID primary key (String(36), immutable job identifier).
        draft_id: Foreign key to drafts.id (parent draft, NOT NULL).
        job_key: Unique identifier within draft (source-grain format), NOT NULL.
            Format: "{source_system}-{schema_grain}" (e.g., "saptcc-co").
        environment: Target environment (dev/staging/prod), NOT NULL.
        source_system: Source system identifier (saptcc, saptce, etc.), NOT NULL.
        schema_grain: Schema/topic grain identifier, NOT NULL.
        topic_name: Kafka topic name, NOT NULL.
        kafka_secret_name: AWS Secrets Manager key for Kafka credentials, NOT NULL.
        glue_job_name: AWS Glue job name, NOT NULL.
        iam_role: IAM role ARN for Glue job execution, NOT NULL.
        worker_type: Worker type (G.1X/G.2X/G.4X), NOT NULL.
        glue_version: Glue version (5.1 frozen for Phase-1), NOT NULL.
        number_of_workers: Number of workers (CQ-04 unresolved), NOT NULL.
        scheduling_mode: Scheduling mode (CQ-05 unresolved), NOT NULL.
        job_type: Job type (unified frozen for Phase-1), NOT NULL.
        job_version: Job version (0.3.0 frozen for Phase-1), NOT NULL.
        enterprise_function: Enterprise function (CQ-03 unresolved), NOT NULL.
        subgroup: Subgroup identifier (APAC/NA/LATAM frozen), NOT NULL.
        lh_database: Lakehouse database name (CQ-A1 unresolved pattern), NOT NULL.
        s3_warehouse: S3 warehouse path (CQ-A1 unresolved pattern), NOT NULL.
        s3_checkpoint: S3 checkpoint path for streaming state, NOT NULL.
        created_at: UTC timestamp when job was added to draft, NOT NULL.

    Relationships:
        draft: Many-to-one reverse relationship to Draft (owned by Draft.draft_glue_jobs).

    Constraints:
        - Primary key: id
        - Foreign key: draft_id → drafts.id (ON DELETE CASCADE)
        - Unique constraint: (draft_id, job_key) ensures one job per key per draft
        - Not null: all columns

    Immutability:
        - DraftGlueJob entries immutable once created
        - Updates via replacement (event-sourcing pattern)
        - Delete + re-add for modifications

    Job Key Format:
        - Format: "{source_system}-{schema_grain}" (e.g., "saptcc-co", "saptce-vd")
        - Unique per draft (enforced by unique constraint)
        - Identifies which source/grain combination this job handles

    CQ References:
        - CQ-03: enterprise_function field (SPEC vs CORP unresolved)
        - CQ-04: number_of_workers default (1 vs 4 unresolved)
        - CQ-05: scheduling_mode value (Manual vs daily 1AM unresolved)
        - CQ-A1: s3_warehouse/lh_database pattern (unresolved)

    Reference: migration 003_add_draft_tables.py
    """

    __tablename__ = "draft_glue_jobs"

    # Primary Key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="UUID primary key (job identifier)",
    )

    # Foreign Key
    draft_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("drafts.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owning draft (foreign key to drafts.id)",
    )

    # Job Identity
    job_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Unique identifier within draft (source-grain format, e.g., saptcc-co)",
    )

    environment: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Target environment (dev/staging/prod)",
    )

    source_system: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Source system (saptcc, saptce, etc.)",
    )

    schema_grain: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Schema/topic grain identifier",
    )

    # Kafka Configuration
    topic_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Kafka topic name",
    )

    kafka_secret_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="AWS Secrets Manager key for Kafka credentials",
    )

    # Glue Job Configuration
    glue_job_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="AWS Glue job name",
    )

    iam_role: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="IAM role ARN for Glue job execution",
    )

    worker_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Worker type (G.1X/G.2X/G.4X)",
    )

    glue_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Glue version (5.1 frozen for Phase-1)",
    )

    number_of_workers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of workers (CQ-04 unresolved: default 1 vs 4)",
    )

    scheduling_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Scheduling mode (CQ-05 unresolved: Manual vs daily 1AM)",
    )

    job_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Job type (unified frozen for Phase-1)",
    )

    job_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Job version (0.3.0 frozen for Phase-1)",
    )

    # Metadata & Classification
    enterprise_function: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Enterprise function (CQ-03 unresolved: SPEC vs CORP)",
    )

    subgroup: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Subgroup (APAC/NA/LATAM frozen)",
    )

    # Lakehouse & S3 Configuration
    lh_database: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Lakehouse database name (CQ-A1 unresolved: pattern)",
    )

    s3_warehouse: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="S3 warehouse path (CQ-A1 unresolved: pattern)",
    )

    s3_checkpoint: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="S3 checkpoint path for streaming state",
    )

    # Audit Column
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="When this job was added to draft (UTC)",
    )

    # Relationship
    draft: Mapped["Draft"] = relationship(
        "Draft",
        back_populates="draft_glue_jobs",
        lazy="select",
        comment="Owning draft (many-to-one reverse from Draft.draft_glue_jobs)",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "draft_id",
            "job_key",
            name="uq_draft_glue_jobs_draft_key",
        ),
    )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"<DraftGlueJob id={self.id!r} draft_id={self.draft_id!r} job_key={self.job_key!r}>"
