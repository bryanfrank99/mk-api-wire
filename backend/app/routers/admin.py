from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from ..core.deps import get_session
from ..models.database import User, Region, Node, AuditLog, WireGuardPeer
from ..core.security import get_password_hash
from pydantic import BaseModel
import uuid

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "USER"

class RegionCreate(BaseModel):
    code: str
    name: str

class NodeCreate(BaseModel):
    region_id: uuid.UUID
    name: str
    endpoint_host: str
    endpoint_port: int = 51820
    server_public_key: str
    ipv4_pool_cidr: str
    allowed_ips: str = "0.0.0.0/0, ::/0"
    mt_host: str
    mt_user: str
    mt_pass: str
    mt_api_port: int = 8750
    interface_name: str = "wg-vpn"

@router.post("/users")
async def create_user(user_in: UserCreate, session: Session = Depends(get_session)):
    user = User(
        username=user_in.username,
        password_hash=get_password_hash(user_in.password),
        role=user_in.role
    )
    session.add(user)
    session.commit()
    return {"message": "User created"}

@router.post("/regions")
async def create_region(region_in: RegionCreate, session: Session = Depends(get_session)):
    region = Region(**region_in.dict())
    session.add(region)
    session.commit()
    return region

@router.post("/nodes")
async def create_node(node_in: NodeCreate, session: Session = Depends(get_session)):
    node = Node(**node_in.dict())
    session.add(node)
    session.commit()
    return node

@router.patch("/nodes/{node_id}")
async def update_node(node_id: uuid.UUID, node_in: dict, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    for key, value in node_in.items():
        if key == "region_id" and isinstance(value, str):
            value = uuid.UUID(value)
        setattr(node, key, value)
        
    session.add(node)
    session.commit()
    session.refresh(node)
    return node

@router.delete("/nodes/{node_id}")
async def delete_node(node_id: uuid.UUID, session: Session = Depends(get_session)):
    node = session.get(Node, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Clean up associated peers first to avoid IntegrityError
    peers = session.exec(select(WireGuardPeer).where(WireGuardPeer.node_id == node_id)).all()
    for peer in peers:
        session.delete(peer)
    
    session.delete(node)
    session.commit()
    return {"message": "Node deleted and associated peers cleared"}

from ..services.wireguard import WireGuardService

@router.post("/users/{user_id}/reset-device")
async def reset_device(user_id: uuid.UUID, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.device_id = None
    session.add(user)
    session.commit()
    return {"message": "Device lock reset"}

@router.post("/users/{user_id}/toggle-status")
async def toggle_user_status(user_id: uuid.UUID, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = not user.is_active
    
    # If deactivating, revoke all active peers on MikroTik
    if not user.is_active:
        wg_service = WireGuardService(session)
        await wg_service.revoke_all_user_peers(user)
        
    session.add(user)
    session.commit()
    return {"message": f"User {'activated' if user.is_active else 'deactivated'}", "is_active": user.is_active}

@router.delete("/users/{user_id}")
async def delete_user(user_id: uuid.UUID, session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Revoke peers on MikroTik first
    wg_service = WireGuardService(session)
    await wg_service.revoke_all_user_peers(user)
    
    # Delete associated peers from DB
    peers = session.exec(select(WireGuardPeer).where(WireGuardPeer.user_id == user_id)).all()
    for peer in peers:
        session.delete(peer)
        
    session.delete(user)
    session.commit()
    return {"message": "User and associated peers deleted from DB and MikroTik"}

@router.get("/users")
async def list_users(session: Session = Depends(get_session)):
    return session.exec(select(User)).all()

@router.get("/nodes")
async def list_nodes(session: Session = Depends(get_session)):
    return session.exec(select(Node)).all()

@router.get("/regions")
async def admin_list_regions(session: Session = Depends(get_session)):
    return session.exec(select(Region)).all()

@router.delete("/regions/{region_id}")
async def delete_region(region_id: uuid.UUID, session: Session = Depends(get_session)):
    region = session.get(Region, region_id)
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    
    # Check if region has nodes
    statement = select(Node).where(Node.region_id == region_id)
    nodes = session.exec(statement).all()
    if nodes:
        raise HTTPException(status_code=400, detail="Cannot delete region with associated nodes")
        
    session.delete(region)
    session.commit()
    return {"message": "Region deleted"}

@router.get("/audit-logs")
async def get_logs(session: Session = Depends(get_session)):
    return session.exec(select(AuditLog).order_by(AuditLog.created_at.desc())).all()
