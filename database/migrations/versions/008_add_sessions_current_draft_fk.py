"""Migration 008: add foreign key constraint for sessions.current_draft_id.

Revision ID: 008_add_sessions_current_draft_fk
Revises: 007_add_indexes
Create Date: Database phase 2.3 fix - referential integrity

Purpose: Add missing foreign key constraint from sessions.current_draft_id
to drafts.id. This constraint was deferred in migration 002 but never added.

Background: Migration 002 created sessions.current_draft_id as a nullable column
with a comment "deferred FK to drafts.id", but the constraint was not implemented.
Migration 007 added an INDEX on the column but index ≠ constraint.
This migration completes the referential integrity enforcement.

Constraint details:
  - Foreign key: sessions.current_draft_id → drafts.id
  - ON DELETE SET NULL: If draft is deleted, session.current_draft_id becomes NULL
    (session remains valid; user can create new draft or restore)
  - Nullable: current_draft_id is nullable (session may have no active draft)

Rationale for ON DELETE SET NULL:
  - Preserves session on draft deletion (not CASCADE)
  - Allows session recovery after draft abandonment
  - Semantically correct (session lifetime > draft lifetime)
  - Consistent with application logic (session can exist without active draft)

Reference: Backend Module Architecture §2.8 (Models - Constraints)
          Architecture_Freeze.md §3 (Data model frozen)
          Database design best practices (referential integrity)
"""

from alembic import op
import sqlalchemy as sa

revision = "008_add_sessions_current_draft_fk"
down_revision = "007_add_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add foreign key constraint for sessions.current_draft_id.

    Adds FK: sessions(current_draft_id) → drafts(id) with ON DELETE SET NULL

    Safety: No existing orphaned references expected. Constraint assumes
    data integrity maintained at application layer.
    """
    op.create_foreign_key(
        constraint_name="fk_sessions_current_draft_id",
        source_table="sessions",
        local_cols=["current_draft_id"],
        referent_table="drafts",
        remote_side=["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Drop foreign key constraint for sessions.current_draft_id."""
    op.drop_constraint(
        constraint_name="fk_sessions_current_draft_id",
        table_name="sessions",
        type_="foreignkey",
    )
