#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""
Script para rodar o ADBee diretamente sem instalação.
Útil para desenvolvimento e testes.

Uso: python run.py
"""

import os
import sys
import subprocess

# Diretório do projeto
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_DIR, 'src')

# Compilar gresource se necessário
GRESOURCE_XML = os.path.join(SRC_DIR, 'adbee.gresource.xml')
GRESOURCE_OUT = os.path.join(SRC_DIR, 'adbee.gresource')

if not os.path.exists(GRESOURCE_OUT) or \
   os.path.getmtime(GRESOURCE_XML) > os.path.getmtime(GRESOURCE_OUT):
    print("Compiling gresource...")
    subprocess.run([
        'glib-compile-resources',
        '--sourcedir=' + SRC_DIR,
        '--target=' + GRESOURCE_OUT,
        GRESOURCE_XML
    ], check=True)

# Setup gettext
import locale
import gettext

locale.bindtextdomain('adbee', os.path.join(PROJECT_DIR, 'po'))
locale.textdomain('adbee')
gettext.install('adbee', os.path.join(PROJECT_DIR, 'po'))

# Importar GTK
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')

from gi.repository import Gio, Gtk, Adw, GLib, GdkPixbuf, Gdk

# Carregar recursos
resource = Gio.Resource.load(GRESOURCE_OUT)
resource._register()

# Importar módulos diretamente (sem imports relativos)
sys.path.insert(0, SRC_DIR)

# Reimplementar imports como não-relativos para dev mode
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

# Carregar módulos na ordem correta
qr_generator = load_module('qr_generator', os.path.join(SRC_DIR, 'qr_generator.py'))
adb_service = load_module('adb_service', os.path.join(SRC_DIR, 'adb_service.py'))

# Agora criar a janela inline para evitar problemas de import
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
        
        self.adb_service_obj = adb_service.AdbService()
        self.qr_generator_obj = qr_generator.QRGenerator()
        
        # Gerar QR code inicial
        self.generate_new_pairing()
        
        # Conectar callback de pareamento bem-sucedido
        self.adb_service_obj.on_paired = self.on_device_paired
    
    @Gtk.Template.Callback()
    def on_generate_clicked(self, button):
        """Handle generate button click."""
        self.generate_new_pairing()
    
    def generate_new_pairing(self):
        """Generate a new pairing code and QR code."""
        # Parar serviço anterior se existir
        self.adb_service_obj.stop()
        
        # Gerar novo código
        service_name, pairing_code = self.adb_service_obj.generate_credentials()
        
        # Atualizar labels
        self.service_name_label.set_label(service_name)
        self.pairing_code_label.set_label(pairing_code)
        self.status_label.set_label("Waiting for device to scan QR code...")
        self.status_label.remove_css_class("success")
        self.status_label.remove_css_class("error")
        
        # Gerar QR code
        qr_data = f"WIFI:T:ADB;S:{service_name};P:{pairing_code};;"
        pixbuf = self.qr_generator_obj.generate(qr_data)
        
        if pixbuf:
            # Usar método não-deprecated para criar texture
            success, png_data = pixbuf.save_to_bufferv('png', [], [])
            if success:
                texture = Gdk.Texture.new_from_bytes(GLib.Bytes.new(png_data))
                self.qr_picture.set_paintable(texture)
        
        # Iniciar serviço mDNS
        self.adb_service_obj.start()
    
    def on_device_paired(self, device_name: str):
        """Callback when a device is successfully paired."""
        GLib.idle_add(self._update_paired_status, device_name)
    
    def _update_paired_status(self, device_name: str):
        """Update UI to show paired status (called on main thread)."""
        self.status_label.set_label("Device paired successfully!")
        self.status_label.add_css_class("success")
        
        toast = Adw.Toast.new(f"✓ {device_name} connected")
        toast.set_timeout(5)
        self.toast_overlay.add_toast(toast)
        
        return False


class AdbeeApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self, version: str):
        super().__init__(
            application_id='io.github.docmine17.adbee',
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.version = version
        self.create_action('quit', lambda *_: self.quit(), ['<primary>q'])
        self.create_action('about', self.on_about_action)

    def do_activate(self):
        """Called when the application is activated."""
        win = self.props.active_window
        if not win:
            win = AdbeeWindow(application=self)
        win.present()

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(
            application_name='ADBee',
            application_icon='io.github.docmine17.adbee',
            developer_name='Gabriel',
            version=self.version,
            developers=['Gabriel'],
            copyright='© 2026 Gabriel',
            license_type=Gtk.License.GPL_3_0,
            website='https://github.com/Docmine17/adbee',
            issue_url='https://github.com/Docmine17/adbee/issues',
            comments='Connect Android devices via ADB WiFi using QR code',
        )
        about.present(self.props.active_window)

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action."""
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f'app.{name}', shortcuts)


if __name__ == '__main__':
    app = AdbeeApplication(version='1.0.0-dev')
    sys.exit(app.run(sys.argv))
