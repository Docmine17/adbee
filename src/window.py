# SPDX-License-Identifier: GPL-3.0-or-later

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio, Gdk
from .adb_service import AdbService
from .qr_generator import QRGenerator


@Gtk.Template(resource_path='/io/github/docmine17/adbee/window.ui')
class AdbeeWindow(Adw.ApplicationWindow):
    """Main application window."""
    
    __gtype_name__ = 'AdbeeWindow'
    
    qr_picture: Gtk.Picture = Gtk.Template.Child()
    status_label: Gtk.Label = Gtk.Template.Child()
    service_name_label: Gtk.Label = Gtk.Template.Child()
    pairing_code_label: Gtk.Label = Gtk.Template.Child()
    generate_button: Gtk.Button = Gtk.Template.Child()
    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.adb_service = AdbService()
        self.qr_generator = QRGenerator()
        
        # Conectar callbacks
        self.adb_service.on_paired = self.on_device_paired
        self.adb_service.on_connected = self.on_device_connected
        
        # Gerar QR code inicial
        self.generate_new_pairing()
        
        # Solicitar background mode
        self.request_background()
        
        # Interceptar fechamento da janela
        self.connect('close-request', self.on_close_request)
    
    @Gtk.Template.Callback()
    def on_generate_clicked(self, button):
        """Handle generate button click."""
        self.generate_new_pairing()
    
    def generate_new_pairing(self):
        """Generate a new pairing code and QR code."""
        # Parar serviço anterior se existir
        self.adb_service.stop()
        
        # Gerar novo código
        service_name, pairing_code = self.adb_service.generate_credentials()
        
        # Atualizar labels
        self.service_name_label.set_label(service_name)
        self.pairing_code_label.set_label(pairing_code)
        self.status_label.set_label(_("Waiting for device to scan QR code..."))
        self.status_label.remove_css_class("success")
        self.status_label.remove_css_class("error")
        
        # Gerar QR code
        qr_data = f"WIFI:T:ADB;S:{service_name};P:{pairing_code};;"
        pixbuf = self.qr_generator.generate(qr_data)
        
        if pixbuf:
            # Usar método não-deprecated para criar texture
            success, png_data = pixbuf.save_to_bufferv('png', [], [])
            if success:
                texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(png_data))
                self.qr_picture.set_paintable(texture)
        
        # Iniciar serviço mDNS
        self.adb_service.start()
    
    def on_device_paired(self, device_name: str):
        """Callback when a device is successfully paired."""
        GLib.idle_add(self._update_paired_status, device_name)
    
    def on_device_connected(self, device_name: str):
        """Callback when a device is successfully connected."""
        GLib.idle_add(self._update_connected_status, device_name)
    
    def _update_paired_status(self, device_name: str):
        """Update UI to show paired status (waiting for connection)."""
        self.status_label.set_label(_("Paired! Waiting for connection..."))
        self.status_label.add_css_class("success")
        return False

    def _update_connected_status(self, device_name: str):
        """Update UI to show connected status."""
        self.status_label.set_label(_("Device connected successfully!"))
        
        toast = Adw.Toast.new(f"✓ Connected to {device_name}")
        toast.set_timeout(5)
        self.toast_overlay.add_toast(toast)
        
        return False

    def request_background(self):
        """Solicita permissão para rodar em segundo plano."""
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.Background",
                None
            )
            
            # Chamada síncrona ao portal
            # RequestBackground(parent_window, options) -> handle
            proxy.call_sync(
                "RequestBackground",
                GLib.Variant("(sa{sv})", (
                    "",
                    {
                        "reason": GLib.Variant("s", _("Keep ADB connections active")),
                        "autostart": GLib.Variant("b", True),
                        "commandline": GLib.Variant("as", ['adbee', '--background']),
                    }
                )),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            
            print("[Background] Permission requested successfully")
            self.background_enabled = True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Background] Failed to request background: {e!r}")
            if isinstance(e, GLib.Error):
                print(f"[Background] GError code: {e.code}, domain: {e.domain}")
            self.background_enabled = False

    def on_close_request(self, *args):
        """Ao fechar a janela, esconde se tiver permissão de background."""
        if getattr(self, 'background_enabled', False):
            print("[Background] Hiding window instead of closing")
            self.set_visible(False)
            return True # Retornar True impede a destruição da janela
        return False # Comportamento padrão (destruir)
