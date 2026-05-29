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
    "Prefer": "return=representation"
}

def init_db():
    print("[DB] Menggunakan database Supabase di cloud via REST API.")
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/log_level_air?limit=1", headers=HEADERS, timeout=5)
        if res.status_code == 200:
            print("[DB] Koneksi ke Supabase berhasil!")
        else:
            print(f"[DB ERROR] Koneksi gagal. Status: {res.status_code}, Pesan: {res.text}")
    except Exception as e:
        print("[DB ERROR] Gagal terhubung ke Supabase:", e)

def simpan_data(status, persen, jarak):
    waktu = time.strftime("%Y-%m-%d %H:%M:%S")
    data = {"waktu": waktu, "status": status, "persen": persen, "jarak_cm": jarak}
    try:
        res = requests.post(f"{SUPABASE_URL}/rest/v1/log_level_air", headers=HEADERS, json=data, timeout=5)
        if res.status_code not in [200, 201]:
            print(f"[DB ERROR] Gagal menyimpan data: {res.text}")
    except Exception as e:
        print("[DB ERROR] Gagal menyimpan data:", e)

def mulai_alarm():
    waktu = time.strftime("%Y-%m-%d %H:%M:%S")
    data = {"waktu_mulai": waktu}
    try:
        res = requests.post(f"{SUPABASE_URL}/rest/v1/log_alarm", headers=HEADERS, json=data, timeout=5)
        if res.status_code in [200, 201]:
            rows = res.json()
            if len(rows) > 0:
                return rows[0]['id']
        else:
            print(f"[DB ERROR] Gagal mulai alarm: {res.text}")
    except Exception as e:
        print("[DB ERROR] Gagal mulai alarm:", e)
    return -1

def selesai_alarm(alarm_id, cara):
    if alarm_id == -1: return
    waktu = time.strftime("%Y-%m-%d %H:%M:%S")
    data = {"waktu_selesai": waktu, "cara_selesai": cara}
    params = {"id": f"eq.{alarm_id}", "waktu_selesai": "is.null"}
    try:
        res = requests.patch(f"{SUPABASE_URL}/rest/v1/log_alarm", headers=HEADERS, params=params, json=data, timeout=5)
        if res.status_code not in [200, 201, 204]:
            print(f"[DB ERROR] Gagal selesai alarm: {res.text}")
    except Exception as e:
        print("[DB ERROR] Gagal selesai alarm:", e)

def cek_alarm_selesai(alarm_id):
    if alarm_id == -1: return False
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/log_alarm?id=eq.{alarm_id}&select=waktu_selesai", headers=HEADERS, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if len(data) > 0 and data[0].get('waktu_selesai') is not None:
                return True
    except:
        pass
    return False

def ambil_riwayat(limit=50):
    params = {"order": "id.desc", "limit": limit}
    try:
        res = requests.get(f"{SUPABASE_URL}/rest/v1/log_level_air", headers=HEADERS, params=params, timeout=5)
        if res.status_code == 200:
            return res.json()
    except:
        pass
    return []

def ambil_statistik():
    try:
        count_headers = HEADERS.copy()
        count_headers["Prefer"] = "count=exact"
        res_alarm = requests.head(f"{SUPABASE_URL}/rest/v1/log_alarm", headers=count_headers, timeout=5)
        total_alarm = 0
        if "Content-Range" in res_alarm.headers:
            total_alarm = int(res_alarm.headers["Content-Range"].split("/")[-1])

        params_data = {"status": "neq.ERROR", "select": "persen"}
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
        return {"rata_rata_persen": 0, "maks_persen": 0, "min_persen": 0, "total_data": 0, "total_alarm": total_alarm}
    except:
        return {"rata_rata_persen": 0, "maks_persen": 0, "min_persen": 0, "total_data": 0, "total_alarm": 0}

def ambil_alarm(limit=50):
    params = {"order": "id.desc", "limit": limit}
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
    except:
        pass
    return []

def hapus_semua():
    try:
        requests.delete(f"{SUPABASE_URL}/rest/v1/log_level_air?id=gte.0", headers=HEADERS, timeout=5)
        requests.delete(f"{SUPABASE_URL}/rest/v1/log_alarm?id=gte.0", headers=HEADERS, timeout=5)
    except Exception as e:
        print("[DB ERROR] Gagal mereset database:", e)
