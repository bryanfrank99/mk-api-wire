import routeros_api
import asyncio
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

class MikroTikService:
    _executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, host: str, user: str, password: str, port: int = 8750):
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.connection = None
        self.api = None

    def _connect(self):
        # Using plaintext_login=True for broader compatibility with newer/older ROS versions
        # but using the API protocol on the specified port
        self.connection = routeros_api.RouterOsApiPool(
            self.host, 
            username=self.user, 
            password=self.password, 
            port=self.port,
            plaintext_login=True
        )
        self.api = self.connection.get_api()

    async def add_peer(self, interface: str, public_key: str, allowed_address: str, comment: str) -> Dict[str, Any]:
        return await asyncio.get_event_loop().run_in_executor(
            self._executor,
            self._sync_add_peer,
            interface, public_key, allowed_address, comment
        )

    def _sync_add_peer(self, interface: str, public_key: str, allowed_address: str, comment: str):
        if not self.api: self._connect()
        peers = self.api.get_resource('/interface/wireguard/peers')
        return peers.add(
            interface=interface,
            **{"public-key": public_key},
            **{"allowed-address": allowed_address},
            comment=comment
        )

    async def remove_peer(self, public_key: str) -> bool:
        return await asyncio.get_event_loop().run_in_executor(
            self._executor,
            self._sync_remove_peer,
            public_key
        )

    def _sync_remove_peer(self, public_key: str):
        if not self.api: self._connect()
        peers_resource = self.api.get_resource('/interface/wireguard/peers')
        peers = peers_resource.get(**{"public-key": public_key})
        
        if not peers:
            return False
            
        peer_id = peers[0]['id']
        peers_resource.remove(id=peer_id)
        return True

    async def get_health(self) -> bool:
        try:
            return await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._sync_get_health
            )
        except Exception:
            return False

    def _sync_get_health(self):
        if not self.api: self._connect()
        resource = self.api.get_resource('/system/resource')
        return len(resource.get()) > 0

    async def __aenter__(self):
        # Connection is deferred to the first call or we can do it here
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self.connection.disconnect
            )
