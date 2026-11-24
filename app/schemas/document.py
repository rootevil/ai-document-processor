
from datetime import datetime

from pydantic import BaseModel


class DocumentRecord(BaseModel):
    id: str
    original_filename: str
    stored_filename: str
    content_type: str
    file_size: int
    status: str
    uploaded_at: datetime
