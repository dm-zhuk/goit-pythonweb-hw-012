from alembic import op
import sqlalchemy as sa
from src.database.models import Role

revision = "1c24784c8a30"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("roles", sa.Enum(Role), nullable=False, server_default="user"),
    )


def downgrade():
    op.drop_column("users", "roles")
