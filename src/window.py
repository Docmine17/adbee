# SPDX-License-Identifier: GPL-3.0-or-later

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')

from gi.repository import Gtk, Adw, GLib, GdkPixbuf, Gio, Gdk
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
