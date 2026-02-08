# SPDX-License-Identifier: GPL-3.0-or-later

import secrets
import socket
import string
import subprocess
import shutil
import time
from typing import Callable

try:
    from zeroconf import Zeroconf, ServiceBrowser, ServiceInfo, ServiceListener, IPVersion
    HAS_ZEROCONF = True
except ImportError:
    HAS_ZEROCONF = False


class AdbPairingListener(ServiceListener):
    """
    Listener para detectar quando o telefone inicia o serviço de pareamento.
    
    Quando o telefone escaneia o QR code, ele anuncia um serviço mDNS.
    Nós detectamos esse serviço e chamamos 'adb pair' automaticamente.
    """
    
    def __init__(self, pairing_code: str, on_paired: Callable[[str], None] | None = None):
        self.pairing_code = pairing_code
        self.on_paired = on_paired
    
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"[mDNS] Service removed: {name}")
    
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        try:
            info: ServiceInfo | None = zc.get_service_info(type_, name)
            if info:
                print(f"[mDNS] Service found: {name}")
                self._pair_device(info)
        except Exception as e:
            print(f"[mDNS] Error processing service '{name}': {e}")
    
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass
    
    def _pair_device(self, info: ServiceInfo) -> None:
        """Executa 'adb pair' quando um dispositivo é detectado."""
        try:
            addresses = info.ip_addresses_by_version(IPVersion.V4Only)
            if not addresses:
                addresses = info.ip_addresses_by_version(IPVersion.All)
            
            if not addresses:
                print("[Error] Could not get device IP address")
                return
            
            ip_address = addresses[0].exploded
            port = info.port
            
            cmd = f"adb pair {ip_address}:{port} {self.pairing_code}"
            print(f"[ADB] Executing: adb pair {ip_address}:{port} ******")
            
            process = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if process.returncode == 0 and "Successfully paired" in process.stdout:
                print(f"[ADB] ✓ Successfully paired with {ip_address}:{port}")
                print(f"[ADB] Waiting for device to announce connection service...")
                
                if self.on_paired:
                    self.on_paired(f"{ip_address}")
            else:
                print(f"[ADB] Pairing failed: {process.stderr or process.stdout}")
                
        except subprocess.TimeoutExpired:
            print("[ADB] Pairing timeout")
        except Exception as e:
            print(f"[ADB] Error during pairing: {e}")


