from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List
from ..core.deps import get_session
from ..models.database import Region
from ..schemas.region import RegionRead

router = APIRouter()

@router.get("/", response_model=List[RegionRead])
async def list_regions(session: Session = Depends(get_session)):
    # Only return regions that have at least one node with status UP and capacity available
    from ..models.database import Node
    statement = (
        select(Region)
        .where(Region.is_active == True)
        .join(Node)
        .where(Node.status == "UP")
        .where(Node.current_peers < Node.max_capacity)
        .distinct()
    )
    return session.exec(statement).all()
