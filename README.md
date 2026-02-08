# ADBee

🐝 Connect Android devices via ADB WiFi using QR code.

<img width="450" height="606" alt="image" src="https://github.com/user-attachments/assets/ef1fa328-aa41-4745-a31c-0f8a7680cd37" />



Simply scan the QR code shown in the app with your Android device's "Pair device with QR code" feature in Developer Options.

## Requirements
- Python 3.10+
- GTK4
- Libadwaita
- qrcode (`pip install qrcode`)
- zeroconf (`pip install zeroconf`)
- pypng (`pip install pypng`)

## Running (Development)

```bash
# Install dependencies
pip install qrcode zeroconf pypng

# Run
python run.py
```

## Building with Meson

```bash
meson setup build
meson compile -C build
sudo meson install -C build
```

## How to Use

1. Open the app
2. On your Android device (Android 11+):
   - Go to **Settings > Developer Options > Wireless Debugging**
   - Tap **Pair device with QR code**
   - Scan the QR code shown in ADBee
3. Done! Your device is now paired.

## License

GPL-3.0
