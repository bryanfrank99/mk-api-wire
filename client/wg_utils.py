import base64
import os
import platform
import subprocess
import time
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import x25519

def generate_wg_keys():
    private_key = x25519.X25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    
    return (
        base64.b64encode(private_bytes).decode('utf-8'),
        base64.b64encode(public_bytes).decode('utf-8')
    )

class WireGuardManager:
    def __init__(self, interface_name="wg_api_wire"):
        self.interface_name = interface_name
        self.os_type = platform.system()
        self.config_path = os.path.join(os.getcwd(), f"{self.interface_name}.conf")

    def save_config(self, config_content):
        with open(self.config_path, "w") as f:
            f.write(config_content)
        return self.config_path

    def connect(self, config_content):
        path = self.save_config(config_content)
        
        if self.os_type == "Windows":
            # 1. Encontrar el ejecutable
            wg_bin = "wireguard.exe"
            common_paths = [
                os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "WireGuard", "wireguard.exe"),
                "wireguard.exe"
            ]
            for p in common_paths:
                if os.path.exists(p):
                    wg_bin = p
                    break

            try:
                # 2. Intentar limpiar por si el servicio ya existe de una sesión previa colgada
                subprocess.run([wg_bin, "/uninstalltunnelservice", self.interface_name], capture_output=True)
                
                # 3. Instalar el servicio
                result = subprocess.run(
                    [wg_bin, "/installtunnelservice", path], 
                    capture_output=True, 
                    text=True,
                    check=True
                )
                return True, "Conectado (Servicio Windows)"
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr or e.stdout or str(e)
                if "Access is denied" in error_msg or "Acceso denegado" in error_msg:
                    return False, "ERROR: ¡Debes abrir el terminal como ADMINISTRADOR para conectar!"
                return False, f"Error de WireGuard: {error_msg.strip()}"
            except Exception as e:
                return False, f"Error de Sistema: {str(e)}"
        
        elif self.os_type == "Linux":
            try:
                subprocess.run(["wg-quick", "up", path], check=True)
                return True, "Conectado (wg-quick)"
            except Exception as e:
                return False, f"Error en Linux: {str(e)}"
        
        return False, "Sistema operativo no soportado para conexión automática"

    def disconnect(self):
        if self.os_type == "Windows":
            try:
                subprocess.run(["wireguard.exe", "/uninstalltunnelservice", self.interface_name], check=True)
                return True, "Desconectado"
            except:
                return False, "Error al desconectar (¿Estaba conectado?)"
        
        elif self.os_type == "Linux":
            try:
                subprocess.run(["wg-quick", "down", self.interface_name], check=True)
                return True, "Desconectado"
            except:
                return False, "Error al desconectar"
        
        return False, "Sistema no soportado"
