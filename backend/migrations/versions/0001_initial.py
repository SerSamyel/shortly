"""Initial schema: users, links and click aggregates

Revision ID: 0001
Revises:
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _link_fk() -> sa.Column:
    return sa.Column(
        "link_id",
        BigId,
        sa.ForeignKey("links.id", ondelete="CASCADE"),
        primary_key=True,
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "links",
        sa.Column("id", BigId, primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column(
            "owner_id",
            BigId,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("target_url", sa.String(2048), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("total_clicks", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.create_table(
        "click_daily",
        _link_fk(),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("clicks", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "click_referrers",
        _link_fk(),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("domain", sa.String(255), primary_key=True),
        sa.Column("clicks", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "click_countries",
        _link_fk(),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("country", sa.String(16), primary_key=True),
        sa.Column("clicks", sa.BigInteger(), nullable=False),
    )
    op.create_table(
        "click_visitors",
        _link_fk(),
        sa.Column("day", sa.Date(), primary_key=True),
        sa.Column("visitor_hash", sa.String(64), primary_key=True),
    )
    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    for table in (
        "processed_events",
        "click_visitors",
        "click_countries",
        "click_referrers",
        "click_daily",
        "links",
        "users",
    ):
        op.drop_table(table)
