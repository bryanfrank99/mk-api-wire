# WireGuard Premium Client & Manager

Solución profesional para la gestión de túneles VPN WireGuard sobre MikroTik v7, con una interfaz de escritorio moderna y arquitectura de seguridad robusta.

## 🚀 Características Principales

### Cliente de Escritorio (Premium UI)
- **Interfaz Flotante**: Diseño moderno y minimalista sin bordes ("frameless") con efectos de desenfoque y sombras profundas.
- **Integración con la Bandeja de Sistema (System Tray)**:
  - Minimización inteligente al área de notificación (System Tray).
  - Icono dinámico que cambia de estado (Verde: Conectado / Gris: Desconectado).
  - Menú contextual para restauración rápida o cierre seguro.
- **Persistencia de Sesión**: Opción de recordar credenciales mediante cifrado local básico.
- **Gestión de Identidad de Dispositivo**: Registro de HWID único por máquina para evitar duplicidad de sesiones.
- **Logs de Depuración**: Registro en tiempo real de eventos de conexión y errores en `client_debug.log`.

### Infraestructura y Backend
- **Arquitectura Multi-Región**: Selección dinámica de nodos geográficos para la salida de tráfico.
- **Seguridad Cero Conocimiento**: Las claves privadas se generan y almacenan exclusivamente en el cliente; el servidor solo conoce la clave pública.
- **Aislamiento de Peers**: Limpieza automática de configuraciones obsoletas para el mismo usuario.
- **Integración Nativa MikroTik**: Comunicación directa vía REST API con RouterOS v7+.

## 🛠️ Requisitos del Sistema

### Cliente Windows
- **WireGuard**: Debe estar instalado en el sistema ([Descargar aquí](https://www.wireguard.com/install/)).
- **Python 3.10+**: Para ejecución desde código fuente.
- **Dependencias**: `flet`, `pystray`, `Pillow`, `requests`.

### Servidor / MikroTik
- **FastAPI / Python 3.10+**.
- **MikroTik v7.x** con API REST habilitada.

## 📦 Instalación y Ejecución

### 1. Configuración del Backend

#### En Windows:
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python seed.py  # Inicializa datos de prueba
uvicorn app.main:app --reload --port 8000
```

#### En Linux (Ubuntu/Debian):
```bash
cd backend
chmod +x *.sh
./setup-linux.sh   # Instala todo y prepara la DB
./run-linux.sh     # Ejecuta manualmente (se cierra al salir)
```

#### Mantener servidor siempre activo (Linux):
Si quieres que el servidor siga corriendo al cerrar la sesión:
```bash
./deploy-service.sh  # Crea un servicio de sistema (Systemd)
```

### 2. Configuración del Cliente
```bash
cd client
pip install -r requirements.txt
# O manualmente: pip install flet pystray Pillow requests
python main.py
```

## ⚙️ Configuración del MikroTik

Para la correcta gestión, el MikroTik debe estar preparado siguiendo estos pasos:

```routeros
# 1. Habilitar API REST con SSL
/ip service set www-ssl disabled=no port=443

# 2. Crear Grupo con permisos específicos
/user group add name=vpn-mgr policy=read,write,api,rest-api,!telnet,!ssh,!ftp

# 3. Crear Usuario de API
/user add name=api-user group=vpn-mgr password="TU_CONTRASEÑA_SEGURA"

# 4. Preparar Interface WireGuard
/interface wireguard add name=wg-vpn listen-port=51820
/ip address add address=10.66.10.1/24 interface=wg-vpn
```

## 🔍 Resolución de Problemas (Troubleshooting)

- **El icono de bandeja no aparece**: Verifica que no haya procesos de Python huérfanos en el administrador de tareas.
- **Error 'NoneType' object can't be awaited**: Resuelto en la v1.2. Asegúrate de usar Flet 0.8.x con llamadas sincrónicas a `update()`.
- **Fallo de Conector WireGuard**: Asegúrate de ejecutar la aplicación con permisos suficientes para gestionar interfaces de red o que el servicio de WireGuard esté activo.
- **Logs**: Consulta siempre el archivo `client/client_debug.log` para ver el rastro técnico de cualquier error.

## 🛡️ Seguridad y Auditoría
- Hasheo de contraseñas con **Bcrypt**.
- Autenticación mediante **JWT (JSON Web Tokens)**.
- Auditoría completa de cada provisionamiento de peer en la base de datos centralizada.
