"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# Revision identifiers (managed by Alembic)
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """Apply migration changes (schema upgrade).

    Purpose: Define database schema changes to move FROM the previous revision
    TO this new revision.

    Alembic operations: op.create_table(), op.add_column(), op.create_index(),
    op.create_foreign_key(), etc.

    Pattern: Each upgrade() should:
        1. Be idempotent (safe to run multiple times)
        2. Have a corresponding downgrade() that reverses it
        3. Include data migrations if needed (ALTER TABLE with defaults)
        4. Add comments/documentation for complex changes
    """
    # ${message}
    pass


def downgrade() -> None:
    """Reverse migration changes (schema downgrade).

    Purpose: Define how to UNDO the changes made in upgrade().
    Allows rollback to previous schema version.

    Alembic operations: op.drop_table(), op.drop_column(), op.drop_index(),
    op.drop_constraint(), etc.

    Pattern: downgrade() must be the exact reverse of upgrade().
    """
    # ${message}
    pass

