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
# Instalar globalmente para que _() funcione em todo lugar
gettext.install('adbee', os.path.join(PROJECT_DIR, 'po'))

# Importar GTK e dependências
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gio, GLib

# Carregar recursos explicitamente antes de importar os módulos que usam templates
resource = Gio.Resource.load(GRESOURCE_OUT)
resource._register()

# Adicionar o diretório atual ao sys.path para permitir 'import src.main'
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

if __name__ == '__main__':
    # Importar main do pacote src
    # Isso resolve os imports relativos (from .window import ...)
    from src.main import main
    sys.exit(main('1.0.0-dev'))
