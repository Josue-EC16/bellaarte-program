"""boutique inventory schema

Revision ID: 20260413_0002
Revises: 20260408_0001
Create Date: 2026-04-13 01:00:00.000000
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260413_0002"
down_revision = "20260408_0001"
branch_labels = None
depends_on = None


tamano_enum = postgresql.ENUM("PEQUEÑO", "MEDIANO", "GRANDE", name="TAMANO", create_type=False)
tipo_vestido_enum = postgresql.ENUM(
    "VESTIDO DE NOVIA",
    "VESTIDO DE CIVIL",
    "VESTIDO DE 15 AÑOS",
    "VESTIDO DE FIESTA O EVENTO",
    "VESTIDO DE NIÑA",
    "DAMAS",
    "OTRO",
    name="TIPO_VESTIDO",
    create_type=False,
)
copa_talla_enum = postgresql.ENUM(
    "COPA AA",
    "COPA A",
    "COPA B",
    "COPA C",
    "COPA D",
    "COPA DD",
    "COPA E",
    "COPA F",
    "COPA G",
    name="COPA_TALLA_VESTIDO_BOUTIQUE",
    create_type=False,
)
talla_vestido_enum = postgresql.ENUM(
    "TALLA XXS",
    "TALLA XS",
    "TALLA S",
    "TALLA M",
    "TALLA L",
    "TALLA XL",
    "TALLA XXL",
    "TALLA XXXL",
    name="TALLA_VESTIDO_BOUTIQUE",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM("PEQUEÑO", "MEDIANO", "GRANDE", name="TAMANO").create(bind, checkfirst=True)
    postgresql.ENUM(
        "VESTIDO DE NOVIA",
        "VESTIDO DE CIVIL",
        "VESTIDO DE 15 AÑOS",
        "VESTIDO DE FIESTA O EVENTO",
        "VESTIDO DE NIÑA",
        "DAMAS",
        "OTRO",
        name="TIPO_VESTIDO",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "COPA AA",
        "COPA A",
        "COPA B",
        "COPA C",
        "COPA D",
        "COPA DD",
        "COPA E",
        "COPA F",
        "COPA G",
        name="COPA_TALLA_VESTIDO_BOUTIQUE",
    ).create(bind, checkfirst=True)
    postgresql.ENUM(
        "TALLA XXS",
        "TALLA XS",
        "TALLA S",
        "TALLA M",
        "TALLA L",
        "TALLA XL",
        "TALLA XXL",
        "TALLA XXXL",
        name="TALLA_VESTIDO_BOUTIQUE",
    ).create(bind, checkfirst=True)

    op.create_table(
        "TIPO_ITEM_BOUTIQUE",
        sa.Column("TIB_ID", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("TIB_NOM", sa.String(length=100), nullable=False),
        sa.Column("TIB_DES", sa.String(length=200), nullable=True),
        sa.Column("TIB_HAB", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("TIB_FEC_REG", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("TIB_NOM", name="UQ_TIB_NOM"),
    )

    op.create_table(
        "ITEM_BOUTIQUE",
        sa.Column("ITB_ID", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("TIB_ID", sa.BigInteger(), nullable=False),
        sa.Column("ITB_COD", sa.String(length=40), nullable=False),
        sa.Column("ITB_NOM", sa.String(length=150), nullable=False),
        sa.Column("ITB_COLOR", sa.String(length=60), nullable=False),
        sa.Column("ITB_FORMA", sa.String(length=60), nullable=True),
        sa.Column("ITB_MATERIAL", sa.String(length=100), nullable=False),
        sa.Column("ITB_MEDIDAS", sa.Text(), nullable=True),
        sa.Column("ITB_PROVEEDOR", sa.String(length=100), nullable=True),
        sa.Column("ITB_DES", sa.Text(), nullable=True),
        sa.Column("ITB_PRECIO_COMPRA", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("ITB_PRECIO_VENTA", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("ITB_STOCK", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("ITB_STOCK_MIN", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("ITB_ESTADO", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ITB_OBS", sa.Text(), nullable=True),
        sa.Column("ITB_FEC_REG", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["TIB_ID"],
            ["TIPO_ITEM_BOUTIQUE.TIB_ID"],
            name="FK_ITB_TIB",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint('"ITB_PRECIO_COMPRA" >= 0', name="CK_ITB_PRECIO_COMPRA"),
        sa.CheckConstraint('"ITB_PRECIO_VENTA" >= 0', name="CK_ITB_PRECIO_VENTA"),
        sa.CheckConstraint('"ITB_STOCK" >= 0', name="CK_ITB_STOCK"),
        sa.CheckConstraint('"ITB_STOCK_MIN" >= 0', name="CK_ITB_STOCK_MIN"),
        sa.UniqueConstraint("ITB_COD", name="UQ_ITB_COD"),
    )

    op.create_table(
        "DETALLE_VESTIDO_BOUTIQUE",
        sa.Column("DVB_ID", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ITB_ID", sa.BigInteger(), nullable=False),
        sa.Column("DVB_TIPO_VESTIDO", tipo_vestido_enum, nullable=False),
        sa.Column("DVB_CORTE_FALDA", sa.String(length=100), nullable=True),
        sa.Column("DVB_TIPO_ESCOTE", sa.String(length=100), nullable=True),
        sa.Column("DVB_TIENE_COLA", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("DVB_TIENE_MANGA", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("DVB_TIENE_PEDRERIA", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("DVB_COPA_TALLA", copa_talla_enum, nullable=True),
        sa.Column("DVB_TALLA", talla_vestido_enum, nullable=False),
        sa.Column("DVB_LARGO_FALDA", sa.Numeric(6, 2), nullable=True),
        sa.Column("DVB_OBS", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ITB_ID"],
            ["ITEM_BOUTIQUE.ITB_ID"],
            name="FK_DVB_ITB",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint('"DVB_LARGO_FALDA" IS NULL OR "DVB_LARGO_FALDA" >= 0', name="CK_DVB_LARGO_FALDA"),
        sa.UniqueConstraint("ITB_ID", name="UQ_DVB_ITB_ID"),
    )

    op.create_table(
        "DETALLE_VELO_BOUTIQUE",
        sa.Column("DVE_ID", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ITB_ID", sa.BigInteger(), nullable=False),
        sa.Column("DVE_TIPO_VELO", sa.String(length=50), nullable=False),
        sa.Column("DVE_LARGO", sa.Numeric(6, 2), nullable=True),
        sa.Column("DVE_TAMANO", tamano_enum, nullable=False),
        sa.Column("DVE_CAPAS", sa.SmallInteger(), nullable=True),
        sa.Column("DVE_BORDE", sa.String(length=100), nullable=True),
        sa.Column("DVE_DECORACION", sa.String(length=100), nullable=False),
        sa.Column("DVE_OBS", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ITB_ID"],
            ["ITEM_BOUTIQUE.ITB_ID"],
            name="FK_DVE_ITB",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint('"DVE_LARGO" IS NULL OR "DVE_LARGO" >= 0', name="CK_DVE_LARGO"),
        sa.CheckConstraint('"DVE_CAPAS" IS NULL OR "DVE_CAPAS" > 0', name="CK_DVE_CAPAS"),
        sa.UniqueConstraint("ITB_ID", name="UQ_DVE_ITB_ID"),
    )

    op.create_table(
        "DETALLE_BOUQUET_BOUTIQUE",
        sa.Column("DBO_ID", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("ITB_ID", sa.BigInteger(), nullable=False),
        sa.Column("DBO_TIPO_BOUQUET", sa.String(length=100), nullable=True),
        sa.Column("DBO_TAMANO", tamano_enum, nullable=False),
        sa.Column("DBO_TIPO_FLOR", sa.String(length=100), nullable=True),
        sa.Column("DBO_DECORACION", sa.String(length=100), nullable=True),
        sa.Column("DBO_OBS", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ITB_ID"],
            ["ITEM_BOUTIQUE.ITB_ID"],
            name="FK_DBO_ITB",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("ITB_ID", name="UQ_DBO_ITB_ID"),
    )


def downgrade() -> None:
    op.drop_table("DETALLE_BOUQUET_BOUTIQUE")
    op.drop_table("DETALLE_VELO_BOUTIQUE")
    op.drop_table("DETALLE_VESTIDO_BOUTIQUE")
    op.drop_table("ITEM_BOUTIQUE")
    op.drop_table("TIPO_ITEM_BOUTIQUE")

    bind = op.get_bind()
    postgresql.ENUM(name="TALLA_VESTIDO_BOUTIQUE").drop(bind, checkfirst=True)
    postgresql.ENUM(name="COPA_TALLA_VESTIDO_BOUTIQUE").drop(bind, checkfirst=True)
    postgresql.ENUM(name="TIPO_VESTIDO").drop(bind, checkfirst=True)
    postgresql.ENUM(name="TAMANO").drop(bind, checkfirst=True)
