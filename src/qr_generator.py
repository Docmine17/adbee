# SPDX-License-Identifier: GPL-3.0-or-later

import io
import gi
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

try:
    import png
    HAS_PYPNG = True
except ImportError:
    HAS_PYPNG = False


class QRGenerator:
    """Generates QR codes for ADB pairing."""
    
    def __init__(self):
        self.size = 280
    
    def generate(self, data: str) -> GdkPixbuf.Pixbuf | None:
        """
        Generate a QR code from the given data.
        
        Args:
            data: The string to encode in the QR code
            
        Returns:
            GdkPixbuf.Pixbuf or None if generation fails
        """
        if not HAS_QRCODE:
            print("Warning: qrcode library not available")
            return None
        
        if not HAS_PYPNG:
            print("Warning: pypng library not available")
            return None
        
        try:
            # Criar QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            # Obter a matriz do QR code
            matrix = qr.get_matrix()
            
            # Calcular tamanho de cada "pixel" do QR code
            qr_size = len(matrix)
            box_size = max(1, self.size // qr_size)
            final_size = box_size * qr_size
            
            # Criar imagem PNG usando pypng
            rows = []
            for row in matrix:
                pixel_row = []
                for cell in row:
                    # Preto (0) se True, branco (255) se False
                    color = 0 if cell else 255
                    # Repetir o pixel box_size vezes
                    pixel_row.extend([color] * box_size)
                # Repetir a linha box_size vezes
                for _ in range(box_size):
                    rows.append(pixel_row)
            
            # Salvar em buffer PNG
            buffer = io.BytesIO()
            writer = png.Writer(width=final_size, height=final_size, greyscale=True, bitdepth=8)
            writer.write(buffer, rows)
            buffer.seek(0)
            
            # Carregar como GdkPixbuf
            loader = GdkPixbuf.PixbufLoader.new_with_type('png')
            loader.write(buffer.read())
            loader.close()
            
            return loader.get_pixbuf()
            
        except Exception as e:
            print(f"Error generating QR code: {e}")
            import traceback
            traceback.print_exc()
            return None
