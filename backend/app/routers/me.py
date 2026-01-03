from fastapi import APIRouter, Depends, HTTPException, Body
from sqlmodel import Session, select
from typing import Optional
from ..core.deps import get_session
from ..models.database import User, Region, Node, WireGuardPeer
from ..services.wireguard import WireGuardService
from ..core.security import ALGORITHM
from ..core.config import settings
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
import uuid

router = APIRouter()
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    session: Session = Depends(get_session),
    token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=403, detail="Could not validate credentials")
    except JWTError:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    
    user = session.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/region")
async def set_preferred_region(
    region_code: str = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    statement = select(Region).where(Region.code == region_code)
    region = session.exec(statement).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
        
    current_user.preferred_region_id = region.id
    session.add(current_user)
    session.commit()
    return {"message": f"Preferred region set to {region.name}"}

@router.post("/wireguard-config")
async def get_wg_config(
    public_key: str = Body(..., embed=True),
    device_id: str = Body(..., embed=True),
    region: Optional[str] = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Enforce 1 device rule globally
    if current_user.device_id and current_user.device_id != device_id:
        raise HTTPException(status_code=403, detail="Device lock active. Contact admin to reset.")
    
    if not current_user.device_id:
        # Check if another user has this device_id
        statement = select(User).where(User.device_id == device_id)
        other_user = session.exec(statement).first()
        if other_user and other_user.id != current_user.id:
            raise HTTPException(status_code=403, detail="This device is already linked to another account.")
            
        current_user.device_id = device_id
        session.add(current_user)
        session.commit()

    # Determine region
    region_code = region or (session.get(Region, current_user.preferred_region_id).code if current_user.preferred_region_id else "US")
    
    wg_service = WireGuardService(session)
    node = wg_service.get_best_node(region_code)
    
    if not node:
        raise HTTPException(status_code=503, detail="No available nodes in this region")
        
    peer = await wg_service.provision_peer(current_user, node, public_key)
    
    # Generate .conf content (Client-side PrivateKey NOT included!)
    conf = f"""[Interface]
Address = {peer.assigned_ip}/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {node.server_public_key}
Endpoint = {node.endpoint_host}:{node.endpoint_port}
AllowedIPs = {node.allowed_ips}
PersistentKeepalive = 25
"""
    return {"config": conf, "region": region_code, "node": node.name}
