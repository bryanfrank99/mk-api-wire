from fastapi import HTTPException
from typing import Optional
from sqlmodel import Session, select, func
from ..models.database import Node, Region, WireGuardPeer, User, AuditLog
from .mikrotik import MikroTikService
import ipaddress

class WireGuardService:
    def __init__(self, session: Session):
        self.session = session

    def get_best_node(self, region_code: str) -> Optional[Node]:
        # Select active nodes in region, ordered by health and capacity
        statement = (
            select(Node)
            .join(Region)
            .where(Region.code == region_code)
            .where(Node.status == "UP")
            .where(Node.current_peers < Node.max_capacity)
            .order_by(Node.priority.desc(), Node.current_peers.asc())
        )
        return self.session.exec(statement).first()

    def get_next_ip(self, node: Node) -> str:
        # Get all IPs currently assigned to active or inactive users to avoid conflicts
        used_ips_statement = select(User.assigned_ip).where(User.assigned_ip != None)
        used_ips = set(self.session.exec(used_ips_statement).all())
        
        network = ipaddress.IPv4Network(node.ipv4_pool_cidr, strict=False)
        hosts = list(network.hosts())
        
        # Start from index 1 (usually skipping .1 which is the server)
        # We search throughout the pool for the first gap
        for i in range(1, len(hosts)):
            ip_str = str(hosts[i])
            if ip_str not in used_ips:
                return ip_str
        
        raise HTTPException(status_code=507, detail="No hay IPs disponibles en este nodo.")

    async def provision_peer(self, user: User, node: Node, public_key: str) -> WireGuardPeer:
        # 1. First, check if there's already an ACTIVE peer for this user on this SPECIFIC node
        statement = (
            select(WireGuardPeer)
            .where(WireGuardPeer.user_id == user.id)
            .where(WireGuardPeer.node_id == node.id)
            .where(WireGuardPeer.status == "ACTIVE")
        )
        existing_peer = self.session.exec(statement).first()
        
        is_simulation = "example.com" in node.mt_host

        if existing_peer:
            # CHECK: If the public key has changed, update it on MikroTik
            if existing_peer.client_public_key != public_key:
                try:
                    if not is_simulation:
                        async with MikroTikService(node.mt_host, node.mt_user, node.mt_pass, port=node.mt_api_port) as mt:
                            await mt.add_peer(
                                interface=node.interface_name,
                                public_key=public_key,
                                allowed_address=existing_peer.assigned_ip,
                                comment=f"User: {user.username} (Key Sync)"
                            )
                    existing_peer.client_public_key = public_key
                    self.session.add(existing_peer)
                    self.session.commit()
                except Exception as e:
                    if not is_simulation:
                        raise HTTPException(status_code=502, detail=f"MikroTik Key Sync Error: {str(e)}")
            return existing_peer

        # 2. Revoke existing active peers on other nodes (1-device rule)
        await self.revoke_all_user_peers(user)
        
        # 3. Handle Static IP Assignment
        if user.assigned_ip:
            assigned_ip = user.assigned_ip
        else:
            # First time connecting: Assign a new IP by scanning for available ones
            assigned_ip = self.get_next_ip(node)
            user.assigned_ip = assigned_ip
            self.session.add(user)
            # No longer need to update next_ip_cursor as get_next_ip scans the pool
        
        # 4. Provision on MikroTik
        try:
            async with MikroTikService(node.mt_host, node.mt_user, node.mt_pass, port=node.mt_api_port) as mt:
                comment = f"User: {user.username} | {user.id}"
                await mt.add_peer(
                    interface=node.interface_name,
                    public_key=public_key,
                    allowed_address=assigned_ip,
                    comment=comment
                )
        except Exception as e:
            if is_simulation:
                print(f"WS-SIMULATION-WARNING: MikroTik at {node.mt_host} unreachable. Error: {e}")
            else:
                raise HTTPException(status_code=502, detail=f"MikroTik Error: {str(e)}")
        
        # 5. Save Peer to DB
        peer = WireGuardPeer(
            user_id=user.id,
            node_id=node.id,
            client_public_key=public_key,
            assigned_ip=assigned_ip,
            status="ACTIVE"
        )
        self.session.add(peer)
        
        # Update node count
        node.current_peers += 1
        self.session.add(node)
        
        # Audit Log
        log = AuditLog(
            user_id=user.id,
            action="PROVISION",
            details=f"Provisioned on node {node.name} (Region: {node.region.code}) with persistent IP {assigned_ip}"
        )
        self.session.add(log)
        
        self.session.commit()
        self.session.refresh(peer)
        return peer

    async def revoke_all_user_peers(self, user: User):
        statement = select(WireGuardPeer).where(WireGuardPeer.user_id == user.id).where(WireGuardPeer.status == "ACTIVE")
        active_peers = self.session.exec(statement).all()
        
        for peer in active_peers:
            node = peer.node
            try:
                async with MikroTikService(node.mt_host, node.mt_user, node.mt_pass, port=node.mt_api_port) as mt:
                    await mt.remove_peer(peer.client_public_key)
            except Exception as e:
                # Log error but continue to update DB
                print(f"Error revoking peer on MikroTik: {e}")
            
            peer.status = "REVOKED"
            node.current_peers -= 1
            self.session.add(peer)
            self.session.add(node)
            
        self.session.commit()
