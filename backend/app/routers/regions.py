from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List
from ..core.deps import get_session, get_current_user
from ..models.database import Region, User
from ..schemas.region import RegionRead

router = APIRouter()

@router.get("/", response_model=List[dict])
async def list_available_nodes_for_client(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) 
):
    from ..models.database import Node
    
    # 1. Base query: Active nodes with capacity
    query = (
        select(Node)
        .where(Node.status == "UP")
        .where(Node.current_peers < Node.max_capacity)
    )
    
    # 2. Filter admin_only if user is not ADMIN
    if current_user.role != "ADMIN":
        query = query.where(Node.admin_only == False)

    nodes = session.exec(query).all()
    
    # 3. Return simplified structure for client dropdown
    # We return region_code inside the object for backward compatibility or potential UI grouping
    results = []
    for node in nodes:
        results.append({
            "id": str(node.id),
            "name": f"{node.name} ({node.region.code})", # Display Name: "Miami-01 (US)"
            "region_code": node.region.code,
            "country_name": node.region.name
        })
        
    return results
