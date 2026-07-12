"""Data models for schema metadata used in vector indexing."""

from pydantic import BaseModel


class TableMetadata(BaseModel):
    """Metadata for a single database table."""
    name: str
    comment: str = ""


class ColumnMetadata(BaseModel):
    """Metadata for a single database column."""
    table: str
    column: str
    data_type: str = ""
    comment: str = ""