class AdbConnectListener(ServiceListener):
    """
    Listener para detectar serviços de conexão ADB wireless.
    
    Após o pareamento, o telefone anuncia _adb-tls-connect._tcp.local.
    Quando detectamos esse serviço, chamamos 'adb connect' automaticamente.
    """
    
    def __init__(self, on_connected: Callable[[str], None] | None = None):
        self.on_connected = on_connected
        self.connected_devices = set()
        self.last_seen_service = None  # (ip, port)
    
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass
    
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        try:
            info: ServiceInfo | None = zc.get_service_info(type_, name)
            if info:
                self._connect_device(info)
        except Exception as e:
            print(f"[mDNS] Error processing service '{name}': {e}")
    
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass
    
    def _connect_device(self, info: ServiceInfo) -> None:
        """Conecta ao dispositivo quando o serviço de conexão é detectado."""
        try:
            addresses = info.ip_addresses_by_version(IPVersion.V4Only)
            if not addresses:
                addresses = info.ip_addresses_by_version(IPVersion.All)
            
            if not addresses:
                return
            
            ip_address = addresses[0].exploded
            port = info.port

            # Guardar última porta vista para tentativa oportuna pós-pareamento
            self.last_seen_service = (ip_address, port)
            
            device_key = f"{ip_address}:{port}"
            
            # Evitar conectar múltiplas vezes ao mesmo dispositivo
            if device_key in self.connected_devices:
                return
            
            print(f"[mDNS] Connect service found: {ip_address}:{port}")
            
            # Tentar conectar com retries (até 3 vezes)
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                print(f"[ADB] Connecting to {ip_address}:{port} (attempt {attempt}/{max_retries})...")
                
                cmd = f"adb connect {ip_address}:{port}"
                
                process = subprocess.run(
                    cmd.split(),
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                output = (process.stdout + process.stderr).lower()
                
                if process.returncode == 0 and ("connected" in output or "already connected" in output):
                    print(f"[ADB] ✓ Connected to {ip_address}:{port}")
                    self.connected_devices.add(device_key)
                    if self.on_connected:
                        self.on_connected(device_key)
                    return
                else:
                    print(f"[ADB] Connection failed: {output.strip()}")
                    if attempt < max_retries:
                        time.sleep(2)
            
            print(f"[ADB] Gave up connecting to {ip_address}:{port} after {max_retries} attempts.")
                
        except Exception as e:
            print(f"[ADB] Error during connection: {e}")


class AdbService:
    """
    Gerencia o pareamento ADB wireless via QR code.
    
    Fluxo:
    1. Gera um nome de serviço e código de pareamento
    2. Mostra QR code no formato: WIFI:T:ADB;S:<nome>;P:<código>;;
    3. Usuário escaneia no telefone (Opções do dev > Depuração sem fio > Parear com QR)
    4. Telefone anuncia serviço mDNS
    5. PC detecta o serviço e chama 'adb pair' automaticamente
    """
    
    PAIRING_SERVICE_TYPE = "_adb-tls-pairing._tcp.local."
    CONNECT_SERVICE_TYPE = "_adb-tls-connect._tcp.local."
    
    def __init__(self):
        self.zeroconf: Zeroconf | None = None
        self.pairing_browser: ServiceBrowser | None = None
        self.connect_browser: ServiceBrowser | None = None
        self.service_name: str = ""
        self.pairing_code: str = ""
        self.on_paired: Callable[[str], None] | None = None
        self._running = False
    
    def generate_credentials(self) -> tuple[str, str]:
        """
        Gera novas credenciais de pareamento.
        
        Returns:
            Tuple de (service_name, pairing_code)
        """
        # Nome simples, similar ao adb-wifi-py
        self.service_name = "adbee"
        
        # Código de 6 dígitos
        self.pairing_code = str(secrets.randbelow(900000) + 100000)
        
        return self.service_name, self.pairing_code
    
    def has_adb(self) -> bool:
        """Verifica se o comando 'adb' está disponível."""
        return shutil.which("adb") is not None
    
    def start(self):
        """Inicia os browsers mDNS para pareamento e conexão."""
        if not HAS_ZEROCONF:
            print("[Warning] zeroconf library not available, mDNS disabled")
            return
        
        if not self.has_adb():
            print("[Warning] 'adb' command not found in PATH")
            return
        
        if self._running:
            self.stop()
        
        try:
            self.zeroconf = Zeroconf()
            
            # Wrapper para pareamento
            def _handle_paired(device_ip):
                print(f"[ADB] Paired with {device_ip}. Triggering opportunistic connection...")
                # Chamar callback externo
                if self.on_paired:
                    self.on_paired(device_ip)
                # Tentar conectar no último serviço visto
                self.try_connect_last_known()

            # Wrapper para conexão
            def _handle_connected(device_ip):
                print(f"[ADB] Connected to {device_ip}.")
                if self.on_connected:
                    self.on_connected(device_ip)
            
            # Browser para pareamento
            self.pairing_listener_instance = AdbPairingListener(
                pairing_code=self.pairing_code,
                on_paired=_handle_paired
            )
            
            self.pairing_browser = ServiceBrowser(
                self.zeroconf,
                self.PAIRING_SERVICE_TYPE,
                self.pairing_listener_instance
            )
            
            # Browser para conexão
            self.connect_listener_instance = AdbConnectListener(
                on_connected=_handle_connected
            )
            
            self.connect_browser = ServiceBrowser(
                self.zeroconf,
                self.CONNECT_SERVICE_TYPE,
                self.connect_listener_instance
            )
            
            self._running = True
            print(f"[mDNS] Watching for pairing and connection services...")
            
        except Exception as e:
            print(f"[Error] Starting mDNS browser: {e}")

    def try_connect_last_known(self):
        """Try to connect to the last seen connection service immediately by IP:Port."""
        if hasattr(self, 'connect_listener_instance') and self.connect_listener_instance.last_seen_service:
            ip, port = self.connect_listener_instance.last_seen_service
            print(f"[ADB] Opportunistic connection attempt to {ip}:{port}...")
            
            cmd = f"adb connect {ip}:{port}"
            
            # Tentar por 5 segundos, pois o dispositivo pode demorar para abrir a porta após parear
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    process = subprocess.run(
                        cmd.split(),
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    output = (process.stdout + process.stderr).lower()
                    
                    if process.returncode == 0 and ("connected" in output or "already connected" in output):
                        print(f"[ADB] ✓ Opportunistic connection successful to {ip}:{port}")
                        if self.on_connected:
                            self.on_connected(f"{ip}:{port}")
                        return
                    else:
                        print(f"[ADB] Opportunistic connection failed (attempt {attempt}/{max_retries}): {output.strip()}")
                        if attempt < max_retries:
                            time.sleep(1.0)
                            
                except Exception as e:
                    print(f"[ADB] Opportunistic connection error: {e}")
                    if attempt < max_retries:
                        time.sleep(1.0)
            
            print(f"[ADB] Gave up opportunistic connecting to {ip}:{port} after {max_retries} attempts.")
    
    def stop(self):
        """Para os browsers mDNS."""
        for browser in [self.pairing_browser, self.connect_browser]:
            if browser:
                try:
                    browser.cancel()
                except Exception:
                    pass
        
        self.pairing_browser = None
        self.connect_browser = None
        
        if self.zeroconf:
            try:
                self.zeroconf.close()
            except Exception:
                pass
            self.zeroconf = None
        
        self._running = False
