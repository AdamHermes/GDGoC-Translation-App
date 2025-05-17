from sqlmodel import SQLModel, Field, Column
from typing import Optional, List

from sqlalchemy import JSON
class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    image_path: str
    ocr_data: Optional[str]
    translation: Optional[str]
    status: str = "pending"
    box: Optional[List[List[List[int]]]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True)
    )

class Text(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ocr_data: Optional[str]
    translation: Optional[str]
    status: str = "pending"
