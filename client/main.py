import flet as ft
import requests
import os
import uuid
import platform
import hashlib
import ctypes
from wg_utils import generate_wg_keys, WireGuardManager
import pystray
from PIL import Image
import threading
import asyncio
import logging
import sys

# Configurar logging para depuración profunda
logging.basicConfig(
    filename='client_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("--- CLIENT START ---")

CLIENT_VERSION = "3.0"
API_BASE = "http://190.15.158.121:8000/api/v1"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class WireGuardClient(ft.Column):
    def __init__(self, app_page: ft.Page):
        super().__init__()
        self.app_page = app_page
        self.token = None
        self.user_data = None
        self.nodes = [] # Renamed from regions
        self.selected_node_id = None # Renamed from selected_region
        self.device_id = hashlib.sha256(platform.node().encode()).hexdigest()[:12]
        self.wg_manager = WireGuardManager()
        self.is_connected = False
        
        # UI Elements
        self.username = ft.TextField(label="Username", border_radius=10, width=300)
        self.password = ft.TextField(label="Password", password=True, can_reveal_password=True, border_radius=10, width=300)
        self.remember_me = ft.Checkbox(label="Remember Credentials", value=False)
        
        self.node_dropdown = ft.Dropdown(
            label="Select Server",
            width=300,
            border_radius=10,
        )
        self.node_dropdown.on_change = self.on_node_change
        
        self.status_text = ft.Text("Ready", color=ft.Colors.BLUE_400, size=18, weight="bold")
        
        # Elementos internos del botón para control total
        self.conn_icon = ft.Icon(ft.Icons.VPN_LOCK, color=ft.Colors.WHITE, size=20)
        self.conn_label = ft.Text("CONNECT", color=ft.Colors.WHITE, weight="bold")
        
        self.connection_btn = ft.FilledButton(
            content=ft.Row(
                [self.conn_icon, self.conn_label],
                alignment=ft.MainAxisAlignment.CENTER,
                tight=True
            ),
            on_click=self.toggle_connection,
            bgcolor=ft.Colors.GREEN_700,
            width=220,
            height=50,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
        )
        
        self.config_box = ft.TextField(
            label="Current Configuration",
            multiline=True,
            read_only=True,
            min_lines=5,
            max_lines=7,
            text_size=10,
        )
        self.log_container = ft.Container(
            content=self.config_box,
            height=150,
            visible=False,
            padding=5
        )
        
        # View containers
        self.login_view = self.create_login_view()
        self.main_view = self.create_main_view()
        self.main_view.visible = False
        
        # Master Container for consistent look (No borders)
        self.master_container = ft.Container(
            content=ft.Column([
                # Custom Title Bar with Drag Area and Close Button
                ft.Row([
                    ft.WindowDragArea(
                        ft.Container(
                            content=ft.Row([
                                ft.Image(src="/logo.png", width=20, height=20),
                                ft.Text("WG PREMIUM", size=12, weight="bold", color=ft.Colors.GREY_400),
                            ], tight=True),
                            padding=ft.Padding.only(left=15),
                        ),
                        expand=True,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REMOVE,
                        icon_size=16,
                        icon_color=ft.Colors.GREY_600,
                        on_click=self.minimize_to_tray,
                        tooltip="Minimize to Tray",
                        style=ft.ButtonStyle(
                            overlay_color=ft.Colors.BLUE_900,
                        )
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_size=16,
                        icon_color=ft.Colors.GREY_600,
                        on_click=self.exit_app,
                        tooltip="Close App",
                        style=ft.ButtonStyle(
                            overlay_color=ft.Colors.RED_400,
                        )
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=0),
                
                # App Views
                ft.Container(
                    content=ft.Column([
                        self.login_view,
                        self.main_view
                    ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.Padding.only(left=20, right=20, bottom=20),
                )
            ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=400,
            height=680,
            border_radius=25,
            bgcolor=ft.Colors.GREY_900,
            # Sombra más pronunciada para resaltar el modo frameless
            shadow=ft.BoxShadow(
                blur_radius=50, 
                spread_radius=1,
                color=ft.Colors.with_opacity(0.5, ft.Colors.BLACK)
            )
        )
        
        self.controls = [self.master_container]
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        # Load saved credentials if exist
        self.load_saved_credentials()
        
        # Iniciar sistema de bandeja independiente (pystray)
        self.setup_pystray()

    def setup_pystray(self):
        logging.info("Starting setup_pystray...")
        def on_restore(icon, item):
            logging.info("Tray: Restore action triggered")
            # Usar run_task para volver al hilo principal de Flet
            logging.info("Tray: Scheduling restore_window on loop...")
            future = asyncio.run_coroutine_threadsafe(self.restore_window(), self.app_page.loop)
            try:
                # No bloqueamos el hilo de la bandeja, pero logueamos si se programó
                logging.info(f"Tray: Restore scheduled. Future: {future}")
            except Exception as e:
                logging.error(f"Tray: Error scheduling restore: {e}")

        def on_exit(icon, item):
            logging.info("Tray: Exit action triggered")
            asyncio.run_coroutine_threadsafe(self.exit_app(), self.app_page.loop)

        # Cargar imagen inicial
        img_path = os.path.join(BASE_DIR, "assets", "disconnected.ico")
        logging.info(f"Tray: Loading icon from {img_path}")
        
        if not os.path.exists(img_path):
            logging.error(f"Tray: Icon file NOT FOUND at {img_path}")
            return

        try:
            self.tray_img = Image.open(img_path)
            logging.info("Tray: Image opened successfully")
            
            self.tray_icon = pystray.Icon(
                "wg_premium", 
                self.tray_img, 
                "WireGuard Premium",
                menu=pystray.Menu(
                    pystray.MenuItem("Mostrar VPN", on_restore, default=True),
                    pystray.MenuItem("Cerrar", on_exit)
                )
            )
            # El clic principal también restaura
            self.tray_icon.on_activate = on_restore
            
            # Ejecutar en hilo separado para no bloquear la UI
            logging.info("Tray: Starting pystray thread...")
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            logging.info("Tray: Thread started")
        except Exception as e:
            logging.exception(f"Tray: CRITICAL ERROR during setup: {e}")

    async def update_tray_state(self, is_connected):
        logging.info(f"Tray: Updating state to {'Connected' if is_connected else 'Disconnected'}")
        if hasattr(self, 'tray_icon'):
            icon_name = "connected.ico" if is_connected else "disconnected.ico"
            img_path = os.path.join(BASE_DIR, "assets", icon_name)
            try:
                self.tray_icon.icon = Image.open(img_path)
                logging.info("Tray: Icon updated successfully")
            except Exception as e:
                logging.error(f"Tray: Failed to update icon: {e}")

    async def minimize_to_tray(self, e=None):
        try:
            logging.info("UI: Minimizing to tray...")
            self.app_page.window.visible = False
            logging.info("UI: Set visible=False, sending update...")
            self.app_page.update()
            logging.info("UI: Window hidden and update sent")
        except Exception as e:
            logging.error(f"UI: Error during minimize: {e}")

    async def restore_window(self, e=None):
        try:
            logging.info("UI: Starting restore_window sequence...")
            
            logging.info("UI: Step 1 - Setting visible = True")
            self.app_page.window.visible = True
            logging.info("UI: Step 2 - Sending first update")
            self.app_page.update()
            
            logging.info("UI: Step 3 - Setting minimized = False")
            self.app_page.window.minimized = False
            logging.info("UI: Step 4 - Setting focus")
            self.app_page.window.focus()
            
            logging.info("UI: Step 5 - Sending final update")
            self.app_page.update()
            
            logging.info("UI: Window restoration sequence COMPLETE")
        except Exception as e:
            logging.exception(f"UI: CRITICAL ERROR during restore_window: {e}")

    async def exit_app(self, e=None):
        # Detener la bandeja
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        
        # Desconectar WireGuard 
        if self.is_connected:
            self.wg_manager.disconnect()
        # Forzar la salida del programa
        await self.app_page.window.destroy()

    def load_saved_credentials(self):
        # Usar archivo local para máxima compatibilidad
        if os.path.exists(".user_prefs"):
            try:
                with open(".user_prefs", "r") as f:
                    lines = f.read().splitlines()
                    if len(lines) >= 2:
                        self.username.value = lines[0]
                        self.password.value = lines[1]
                        self.remember_me.value = True
            except:
                pass

    def create_login_view(self):
        return ft.Column([
            ft.Text("WireGuard Premium", size=30, weight="bold", color=ft.Colors.BLUE_400),
            ft.Text("Secure Tunneling Architecture", size=14, color=ft.Colors.GREY_400),
            ft.Container(height=20),
            self.username,
            self.password,
            ft.Container(self.remember_me, width=300, padding=ft.Padding.only(left=5)),
            ft.FilledButton(
                content=ft.Text("LOGIN", weight="bold"),
                on_click=self.handle_login,
                width=300,
                height=50,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=12),
                    bgcolor=ft.Colors.BLUE_800,
                    color=ft.Colors.WHITE
                )
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)

    def create_main_view(self):
        return ft.Column([
            ft.Row([
                ft.Text("WG MANAGER", size=20, weight="bold", color=ft.Colors.BLUE_200),
                ft.Container(
                    content=ft.Text(f"V{CLIENT_VERSION} PRO", size=10, weight="bold", color=ft.Colors.BLACK),
                    bgcolor=ft.Colors.BLUE_400,
                    padding=10,
                    border_radius=5
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            ft.Container(
                content=ft.Column([
                    ft.Text("DEVICE INFORMATION", size=10, weight="bold", color=ft.Colors.GREY_500),
                    ft.Row([
                        ft.Icon(ft.Icons.COMPUTER, size=16, color=ft.Colors.GREY_400),
                        ft.Text(f"{platform.node()}", size=14, weight="bold"),
                    ]),
                    ft.Text(f"HWID: {self.device_id.upper()}", size=10, font_family="monospace", color=ft.Colors.GREY_600)
                ], spacing=5),
                padding=15,
                bgcolor=ft.Colors.BLACK38,
                border_radius=15
            ),
            
            self.node_dropdown,
            
            ft.Container(
                content=ft.Column([
                    self.status_text,
                    self.connection_btn,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                padding=10,
            ),
            
            ft.TextButton(
                content=ft.Row([ft.Icon(ft.Icons.LOGOUT, size=16), ft.Text("SIGN OUT")], tight=True),
                on_click=self.handle_logout, 
                style=ft.ButtonStyle(color=ft.Colors.GREY_600)
            ),
            
            # Config/Log Area inside a scrollable container
            self.log_container
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20)

    async def handle_login(self, e):
        try:
            response = requests.post(
                f"{API_BASE}/auth/login",
                headers={"X-Client-Version": CLIENT_VERSION},
                data={"username": self.username.value, "password": self.password.value},
            )
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                
                # Persistir credenciales si se solicita (usando archivo local)
                if self.remember_me.value:
                    with open(".user_prefs", "w") as f:
                        f.write(f"{self.username.value}\n{self.password.value}")
                else:
                    if os.path.exists(".user_prefs"):
                        os.remove(".user_prefs")

                await self.load_available_nodes()
                self.login_view.visible = False
                self.main_view.visible = True
                self.app_page.update()
            else:
                await self.show_message("Invalid credentials")
        except Exception as ex:
            await self.show_message(f"Connection Error: {ex}")

    async def load_available_nodes(self):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Client-Version": CLIENT_VERSION,
        }
        try:
            # Modified endpoint now returns list of available nodes
            # response format: [{"id": "uuid", "name": "NodeName (US)", "region_code": "US"}, ...]
            response = requests.get(f"{API_BASE}/regions/", headers=headers)
            if response.status_code == 200:
                self.nodes = response.json()
                self.node_dropdown.options = [
                    ft.dropdown.Option(n["id"], n["name"]) for n in self.nodes
                ]
            self.app_page.update()
        except:
            pass

    def on_node_change(self, e):
        self.selected_node_id = self.node_dropdown.value

    async def toggle_connection(self, e):
        if self.is_connected:
            await self.disconnect()
        else:
            await self.connect()

    def get_local_keys(self):
        # Save keys in a hidden-ish file to avoid re-generating on every connect
        key_file = ".wg_keys"
        if os.path.exists(key_file):
            with open(key_file, "r") as f:
                lines = f.read().splitlines()
                if len(lines) == 2:
                    return lines[0], lines[1]
        
        priv, pub = generate_wg_keys()
        with open(key_file, "w") as f:
            f.write(f"{priv}\n{pub}")
        return priv, pub

    async def connect(self):
        node_id = self.node_dropdown.value
        if not node_id:
            await self.show_message("Please select a server")
            return
            
        self.status_text.value = "PROVISIONING..."
        self.status_text.color = ft.Colors.AMBER_400
        self.connection_btn.disabled = True
        self.app_page.update()

        priv_key, pub_key = self.get_local_keys()
        headers = {
            "Authorization": f"Bearer {self.token}",
            "X-Client-Version": CLIENT_VERSION,
        }
        payload = {
            "region": node_id, # Sending Node UUID in the 'region' field (Backward Comp.)
            "public_key": pub_key,
            "device_id": self.device_id
        }
        
        try:
            response = requests.post(f"{API_BASE}/me/wireguard-config", headers=headers, json=payload)
            if response.status_code == 200:
                config_data = response.json()
                raw_conf = config_data["config"]
                
                # Get display name for the connected node
                connected_node_name = config_data.get("node", "UNKNOWN")
                
                full_conf = raw_conf.replace("[Interface]", f"[Interface]\nPrivateKey = {priv_key}")
                
                # Intentar conexión automática
                success, msg = self.wg_manager.connect(full_conf)
                
                if success:
                    self.is_connected = True
                    self.status_text.value = f"SECURED: {connected_node_name.upper()}"
                    self.status_text.color = ft.Colors.GREEN_400
                    
                    # Actualizar UI del botón
                    self.conn_label.value = "DISCONNECT"
                    self.conn_icon.name = ft.Icons.STOP
                    self.connection_btn.bgcolor = ft.Colors.RED_700
                    
                    self.config_box.value = full_conf
                    self.log_container.visible = False
                    
                    # Actualizar Tray Icon (pystray)
                    await self.update_tray_state(True)
                    
                    self.app_page.update()
                    await self.show_message("Secure tunnel established!")
                else:
                    self.status_text.value = "DRIVER ERROR"
                    self.status_text.color = ft.Colors.RED_400
                    self.config_box.value = full_conf
                    self.log_container.visible = True
                    await self.show_message(msg)
            else:
                self.status_text.value = "API ERROR"
                await self.show_message(f"Error: {response.json().get('detail')}")
        except Exception as ex:
            await self.show_message(f"Fatal Error: {ex}")
        
        self.connection_btn.disabled = False
        self.connection_btn.update()
        self.app_page.update()

    async def disconnect(self):
        self.status_text.value = "DISCONNECTING..."
        self.app_page.update()
        
        success, msg = self.wg_manager.disconnect()
        if success:
            self.is_connected = False
            self.status_text.value = "READY"
            self.status_text.color = ft.Colors.BLUE_400
            
            # Restaurar UI del botón
            self.conn_label.value = "CONNECT"
            self.conn_icon.name = ft.Icons.VPN_LOCK
            self.connection_btn.bgcolor = ft.Colors.GREEN_700
            
            self.log_container.visible = False
            
            # Restaurar Tray Icon (pystray)
            await self.update_tray_state(False)

            self.app_page.update()
            await self.show_message("Disconnected")
        else:
            await self.show_message(msg)
            
        self.app_page.update()

    async def handle_logout(self, e):
        if self.is_connected:
            await self.disconnect()
        self.token = None
        self.main_view.visible = False
        self.login_view.visible = True
        self.app_page.update()

    async def show_message(self, text):
        self.app_page.overlay.append(ft.SnackBar(content=ft.Text(text), open=True))
        self.app_page.update()

async def main(page: ft.Page):
    # ID único para que Windows no lo agrupe con el proceso genérico de Python
    myappid = 'wg.premium.client.app' 
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass

    page.title = "WireGuard Premium Client"
    
    # Usar ruta absoluta para el icono .ico (Nativo de Windows para la barra de tareas)
    icon_full_path = os.path.join(BASE_DIR, "assets", "icon.ico")
    page.window.icon = icon_full_path
    page.icon = icon_full_path
    
    page.window.width = 400
    page.window.height = 700
    page.window.frameless = True
    page.window.bgcolor = ft.Colors.TRANSPARENT
    page.bgcolor = ft.Colors.TRANSPARENT
    page.theme_mode = ft.ThemeMode.DARK
    
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    client_app = WireGuardClient(page)
    
    # Manejo de cierre sincronizado (evita warnings de Python 3.14/Flet 0.80)
    page.window.prevent_close = True
    async def handle_window_event(e):
        if e.data == "close":
            await client_app.exit_app()
    page.window.on_event = handle_window_event
    
    # Desactivamos el tray de Flet ya que usaremos pystray para mayor fiabilidad
    page.window.tray_icon_visible = False
    
    page.add(client_app)
    page.update()

if __name__ == "__main__":
    # Verificación de privilegios de Administrador (Necesario para WireGuard)
    if platform.system() == "Windows":
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            is_admin = False
            
        if not is_admin:
            # Intentar relanzar con privilegios de administrador
            print("Redirecting to Admin mode...")
            try:
                # El parámetro "runas" solicita elevación en Windows
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", sys.executable, " ".join(sys.argv), None, 1
                )
            except Exception as e:
                print(f"Error al elevar privilegios: {e}")
            sys.exit(0)

    # Usar ft.app para compatibilidad con Flet mas reciente
    ft.app(target=main, assets_dir=os.path.join(BASE_DIR, "assets"))
