# 💧 AquaMonitor — Sistem Monitoring Tangki Air IoT

AquaMonitor adalah sistem *Internet of Things* (IoT) terintegrasi yang dirancang untuk memantau level ketinggian air di dalam tangki secara *real-time*. Sistem ini menggabungkan pembacaan sensor secara lokal dengan sinkronisasi ke *cloud database*, memungkinkan pemantauan dan pengendalian jarak jauh melalui perangkat apa pun.

![Screenshot Web](logo.png)

---

## ✨ Fitur Utama
1. **Real-time Monitoring & Cloud Sync**: Data ketinggian air diunggah secara *real-time* ke Supabase dan ditampilkan ke antarmuka web tanpa perlu *refresh*.
2. **Progressive Web App (PWA)**: Website dilengkapi dengan `manifest.json`. Anda bisa menggunakan fitur **"Add to Home Screen"** di *smartphone* (iOS/Android) untuk menginstal web ini layaknya aplikasi *native* dengan logo khusus.
3. **Smart Alarm & 2-Way Communication**: Piezo buzzer berbunyi saat air kosong. Alarm ini dapat dimatikan (*Mute*) dari jarak jauh melalui tombol di Website, yang akan mengirim perintah kembali ke laptop dan diteruskan ke Arduino.
4. **Offline Detection**: Sistem cerdas yang mendeteksi jika kabel USB Arduino dicabut atau program Python dimatikan secara paksa (*Ctrl+C*), lalu memberikan peringatan **"TIDAK TERHUBUNG"** di web.
5. **Sensor Jitter Filter**: Menggunakan algoritma *Exponential Moving Average (EMA)* pada Arduino untuk menyaring "noise" gelombang ultrasonik, menghasilkan angka yang sangat stabil.
6. **Serial Buffer Drain**: Python secara proaktif menguras tumpukan data lama (*buffer lag*) dari Arduino untuk menjamin data yang dikirim ke *cloud* adalah data yang paling *real-time*.

---

## 🧠 Cara Kerja Sistem (Data Flow)

Alur komunikasi data pada AquaMonitor dirancang secara satu arah (untuk data sensor) dan dua arah (untuk kontrol alarm), dengan urutan sebagai berikut:

1. **Sensor & Arduino (Lapisan Perangkat Keras)**
   Sensor ultrasonik HC-SR04 membaca jarak permukaan air. Arduino menyaring data tersebut dengan algoritma EMA untuk mencegah angka melompat. Arduino lalu mencetak string CSV sederhana (contoh: `SEDANG,72,5.20`) ke jalur komunikasi Serial USB setiap 1 detik.
2. **Server Python (Lapisan Jembatan Lokal)**
   Skrip `server.py` yang berjalan di laptop membaca data Serial dari Arduino. Untuk mencegah data basi (*buffer lag*), Python selalu menguras antrean *buffer* serial. Jika data berubah, Python langsung mengirim HTTP POST/PATCH Request ke Supabase *REST API*.
3. **Supabase (Lapisan Cloud Database)**
   Supabase menyimpan data dalam dua tabel utama: `log_level_air` (menyimpan riwayat tinggi air) dan `log_alarm` (menyimpan log kapan alarm menyala dan kapan dimatikan).
4. **Vercel Web (Lapisan Antarmuka Pengguna)**
   Halaman web statis yang di-*hosting* di Vercel melakukan *Fetch* (Tarik Data) ke Supabase setiap 1 detik. Jika pengguna menekan tombol "Matikan Alarm" di web, web akan meng-*update* baris di tabel `log_alarm`. Python yang terus memantau tabel ini akan menyadari perubahan tersebut dan mengirim teks `SILENT\n` ke Arduino melalui kabel USB.

---

## ⚙️ Persiapan Database (Supabase)

Proyek ini tidak menggunakan *backend database* lokal, melainkan **Supabase**. Berikut cara inisiasinya:
1. Buat proyek baru di [Supabase](https://supabase.com/).
2. Masuk ke menu **SQL Editor**.
3. Buka file `setup_supabase.sql` dari repositori ini, salin seluruh kodenya, dan *paste* ke SQL Editor Supabase.
4. Klik **Run**. Script ini akan otomatis:
   - Membuat tabel `log_level_air` dan `log_alarm`.
   - Menyalakan Row Level Security (RLS).
   - Membuat *Policy* publik agar Python dan Web dapat menulis/membaca data secara anonim (bebas akses tanpa login untuk keperluan praktikum).

---

## 🚀 Panduan Deployment & Eksekusi

### 1. Eksekusi Perangkat Keras (Arduino)
- Rangkai komponen HC-SR04, 3 buah LED (Merah, Kuning, Hijau), dan Piezo Buzzer sesuai nomor pin di skrip `monitoring_tangki_air.ino`.
- Buka file `.ino` tersebut di **Arduino IDE**, lalu klik **Upload** ke papan Arduino Uno.

### 2. Eksekusi Jembatan Lokal (Python)
Buka Terminal/Command Prompt di dalam folder proyek ini dan *install* modul yang dibutuhkan:
```bash
pip install pyserial requests
```
*(Opsional: Jika Anda mengubah database Supabase, pastikan Anda mengganti string `SUPABASE_URL` dan `SUPABASE_KEY` di dalam file `server.py` dan `database.py` dengan URL dan Anon Key dari proyek Supabase Anda yang baru).*

Jalankan server penghubung:
```bash
python server.py
```
*(Biarkan jendela terminal ini tetap terbuka selama alat beroperasi).*

### 3. Deploy Web ke Vercel
Karena proyek ini menggunakan antarmuka Vanilla HTML/JS murni, proses *deploy* ke Vercel sangatlah mudah:
1. Dorong (*Push*) seluruh repositori ini ke akun GitHub Anda.
2. Buka [Vercel](https://vercel.com/) dan buat *Project* baru.
3. *Import* repositori GitHub ini.
4. Kosongkan *Build Command* dan *Output Directory* (biarkan *default*).
5. Klik **Deploy**.
6. Dalam hitungan detik, web Anda akan mengudara.

*(Catatan: Pengaturan **Environment Variables** di Vercel tidak diwajibkan dalam arsitektur saat ini, karena Kunci Anonim Supabase diletakkan langsung di dalam `index.html` dan `server.py`. Kunci Anonim Supabase memang dirancang untuk aman diekspos di frontend berkat sistem perlindungan RLS (Row Level Security) dari Supabase).*

---

## 👨‍💻 Tim Pengembang
Dikembangkan sebagai bagian dari Tugas Besar. 
**Kelompok Tubes Andes** - 2026.
