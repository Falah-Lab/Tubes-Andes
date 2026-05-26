# ================================================================
#  database.py — Modul Database SQLite AquaMonitor
#  Dipanggil dari server.py
#  Tidak perlu install apapun (sqlite3 sudah built-in Python)
# ================================================================

import sqlite3
import time

DB_FILE = 'aquamonitor.db'


# ================================================================
#  Buat koneksi baru (thread-safe: buat & tutup per query)
# ================================================================
def koneksi():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # hasil query bisa diakses seperti dict
    return conn


# ================================================================
#  Inisialisasi tabel saat server pertama kali jalan
# ================================================================
def init_db():
    conn = koneksi()
    cur  = conn.cursor()

    # Tabel riwayat pembacaan sensor
    cur.execute('''
        CREATE TABLE IF NOT EXISTS log_level_air (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            waktu    TEXT    NOT NULL,
            status   TEXT    NOT NULL,
            persen   INTEGER NOT NULL,
            jarak_cm REAL    NOT NULL
        )
    ''')

    # Index waktu agar query riwayat lebih cepat
    cur.execute('''
        CREATE INDEX IF NOT EXISTS idx_waktu
        ON log_level_air (waktu)
    ''')

    # Tabel riwayat alarm
    cur.execute('''
        CREATE TABLE IF NOT EXISTS log_alarm (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            waktu_mulai   TEXT NOT NULL,
            waktu_selesai TEXT,
            cara_selesai  TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("[DB] Database siap:", DB_FILE)


# ================================================================
#  Simpan data sensor ke log_level_air
#  Dipanggil setiap kali Arduino kirim data valid
# ================================================================
def simpan_data(status, persen, jarak):
    waktu = time.strftime("%Y-%m-%d %H:%M:%S")
    conn  = koneksi()
    conn.execute(
        'INSERT INTO log_level_air (waktu, status, persen, jarak_cm) VALUES (?,?,?,?)',
        (waktu, status, persen, jarak)
    )
    conn.commit()
    conn.close()


# ================================================================
#  Mulai alarm — simpan waktu mulai ke log_alarm
#  Return: id alarm yang baru dibuat
# ================================================================
def mulai_alarm():
    waktu = time.strftime("%Y-%m-%d %H:%M:%S")
    conn  = koneksi()
    cur   = conn.execute(
        'INSERT INTO log_alarm (waktu_mulai) VALUES (?)',
        (waktu,)
    )
    alarm_id = cur.lastrowid
    conn.commit()
    conn.close()
    return alarm_id


# ================================================================
#  Selesai alarm — update waktu_selesai dan cara_selesai
#  cara: "MANUAL" atau "OTOMATIS"
# ================================================================
def selesai_alarm(alarm_id, cara):
    waktu = time.strftime("%Y-%m-%d %H:%M:%S")
    conn  = koneksi()
    conn.execute(
        '''UPDATE log_alarm
           SET waktu_selesai = ?, cara_selesai = ?
           WHERE id = ? AND waktu_selesai IS NULL''',
        (waktu, cara, alarm_id)
    )
    conn.commit()
    conn.close()


# ================================================================
#  Ambil riwayat terbaru (default 50 data)
# ================================================================
def ambil_riwayat(limit=50):
    conn = koneksi()
    rows = conn.execute(
        'SELECT * FROM log_level_air ORDER BY id DESC LIMIT ?',
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ================================================================
#  Ambil statistik ringkasan
# ================================================================
def ambil_statistik():
    conn = koneksi()

    stats = conn.execute('''
        SELECT
            ROUND(AVG(persen), 1) AS rata_rata_persen,
            MAX(persen)           AS maks_persen,
            MIN(persen)           AS min_persen,
            COUNT(*)              AS total_data
        FROM log_level_air
        WHERE status != 'ERROR'
    ''').fetchone()

    total_alarm = conn.execute(
        'SELECT COUNT(*) FROM log_alarm'
    ).fetchone()[0]

    conn.close()

    return {
        "rata_rata_persen" : stats["rata_rata_persen"] or 0,
        "maks_persen"      : stats["maks_persen"] or 0,
        "min_persen"       : stats["min_persen"] or 0,
        "total_data"       : stats["total_data"] or 0,
        "total_alarm"      : total_alarm
    }


# ================================================================
#  Ambil riwayat alarm
# ================================================================
def ambil_alarm(limit=50):
    conn = koneksi()
    rows = conn.execute(
        'SELECT * FROM log_alarm ORDER BY id DESC LIMIT ?',
        (limit,)
    ).fetchall()
    conn.close()

    hasil = []
    for r in rows:
        r = dict(r)
        # Hitung durasi jika alarm sudah selesai
        if r['waktu_mulai'] and r['waktu_selesai']:
            fmt = "%Y-%m-%d %H:%M:%S"
            t1  = time.mktime(time.strptime(r['waktu_mulai'],   fmt))
            t2  = time.mktime(time.strptime(r['waktu_selesai'], fmt))
            detik = int(t2 - t1)
            r['durasi'] = f"{detik // 60}m {detik % 60}s"
        else:
            r['durasi'] = "Berlangsung..."
        hasil.append(r)

    return hasil


# ================================================================
#  Hapus semua data riwayat (reset)
# ================================================================
def hapus_semua():
    conn = koneksi()
    conn.execute('DELETE FROM log_level_air')
    conn.execute('DELETE FROM log_alarm')
    conn.execute('DELETE FROM sqlite_sequence WHERE name="log_level_air"')
    conn.execute('DELETE FROM sqlite_sequence WHERE name="log_alarm"')
    conn.commit()
    conn.close()
