from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship

class Region(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code: str = Field(unique=True, index=True) # US, MX, PT
    name: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    nodes: List["Node"] = Relationship(back_populates="region")

class Node(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    region_id: UUID = Field(foreign_key="region.id")
    name: str
    endpoint_host: str
    endpoint_port: int = Field(default=51820)
    server_public_key: str
    interface_name: str = Field(default="wg-vpn")
    ipv4_pool_cidr: str # ej: 10.66.10.0/24
    allowed_ips: str = Field(default="0.0.0.0/0, ::/0")
    next_ip_cursor: int = Field(default=2)
    max_capacity: int = Field(default=200)
    current_peers: int = Field(default=0)
    
    mt_host: str
    mt_user: str
    mt_pass: str # Should be encrypted in prod
    mt_api_port: int = Field(default=8750)
    
    status: str = Field(default="UP") # UP, DOWN, MAINTENANCE
    priority: int = Field(default=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    region: Region = Relationship(back_populates="nodes")
    peers: List["WireGuardPeer"] = Relationship(back_populates="node")

class User(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    role: str = Field(default="USER") # ADMIN, USER
    device_id: Optional[str] = Field(default=None, unique=True)
    preferred_region_id: Optional[UUID] = Field(default=None, foreign_key="region.id")
    is_active: bool = Field(default=True)
    assigned_ip: Optional[str] = Field(default=None) # Stable internal IP
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    peers: List["WireGuardPeer"] = Relationship(back_populates="user")

class WireGuardPeer(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id")
    node_id: UUID = Field(foreign_key="node.id")
    client_public_key: str
    assigned_ip: str
    status: str = Field(default="ACTIVE") # ACTIVE, REVOKED
    provisioned_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="peers")
    node: Node = Relationship(back_populates="peers")

class AuditLog(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id")
    action: str
    details: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
