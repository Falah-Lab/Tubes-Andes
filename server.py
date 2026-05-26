# ================================================================
#  server.py — Backend Web AquaMonitor
#  Cara pakai:
#    1. pip install pyserial
#    2. py server.py
#    3. Buka browser: http://localhost:8080
# ================================================================

import serial
import serial.tools.list_ports
import threading
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import database as db

# ── Konfigurasi ─────────────────────────────────────────────────
# Kita akan mencoba mendeteksi port secara otomatis jika memungkinkan
SERIAL_PORT = 'COM9'   # Port default fallback
BAUD_RATE   = 9600

# ── State global ────────────────────────────────────────────────
data_tangki = {
    "status" : "TIDAK TERHUBUNG",
    "persen" : 0,
    "jarak"  : 0.0,
    "jam"    : "00:00:00"
}

ser_obj      = None
status_lama  = ""
alarm_id     = None   # id alarm yang sedang berjalan


# ================================================================
#  Thread: baca Serial dari Arduino terus-menerus
# ================================================================
def auto_detect_port():
    ports = serial.tools.list_ports.comports()
    for port, desc, hwid in sorted(ports):
        if "CH340" in desc or "Arduino" in desc or "USB Serial" in desc:
            return port
    if ports:
        return ports[0].device  # Return first available as fallback
    return None

def baca_serial():
    global data_tangki, ser_obj, status_lama, alarm_id
    while True:
        try:
            port_to_use = SERIAL_PORT
            detected = auto_detect_port()
            if detected:
                port_to_use = detected
            
            ser_obj = serial.Serial(port_to_use, BAUD_RATE, timeout=2)
            print(f"[OK] Terhubung ke Arduino di {port_to_use}")
            
            persen_lama = -1

            while True:
                line = ser_obj.readline().decode('utf-8').strip()
                if ',' not in line or line == "STATUS,PERSEN,JARAK_CM":
                    continue

                parts = line.split(',')
                if len(parts) != 3:
                    continue

                status, persen, jarak = parts

                if status == "ERROR":
                    data_tangki["status"] = "ERROR"
                    continue

                persen = int(persen)
                jarak  = float(jarak)

                data_tangki["status"] = status
                data_tangki["persen"] = persen
                data_tangki["jarak"]  = jarak
                data_tangki["jam"]    = time.strftime("%H:%M:%S")

                # Simpan ke database hanya jika persen berubah
                if persen != persen_lama:
                    db.simpan_data(status, persen, jarak)
                    persen_lama = persen

                # Logika alarm database
                if status == "KOSONG" and alarm_id is None:
                    alarm_id = db.mulai_alarm()
                    print(f"[ALARM] Mulai — id: {alarm_id}")

                elif status != "KOSONG" and alarm_id is not None:
                    db.selesai_alarm(alarm_id, "OTOMATIS")
                    print(f"[ALARM] Selesai otomatis — id: {alarm_id}")
                    alarm_id = None

                status_lama = status
                print(f"[DATA] {data_tangki}")

        except serial.SerialException as e:
            print(f"[ERROR] {e} — coba lagi dalam 3 detik...")
            data_tangki["status"] = "TIDAK TERHUBUNG"
            ser_obj = None
            time.sleep(3)


# ================================================================
#  Thread: update jam terus walau Arduino tidak terhubung
# ================================================================
def update_jam():
    while True:
        data_tangki["jam"] = time.strftime("%H:%M:%S")
        time.sleep(1)


# ================================================================
#  HTTP Handler
# ================================================================
class Handler(BaseHTTPRequestHandler):

    def kirim_json(self, data, kode=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(kode)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        params = parse_qs(parsed.query)

        # GET /api/data — data sensor terkini
        if path == '/api/data':
            self.kirim_json(data_tangki)

        # GET /api/riwayat?limit=50
        elif path == '/api/riwayat':
            limit = int(params.get('limit', [50])[0])
            self.kirim_json({"data": db.ambil_riwayat(limit)})

        # GET /api/statistik
        elif path == '/api/statistik':
            self.kirim_json(db.ambil_statistik())

        # GET /api/alarm
        elif path == '/api/alarm':
            self.kirim_json({"alarm": db.ambil_alarm()})

        # GET / — halaman utama
        elif path in ('/', '/index.html'):
            try:
                with open('index.html', 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'index.html tidak ditemukan!')
        elif path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico')):
            try:
                # Remove leading slash to get local filename
                filename = path[1:]
                with open(filename, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                ext = path.split('.')[-1].lower()
                ctype = 'image/jpeg' if ext in ('jpg', 'jpeg') else f'image/{ext}'
                self.send_header('Content-Type', ctype)
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        # POST /api/silent — matikan alarm manual
        if self.path == '/api/silent':
            global alarm_id
            if ser_obj and ser_obj.is_open:
                ser_obj.write(b'SILENT\n')
                print("[INFO] Perintah SILENT dikirim ke Arduino")
            # Tandai alarm selesai manual di database
            if alarm_id is not None:
                db.selesai_alarm(alarm_id, "MANUAL")
                print(f"[ALARM] Dimatikan manual — id: {alarm_id}")
                alarm_id = None
            self.kirim_json({"ok": True})

        # DELETE /api/riwayat (via POST dengan _method=DELETE)
        elif self.path == '/api/reset':
            db.hapus_semua()
            self.kirim_json({"ok": True, "pesan": "Database berhasil direset"})

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()

    def log_message(self, format, *args):
        pass  # nonaktifkan log request


# ================================================================
#  Main
# ================================================================
if __name__ == '__main__':
    # Inisialisasi database
    db.init_db()

    # Jalankan thread serial
    threading.Thread(target=baca_serial, daemon=True).start()

    # Jalankan thread jam
    threading.Thread(target=update_jam, daemon=True).start()

    server = HTTPServer(('localhost', 8080), Handler)
    print("=" * 45)
    print("  Server berjalan di http://localhost:8080")
    print("  Tekan Ctrl+C untuk berhenti")
    print("=" * 45)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Server dihentikan.")
