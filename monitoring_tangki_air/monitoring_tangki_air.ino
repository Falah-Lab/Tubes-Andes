// ================================================================
//  SISTEM MONITORING TANGKI AIR — Arduino Uno
//  Kelompok  : Tubes Andes
//  Deskripsi : Membaca level air via HC-SR04, menampilkan status
//              lewat LED & piezo, serta mengirim data ke web lokal
// ================================================================
//
//  WIRING:
//    HC-SR04  → VCC : 5V  | GND : GND | Trig : D9 | Echo : D10
//    LED Merah  (Kosong) → D5 — Resistor 220Ω — GND
//    LED Kuning (Rendah) → D4 — Resistor 220Ω — GND
//    LED Hijau  (Normal) → D3 — Resistor 220Ω — GND
//    Piezo Buzzer        → (+) D8 | (−) GND
//
//  FORMAT DATA SERIAL (CSV):
//    STATUS,PERSEN,JARAK_CM
//    Contoh: SEDANG,72,5.20
//
//  PERINTAH MASUK DARI WEB:
//    "SILENT" → matikan piezo manual
// ================================================================


// ── Pin Definitions ─────────────────────────────────────────────
#define TRIG_PIN    9
#define ECHO_PIN    10
#define LED_MERAH   5
#define LED_KUNING  4
#define LED_HIJAU   3
#define PIEZO_PIN   8


// ── Konfigurasi Tangki ───────────────────────────────────────────
#define JARAK_PENUH    2    // cm - jarak sensor ke air saat PENUH
#define JARAK_KOSONG   16   // cm - jarak sensor ke dasar saat KOSONG (16.5cm)


// ── Variabel Global ──────────────────────────────────────────────
unsigned long waktuBacaTerakhir = 0;
int           persenTerakhir    = -1;  // -1 = belum ada data valid
bool          piezoSilent       = false; // true = alarm dimatikan manual


// ================================================================
//  SETUP
// ================================================================
void setup() {
  Serial.begin(9600);

  pinMode(TRIG_PIN,   OUTPUT);
  pinMode(ECHO_PIN,   INPUT);
  pinMode(LED_MERAH,  OUTPUT);
  pinMode(LED_KUNING, OUTPUT);
  pinMode(LED_HIJAU,  OUTPUT);
  pinMode(PIEZO_PIN,  OUTPUT);

  // Test startup: semua LED + piezo sebentar
  digitalWrite(LED_MERAH,  HIGH);
  digitalWrite(LED_KUNING, HIGH);
  digitalWrite(LED_HIJAU,  HIGH);
  tone(PIEZO_PIN, 3000);
  delay(300);
  noTone(PIEZO_PIN);
  delay(500);
  digitalWrite(LED_MERAH,  LOW);
  digitalWrite(LED_KUNING, LOW);
  digitalWrite(LED_HIJAU,  LOW);

  Serial.println("STATUS,PERSEN,JARAK_CM");
}


// ================================================================
//  bacaJarak
//  Kirim pulsa ultrasonik dan ukur jarak ke permukaan air (cm)
//  Return: jarak cm | -1 jika error
// ================================================================
float bacaJarak() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long durasi = pulseIn(ECHO_PIN, HIGH, 6000);
  if (durasi == 0) return -1;

  return durasi / 58.0;
}


// ================================================================
//  hitungPersen
//  Konversi jarak → persentase level air (0–100%)
// ================================================================
int hitungPersen(float jarak) {
  int persen = map((int)jarak, JARAK_KOSONG, JARAK_PENUH, 0, 100);
  return constrain(persen, 0, 100);
}


// ================================================================
//  aturLED
//  Nyalakan LED sesuai level air
//  <= 20% Merah | <= 50% Kuning | > 50% Hijau
// ================================================================
void aturLED(int persen) {
  digitalWrite(LED_MERAH,  LOW);
  digitalWrite(LED_KUNING, LOW);
  digitalWrite(LED_HIJAU,  LOW);

  if      (persen <= 20) digitalWrite(LED_MERAH,  HIGH);
  else if (persen <= 50) digitalWrite(LED_KUNING, HIGH);
  else                   digitalWrite(LED_HIJAU,  HIGH);
}


// ================================================================
//  aturPiezo
//  Bunyi terus saat air kosong (<= 20%), dua nada bergantian
//  FIX: piezoSilent hanya reset jika air benar-benar naik (>20%)
//       dan data valid (bukan 0 dari error sensor)
// ================================================================
void aturPiezo(int persen) {
  if (persen <= 20 && !piezoSilent) {
    // Pola: 400ms nada tinggi → 100ms diam → 400ms nada sedang → 100ms diam
    unsigned long elapsed = millis() % 1000;
    if      (elapsed < 400) tone(PIEZO_PIN, 3800);
    else if (elapsed < 500) noTone(PIEZO_PIN);
    else if (elapsed < 900) tone(PIEZO_PIN, 2800);
    else                    noTone(PIEZO_PIN);

  } else {
    noTone(PIEZO_PIN);

    // Reset piezoSilent HANYA jika air benar-benar naik (21–100%)
    // Tidak reset jika persen = 0 dari error sensor
    if (persen > 20 && persen <= 100) {
      piezoSilent = false;
    }
  }
}


// ================================================================
//  kirimSerial
//  Kirim data CSV ke serial → dibaca web server
//  Format: STATUS,PERSEN,JARAK_CM
// ================================================================
void kirimSerial(int persen, float jarak) {
  String status;
  if      (persen <= 20) status = "KOSONG";
  else if (persen <= 50) status = "RENDAH";
  else if (persen <= 80) status = "SEDANG";
  else                   status = "PENUH";

  Serial.print(status);  Serial.print(",");
  Serial.print(persen);  Serial.print(",");
  Serial.println(jarak, 2);
}


// ================================================================
//  cekPerintah
//  Baca perintah masuk dari web via Serial
//  "SILENT" → set piezoSilent = true → piezo langsung diam
// ================================================================
void cekPerintah() {
  if (Serial.available() > 0) {
    String perintah = Serial.readStringUntil('\n');
    perintah.trim();

    if (perintah == "SILENT") {
      piezoSilent = true;  // tandai alarm dimatikan manual
      noTone(PIEZO_PIN);   // matikan piezo seketika
    }
  }
}


// ================================================================
//  LOOP
// ================================================================
void loop() {
  // 1. Cek perintah masuk dari web (prioritas pertama)
  cekPerintah();

  // 2. Jalankan piezo non-blocking HANYA jika data valid
  //    persenTerakhir = -1 artinya belum ada data → skip piezo
  if (persenTerakhir >= 0) {
    aturPiezo(persenTerakhir);
  }

  // 3. Baca sensor & update setiap 1 detik
  if (millis() - waktuBacaTerakhir >= 1000) {
    waktuBacaTerakhir = millis();

    float jarak = bacaJarak();

    // Jika sensor error → kirim notif, JANGAN ubah persenTerakhir
    // agar piezoSilent tidak ter-reset oleh nilai error
    if (jarak < 0) {
      Serial.println("ERROR,-1,-1");
      return;
    }

    // Data valid → update semua
    persenTerakhir = hitungPersen(jarak);
    aturLED(persenTerakhir);
    kirimSerial(persenTerakhir, jarak);
  }
}
