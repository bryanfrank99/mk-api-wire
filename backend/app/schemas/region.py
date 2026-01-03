from pydantic import BaseModel
from uuid import UUID

class RegionRead(BaseModel):
    id: UUID
    code: str
    name: str
    is_active: bool

    class Config:
        from_attributes = True
