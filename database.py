# ================================================================
#  database.py — Modul Database Supabase AquaMonitor
#  Menggunakan 'requests' murni agar tidak butuh C++ Build Tools
# ================================================================

import time
import requests
import json

# Konfigurasi Supabase
SUPABASE_URL = "https://cczjlxluqvwvvijvyawk.supabase.co"
SUPABASE_KEY = "sb_publishable_2hda1xyT_AFdeKmkteNMVA_As_w4qY9"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"  # Agar Supabase mengembalikan data setelah insert
}

# ================================================================
#  Inisialisasi tabel (Sudah di-handle di Supabase)
# ================================================================
def init_db():
    print("[DB] Menggunakan database Supabase di cloud via REST API.")
    # Uji koneksi sederhana
    try:
        requests.get(f"{SUPABASE_URL}/rest/v1/log_level_air?limit=1", headers=HEADERS, timeout=5)
        print("[DB] Koneksi ke Supabase berhasil!")
    except Exception as e:
        print("[DB ERROR] Gagal terhubung ke Supabase:", e)


# ================================================================
#  Simpan data sensor ke log_level_air
# ================================================================
def simpan_data(status, persen, jarak):
    waktu = time.strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "waktu": waktu,
        "status": status,
        "persen": persen,
        "jarak_cm": jarak
    }
    try:
        requests.post(f"{SUPABASE_URL}/rest/v1/log_level_air", headers=HEADERS, json=data, timeout=5)
    except Exception as e:
        print("[DB ERROR] Gagal menyimpan data:", e)


# ================================================================
#  Mulai alarm — simpan waktu mulai ke log_alarm
#  Return: id alarm yang baru dibuat
# ================================================================
def mulai_alarm():
    waktu = time.strftime("%Y-%m-%d %H:%M:%S")
    data = {"waktu_mulai": waktu}
    try:
        res = requests.post(f"{SUPABASE_URL}/rest/v1/log_alarm", headers=HEADERS, json=data, timeout=5)
        if res.status_code in [200, 201]:
            rows = res.json()
            if len(rows) > 0:
                return rows[0]['id']
    except Exception as e:
        print("[DB ERROR] Gagal mulai alarm:", e)
    return -1


# ================================================================
#  Selesai alarm — update waktu_selesai dan cara_selesai
# ================================================================
def selesai_alarm(alarm_id, cara):
    if alarm_id == -1: return
    waktu = time.strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "waktu_selesai": waktu,
        "cara_selesai": cara
    }
    
    # Update dimana id=alarm_id dan waktu_selesai is null
    params = {
        "id": f"eq.{alarm_id}",
        "waktu_selesai": "is.null"
    }
    
    # Untuk update, kita pakai method PATCH
    patch_headers = HEADERS.copy()
    try:
        requests.patch(f"{SUPABASE_URL}/rest/v1/log_alarm", headers=patch_headers, params=params, json=data, timeout=5)
    except Exception as e:
        print("[DB ERROR] Gagal selesai alarm:", e)


# ================================================================
#  Ambil riwayat terbaru (default 50 data)
# ================================================================
def ambil_riwayat(limit=50):
    params = {
        "order": "id.desc",
        "limit": limit
    }
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/log_level_air", headers=HEADERS, params=params, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print("[DB ERROR] Gagal ambil riwayat:", e)
    return []


# ================================================================
#  Ambil statistik ringkasan
# ================================================================
def ambil_statistik():
    try:
        # 1. Hitung total alarm (Gunakan head request dgn exact count)
        count_headers = HEADERS.copy()
        count_headers["Prefer"] = "count=exact"
        res_alarm = requests.head(f"{SUPABASE_URL}/rest/v1/log_alarm", headers=count_headers, timeout=5)
        
        # PostgREST menaruh jumlah data di header 'Content-Range' (contoh: 0-14/15)
        total_alarm = 0
        if "Content-Range" in res_alarm.headers:
            range_val = res_alarm.headers["Content-Range"]
            total_alarm = int(range_val.split("/")[-1])

        # 2. Ambil semua data (tanpa ERROR) untuk menghitung rata-rata, max, min
        params_data = {
            "status": "neq.ERROR",
            "select": "persen"
        }
        res_data = requests.get(f"{SUPABASE_URL}/rest/v1/log_level_air", headers=HEADERS, params=params_data, timeout=5)
        
        if res_data.status_code == 200:
            data = res_data.json()
            if len(data) > 0:
                persens = [r['persen'] for r in data]
                return {
                    "rata_rata_persen": round(sum(persens) / len(persens), 1),
                    "maks_persen": max(persens),
                    "min_persen": min(persens),
                    "total_data": len(persens),
                    "total_alarm": total_alarm
                }
                
        return {
            "rata_rata_persen": 0, "maks_persen": 0, "min_persen": 0, 
            "total_data": 0, "total_alarm": total_alarm
        }
    except Exception as e:
        print("[DB ERROR] Gagal ambil statistik:", e)
        return {
            "rata_rata_persen": 0, "maks_persen": 0, "min_persen": 0, 
            "total_data": 0, "total_alarm": 0
        }


# ================================================================
#  Ambil riwayat alarm
# ================================================================
def ambil_alarm(limit=50):
    params = {
        "order": "id.desc",
        "limit": limit
    }
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/log_alarm", headers=HEADERS, params=params, timeout=5)
        if res.status_code == 200:
            hasil = []
            for r in res.json():
                if r.get('waktu_mulai') and r.get('waktu_selesai'):
                    try:
                        fmt = "%Y-%m-%d %H:%M:%S"
                        t1  = time.mktime(time.strptime(r['waktu_mulai'], fmt))
                        t2  = time.mktime(time.strptime(r['waktu_selesai'], fmt))
                        detik = int(t2 - t1)
                        r['durasi'] = f"{detik // 60}m {detik % 60}s"
                    except:
                        r['durasi'] = "Berlangsung..."
                else:
                    r['durasi'] = "Berlangsung..."
                hasil.append(r)
            return hasil
    except Exception as e:
        print("[DB ERROR] Gagal ambil alarm:", e)
    return []


# ================================================================
#  Hapus semua data riwayat (reset)
# ================================================================
def hapus_semua():
    try:
        # Hapus dimana id >= 0
        params = {"id": "gte.0"}
        requests.delete(f"{SUPABASE_URL}/rest/v1/log_level_air", headers=HEADERS, params=params, timeout=5)
        requests.delete(f"{SUPABASE_URL}/rest/v1/log_alarm", headers=HEADERS, params=params, timeout=5)
    except Exception as e:
        print("[DB ERROR] Gagal mereset database:", e)
