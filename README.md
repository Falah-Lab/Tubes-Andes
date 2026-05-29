# 💧 AquaMonitor — Sistem Monitoring Tangki Air IoT

AquaMonitor adalah sistem *Internet of Things* (IoT) komprehensif yang dirancang untuk memantau level ketinggian air di dalam tangki secara *real-time*. Sistem ini menggabungkan perangkat keras (Arduino) dengan arsitektur web modern untuk memberikan pengalaman pemantauan yang instan, responsif, dan dapat diakses dari mana saja.

![Screenshot Web](logo.png)

## ✨ Fitur Utama
- **Real-time Monitoring**: Memantau volume air (Persentase & Jarak cm) secara langsung tanpa *delay*.
- **Cloud Database (Supabase)**: Data diunggah ke *cloud* secara efisien menggunakan REST API.
- **Auto-Sync antar Perangkat**: Perubahan status di HP akan langsung mengubah tampilan di layar laptop Anda di detik yang sama.
- **Smart Alarm System**: Piezo buzzer akan berbunyi saat air kosong. Alarm dapat dimatikan dari jarak jauh melalui antarmuka Web Vercel.
- **Progressive Web App (PWA)**: Website dapat diinstal ke layar utama (*Home Screen*) *smartphone* Android & iOS sehingga terasa seperti aplikasi *native*.
- **Deteksi Putus Sambungan**: Web akan otomatis berubah abu-abu dan memunculkan peringatan jika kabel Arduino dicabut atau server dimatikan.
- **Sensor Jitter Filter**: Dilengkapi algoritma *Exponential Moving Average (EMA)* pada Arduino untuk menjamin angka indikator tidak melompat-lompat akibat riak air.

---

## 🛠️ Arsitektur & Teknologi
Proyek ini dibangun menggunakan 3 pilar utama:
1. **Perangkat Keras (Arduino Uno)**: Membaca sensor ultrasonik, menyalakan indikator LED, dan membunyikan alarm.
2. **Server Lokal (Python)**: Bertindak sebagai "jembatan" penghubung. Mengambil data dari Arduino via kabel Serial USB dan mengunggahnya ke *database cloud*.
3. **Frontend Web (Vercel & Supabase)**: Antarmuka cantik bergaya *Glassmorphism* & *Cyberpunk* yang mengambil data secara *real-time* dari Supabase.

---

## 🔌 Skema Rangkaian (Wiring) Arduino
| Komponen | Pin Arduino | Keterangan |
| :--- | :---: | :--- |
| **Sensor HC-SR04** | `5V`, `GND` | Power & Ground |
| | `D9` | Pin Trigger |
| | `D10` | Pin Echo |
| **LED Merah** | `D5` | Menyala saat air **Kosong** (≤ 20%) |
| **LED Kuning** | `D4` | Menyala saat air **Rendah** (21% - 50%) |
| **LED Hijau** | `D3` | Menyala saat air **Normal/Penuh** (> 50%) |
| **Piezo Buzzer** | `D8` | (+) ke D8, (-) ke GND |

*(Catatan: Semua kaki panjang LED dihubungkan ke Pin Digital, dan kaki pendek ke GND menggunakan resistor 220Ω).*

---

## 🚀 Cara Menjalankan Sistem

### 1. Persiapan Perangkat Keras
- Rangkai komponen sesuai tabel *wiring* di atas.
- Buka `monitoring_tangki_air/monitoring_tangki_air.ino` menggunakan **Arduino IDE**.
- Sambungkan Arduino ke laptop dan klik **Upload**.

### 2. Persiapan Server Lokal (Laptop)
Pastikan Python sudah terinstal di laptop Anda. Buka Terminal/Command Prompt di dalam folder proyek ini dan jalankan perintah:
```bash
pip install pyserial requests
```
Setelah modul terinstal, jalankan server:
```bash
python server.py
# atau
py server.py
```
*(Server akan otomatis mendeteksi Port USB Arduino Anda dan langsung mengirim data ke Supabase).*

### 3. Membuka Aplikasi
- Buka tautan Vercel Anda di *browser* HP atau Laptop: `https://tubes-andes.vercel.app`
- Jika ingin memasang aplikasinya di HP, buka web tersebut di Google Chrome (Android) atau Safari (iOS), lalu pilih **"Add to Home Screen"**.

---

## 👨‍💻 Tim Pengembang
Dikembangkan sebagai bagian dari Tugas Besar. 
**Kelompok Tubes Andes** - 2026.
