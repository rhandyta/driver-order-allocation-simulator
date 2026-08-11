# Driver Order Allocation Simulator

Simulasi dan eksperimen terhadap kemungkinan mekanisme alokasi order driver berdasarkan informasi yang tersedia pada fitur **Cek Kondisi Akun Gojek Driver**.

> **Disclaimer**
>
> Proyek ini bukan implementasi algoritma internal Gojek dan tidak mengklaim mengetahui formula, bobot, atau model produksi Gojek.
>
> Model scoring di proyek ini merupakan **hipotesis/reconstruction model** yang dibuat berdasarkan informasi yang tersedia pada materi Gojek Driver dan digunakan untuk eksperimen, analisis, serta pembelajaran.

---

## 1. Tujuan

Project ini bertujuan membuat simulasi:

1. Customer membuat order.
2. Sistem mencari driver yang sedang online.
3. Sistem memfilter driver yang memenuhi kondisi dasar.
4. Sistem menghitung kesesuaian driver terhadap order.
5. Driver kandidat diberi skor.
6. Kandidat di-ranking.
7. Order dialokasikan kepada kandidat dengan skor terbaik.
8. Simulator mencatat hasil dan melakukan eksperimen berulang.

Fokus utama adalah mengetahui bagaimana perubahan:

* demand
* supply
* lokasi
* jarak
* ETA
* jenis layanan
* jam online
* hari online
* acceptance rate
* completion rate
* riwayat layanan
* riwayat area
* riwayat jarak
* riwayat waktu
* kondisi akun/perangkat
* pengaturan trip

dapat memengaruhi peluang seorang driver mendapatkan order.

---

# 2. Dasar Model

Materi Gojek Driver yang digunakan sebagai dasar menyebut bahwa jumlah bid/transaksi dapat dipengaruhi oleh:

* kinerja Mitra;
* tingkat penerimaan bid;
* tingkat penyelesaian trip;
* jam online;
* hari online;
* jumlah permintaan pelanggan dibanding jumlah driver online;
* keberadaan driver di lokasi;
* jam ramai;
* kondisi akun;
* kondisi HP;
* pengaturan trip.

Selain itu, riwayat penyelesaian selama sekitar **7–14 hari terakhir** disebut dapat memengaruhi kesempatan memperoleh trip berikutnya.

Riwayat tersebut mencakup antara lain:

* jenis layanan;
* jarak jemput;
* jarak antar;
* jenis tempat/area;
* titik jemput;
* titik antar;
* jam online.

Sumber yang digunakan dalam pembahasan ini juga menyatakan bahwa faktor terbesar untuk mendapatkan trip tetap jumlah trip pelanggan di sekitar driver.

## Semua poin tersebut berasal dari materi yang diberikan pengguna.

# 3. Model Konseptual

Simulator menggunakan konsep:

```text
                    CUSTOMER ORDER
                          |
                          v
                +-------------------+
                | Candidate Drivers |
                +---------+---------+
                          |
                          v
                  Eligibility Filter
                          |
                          v
                +-------------------+
                | Feature Extraction|
                +---------+---------+
                          |
                          v
                  Matching / Scoring
                          |
                          v
                    Rank Drivers
                          |
                          v
                   Allocate Order
                          |
                          v
                 Update Driver State
                          |
                          v
                   Update History
```

---

# 4. Prinsip Utama

Model tidak menggunakan asumsi:

```text
driver terdekat = pasti mendapatkan order
```

Sebaliknya, simulator menggunakan konsep:

```text
Order Fit =
    Demand/Supply
    + Location Fit
    + Historical Fit
    + Service Fit
    + Time Fit
    + Distance/ETA Fit
    + Performance
    + Online Consistency
```

Bentuk matematis sederhananya:

```text
score(driver, order) =
    w_demand     * demand_score
  + w_location   * location_score
  + w_history    * historical_fit
  + w_service    * service_fit
  + w_time       * time_fit
  + w_distance   * distance_fit
  + w_eta        * eta_fit
  + w_ar         * acceptance_score
  + w_cr         * completion_score
  + w_online     * online_consistency
```

**Bobot di atas adalah parameter eksperimen, bukan bobot resmi Gojek.**

---

# 5. Bobot Awal Eksperimen

Sebagai baseline awal:

| Faktor              | Bobot Awal |
| ------------------- | ---------: |
| Demand / Supply     |         30 |
| Historical Area Fit |         20 |
| Service Fit         |         15 |
| Time Fit            |         10 |
| Distance Fit        |         10 |
| ETA Fit             |          5 |
| Completion Rate     |          5 |
| Acceptance Rate     |          3 |
| Online Consistency  |          2 |
| **Total**           |    **100** |

Bobot tersebut sengaja dibuat sebagai **baseline yang dapat diubah**.

Jangan menganggap:

```text
Demand = 30%
Area = 20%
```

sebagai formula Gojek.

Tujuan eksperimen adalah mencari apakah perubahan bobot tertentu dapat menghasilkan perilaku simulasi yang sesuai dengan pola observasi.

---

# 6. Data Model

## Driver

```python
Driver(
    id,
    location,
    service_types,
    online,
    acceptance_rate,
    completion_rate,
    online_hours,
    online_days,
    history,
    account_status,
    device_status,
    trip_settings
)
```

Contoh:

```python
driver = Driver(
    id="D001",
    location=( -6.9147, 107.6098 ),
    service_types=["GoRide", "GoFood"],
    online=True,
    acceptance_rate=0.98,
    completion_rate=0.99,
    online_hours=72,
    online_days=12,
    history={...},
    account_status="active",
    device_status="healthy",
    trip_settings={}
)
```

---

# 7. Order Model

```python
Order(
    id,
    service_type,
    pickup,
    destination,
    timestamp,
    estimated_distance,
    estimated_duration
)
```

Contoh:

```python
order = Order(
    id="O001",
    service_type="GoFood",
    pickup=(-6.913, 107.610),
    destination=(-6.920, 107.620),
    timestamp="2026-08-11 12:30:00",
    estimated_distance=3.2,
    estimated_duration=18
)
```

---

# 8. Historical Profile

Setiap driver memiliki riwayat 7–14 hari.

Contoh:

```python
history = {
    "services": {
        "GoFood": 32,
        "GoRide": 10,
        "GoSend": 3
    },

    "areas": {
        "area_A": 28,
        "area_B": 12
    },

    "time_slots": {
        "morning": 8,
        "lunch": 22,
        "evening": 15
    },

    "distance_buckets": {
        "0-3km": 24,
        "3-7km": 18,
        "7km+": 3
    }
}
```

---

# 9. Historical Fit

Historical Fit merupakan salah satu komponen terpenting dalam eksperimen.

Misalnya order:

```text
service = GoFood
area = area_A
time = lunch
distance = 3 km
```

Driver dengan riwayat:

```text
GoFood     = tinggi
area_A     = tinggi
lunch      = tinggi
0-3km      = tinggi
```

akan memperoleh `historical_fit` lebih tinggi.

Contoh:

```python
historical_fit = (
    service_history_fit * 0.35
    + area_history_fit * 0.30
    + time_history_fit * 0.20
    + distance_history_fit * 0.15
)
```

Bobot internal ini juga merupakan parameter eksperimen.

---

# 10. Demand / Supply

Simulator harus memiliki kondisi pasar.

Contoh:

```python
market = Market(
    area="area_A",
    active_drivers=50,
    active_orders=120
)
```

Rasio sederhana:

```python
demand_supply_ratio = active_orders / active_drivers
```

Semakin besar rasio:

```text
order banyak
driver sedikit
```

semakin tinggi opportunity.

Contoh normalisasi:

```python
demand_score = normalize(
    active_orders / max(active_drivers, 1)
)
```

> Catatan: formula ini bukan formula resmi Gojek. Ini hanya model simulasi.

---

# 11. Location Fit

Location Fit tidak harus sama dengan jarak geografis.

Minimal simulator dapat menggunakan:

```text
distance to pickup
```

Versi berikutnya dapat menambahkan:

```text
ETA to pickup
traffic
road direction
pickup accessibility
driver zone
```

Contoh:

```python
location_score = distance_score(
    driver.location,
    order.pickup
)
```

---

# 12. Service Fit

Contoh:

```python
if order.service_type in driver.service_types:
    service_fit = 1.0
else:
    service_fit = 0.0
```

Kemudian versi lebih lanjut dapat menggunakan histori:

```python
service_fit = historical_service_ratio(
    driver.history,
    order.service_type
)
```

---

# 13. Time Fit

Order:

```text
GoFood
12:30
```

Driver yang memiliki riwayat aktif:

```text
11:00 - 14:00
```

akan memperoleh time fit lebih tinggi dibanding driver yang biasanya aktif:

```text
06:00 - 09:00
```

Contoh:

```python
time_fit = calculate_time_history_fit(
    driver.history,
    order.timestamp
)
```

---

# 14. Acceptance Rate

Acceptance rate dimasukkan sebagai salah satu komponen performance.

```python
acceptance_score = driver.acceptance_rate
```

Namun simulator tidak boleh membuat asumsi:

```text
AR 100% = pasti mendapatkan order
```

Karena materi Gojek menyatakan bahwa alokasi tidak hanya dipengaruhi faktor kinerja penyelesaian.

---

# 15. Completion Rate

Sama seperti AR:

```python
completion_score = driver.completion_rate
```

Completion rate merupakan faktor kinerja, tetapi bukan satu-satunya faktor.

---

# 16. Online Consistency

Gunakan:

```text
online_hours
online_days
```

dalam window 14 hari.

Contoh sederhana:

```python
online_consistency = (
    normalize(driver.online_hours)
    + normalize(driver.online_days)
) / 2
```

---

# 17. Eligibility Filter

Sebelum scoring, driver harus lolos filter.

Contoh:

```python
def is_eligible(driver, order):

    if not driver.online:
        return False

    if driver.account_status != "active":
        return False

    if order.service_type not in driver.service_types:
        return False

    return True
```

Kondisi akun/perangkat dapat dimodelkan sebagai:

```text
hard constraint
```

atau:

```text
soft score
```

dan simulator harus bisa menguji keduanya.

Materi Gojek menyebut kondisi akun dan HP sebagai faktor yang dapat memengaruhi jumlah bid.

---

# 18. Ranking

Setelah semua driver mendapatkan skor:

```python
ranked = sorted(
    candidates,
    key=lambda driver: driver.score,
    reverse=True
)
```

Hasil:

```text
1. D004  score=91.2
2. D008  score=87.4
3. D002  score=83.1
4. D001  score=80.8
...
```

---

# 19. Jangan Selalu Pilih Rank #1

Untuk simulasi yang lebih realistis, gunakan probabilistic allocation.

Misalnya:

```python
P(driver_i) =
    exp(score_i / temperature)
    --------------------------------
    sum(exp(score_j / temperature))
```

Ini dapat dibuat dengan Softmax.

Contoh:

```python
P(D001) = 0.42
P(D002) = 0.27
P(D003) = 0.18
P(D004) = 0.08
P(D005) = 0.05
```

Kemudian pilih berdasarkan probabilitas.

Keuntungan:

* tidak selalu deterministik;
* dapat mensimulasikan variasi;
* lebih cocok untuk eksperimen Monte Carlo.

---

# 20. Update Setelah Order

Setelah driver mendapatkan order:

```text
accept
   ↓
pickup
   ↓
complete
   ↓
update history
   ↓
update AR
   ↓
update CR
   ↓
update online/trip statistics
```

Jika cancel:

```text
cancel
   ↓
update completion
   ↓
update history
```

---

# 21. Rolling Window 14 Hari

Gunakan rolling window:

```text
Day 1 ... Day 14
```

Ketika masuk Day 15:

```text
hapus Day 1
masukkan Day 15
```

Sehingga:

```text
Window(t) = [t-13, ..., t]
```

Materi Gojek menyatakan performa pada fitur Cek Kondisi Akun menggunakan periode 14 hari terakhir, dengan contoh bahwa jam online dapat berubah karena hari lama keluar dari periode penghitungan.

---

# 22. Eksperimen Utama

Simulator harus mendukung eksperimen berikut.

## Experiment A — Pengaruh AR

Bandingkan:

```text
AR = 70%
AR = 80%
AR = 90%
AR = 95%
AR = 99%
AR = 100%
```

Tetapkan faktor lain sama.

Output:

```text
AR vs Order Probability
```

---

## Experiment B — Pengaruh CR

```text
CR = 70%
CR = 80%
CR = 90%
CR = 95%
CR = 99%
CR = 100%
```

---

## Experiment C — Pengaruh Historical Fit

Bandingkan:

```text
History match = 0%
25%
50%
75%
100%
```

---

## Experiment D — Area

Bandingkan:

```text
Area dengan riwayat
vs
Area baru
```

---

## Experiment E — Demand / Supply

Contoh:

```text
10 orders / 100 drivers
20 orders / 100 drivers
50 orders / 100 drivers
100 orders / 100 drivers
200 orders / 100 drivers
```

---

## Experiment F — Online Consistency

Bandingkan:

```text
2 hari
5 hari
7 hari
10 hari
14 hari
```

---

## Experiment G — Combined Profile

Buat 3 driver:

```text
Driver A
AR tinggi
CR tinggi
History tinggi
Area cocok

Driver B
AR sempurna
CR sempurna
History rendah
Area baru

Driver C
AR sedang
CR sedang
History sangat tinggi
Area sangat cocok
```

Tujuannya melihat apakah:

```text
performance terbaik
```

selalu sama dengan:

```text
allocation probability tertinggi
```

---

# 23. Monte Carlo Simulation

Untuk setiap kondisi:

```python
for iteration in range(10_000):
    generate_orders()
    generate_driver_population()
    run_allocation()
    record_result()
```

Kemudian hitung:

```text
total orders
orders per driver
order probability
average waiting time
service distribution
area distribution
```

Contoh output:

```text
Driver   Orders   Probability   Avg Wait
D001     321      12.8%         8.2 min
D002     287      11.5%         9.4 min
D003     198       7.9%        13.1 min
...
```

---

# 24. Sensitivity Analysis

Tujuan utama proyek adalah mengetahui faktor yang paling sensitif.

Contoh:

```text
Variable             Δ Probability
----------------------------------
Demand               +18.2%
Historical Fit       +13.4%
Area Fit               +9.8%
Service Fit            +7.1%
CR                     +3.2%
AR                     +2.4%
Online Hours           +1.8%
```

Ini dapat digunakan untuk melihat:

> "Jika hanya satu faktor berubah, seberapa besar peluang order berubah?"

---

# 25. Scenario: "Driver Favorit Sistem"

Istilah dalam proyek:

```text
High Historical-Fit Driver
```

bukan:

```text
Favorite Driver
```

Contoh:

```text
Driver A

AR                 98%
CR                 99%
Online days        13/14
Online hours       75
Area history       90%
Service history    95%
Time history       90%
Distance fit       85%
```

Bandingkan dengan:

```text
Driver B

AR                 100%
CR                 100%
Online days        10/14
Online hours       55
Area history       20%
Service history    30%
Time history       40%
Distance fit       50%
```

Simulator harus memungkinkan kita menguji apakah Driver A memperoleh lebih banyak order walaupun AR/CR Driver B lebih tinggi.

---

# 26. Struktur Project Python

```text
order-simulator/
│
├── README.md
├── requirements.txt
│
├── config/
│   └── weights.yaml
│
├── data/
│   ├── drivers.json
│   ├── orders.json
│   └── market.json
│
├── src/
│   ├── main.py
│   ├── models.py
│   ├── eligibility.py
│   ├── features.py
│   ├── scoring.py
│   ├── allocator.py
│   ├── history.py
│   ├── market.py
│   └── simulation.py
│
├── experiments/
│   ├── experiment_ar.py
│   ├── experiment_cr.py
│   ├── experiment_history.py
│   ├── experiment_demand.py
│   └── monte_carlo.py
│
├── tests/
│   ├── test_scoring.py
│   ├── test_history.py
│   └── test_allocator.py
│
└── results/
    ├── csv/
    └── charts/
```

---

# 27. Struktur Project Go

Alternatif implementasi:

```text
order-simulator/
│
├── README.md
├── go.mod
│
├── cmd/
│   └── simulator/
│       └── main.go
│
├── internal/
│   ├── model/
│   ├── eligibility/
│   ├── feature/
│   ├── scoring/
│   ├── allocator/
│   ├── history/
│   ├── market/
│   └── simulation/
│
├── experiments/
│
└── tests/
```

---

# 28. Python Dependencies

Versi awal dapat menggunakan:

```text
numpy
pandas
scipy
scikit-learn
matplotlib
pyyaml
pytest
```

Install:

```bash
pip install -r requirements.txt
```

---

# 29. CLI

Contoh:

```bash
python -m src.main simulate \
    --days 14 \
    --drivers 100 \
    --orders 1000
```

Eksperimen:

```bash
python -m src.main experiment \
    --name acceptance_rate
```

Monte Carlo:

```bash
python -m src.main monte-carlo \
    --iterations 10000
```

Sensitivity:

```bash
python -m src.main sensitivity
```

---

# 30. Output

Simulator menghasilkan:

```text
results/
├── allocation.csv
├── driver_statistics.csv
├── daily_statistics.csv
├── sensitivity.csv
└── charts/
    ├── order_probability.png
    ├── demand_vs_orders.png
    ├── history_fit.png
    └── driver_comparison.png
```

Contoh `allocation.csv`:

```csv
timestamp,order_id,driver_id,score,probability,result
12:31,O001,D021,87.2,0.31,allocated
12:32,O002,D044,91.4,0.42,allocated
12:33,O003,D021,85.7,0.28,allocated
```

---

# 31. Validasi

Simulator harus memiliki dua jenis validasi.

### Model Validation

Apakah kode menghitung formula dengan benar?

Contoh:

```text
same input
→ same score
```

### Behavioral Validation

Apakah simulasi menghasilkan perilaku yang sesuai dengan informasi sumber?

Misalnya:

```text
Demand ↑
→ opportunity ↑
```

```text
Historical Fit ↑
→ probability ↑
```

```text
Performance ↑
→ probability tidak selalu ↑ secara absolut
```

karena faktor lain ikut menentukan.

---

# 32. Hal yang Tidak Boleh Diklaim

Project ini **tidak boleh menyatakan**:

```text
"Ini algoritma Gojek."
```

atau:

```text
"Bobot Gojek adalah 30% demand."
```

atau:

```text
"Driver dengan score 90 pasti mendapatkan order."
```

Yang benar:

```text
"Ini model simulasi berdasarkan informasi publik/materi
Gojek Driver dan asumsi eksperimen."
```

---

# 33. Roadmap

## Phase 1 — Rule Based

```text
Driver
Order
Market
Score
Allocation
```

## Phase 2 — Historical Profile

Tambahkan:

```text
7–14 day rolling history
```

## Phase 3 — Monte Carlo

```text
10,000+
simulations
```

## Phase 4 — Calibration

Jika tersedia data observasi yang sah:

```text
real observation
        ↓
model prediction
        ↓
compare
        ↓
adjust parameters
```

## Phase 5 — Machine Learning

Jika dataset cukup:

```text
Logistic Regression
Random Forest
XGBoost / LightGBM
```

Target:

```text
P(driver receives order | driver, order, market, time)
```

## Phase 6 — Explainability

Gunakan:

```text
Feature Importance
SHAP
Partial Dependence
Sensitivity Analysis
```

untuk menjawab:

> Faktor apa yang paling memengaruhi probabilitas order?

---

# 34. Prinsip Etika

Simulator hanya digunakan untuk:

* penelitian;
* pembelajaran;
* analisis statistik;
* eksperimen simulasi;
* pemahaman mekanisme dispatch.

Simulator tidak dimaksudkan untuk:

* memanipulasi aplikasi driver;
* mengubah GPS;
* melakukan spoofing lokasi;
* mengirim request palsu;
* mengakses API internal;
* bypass sistem keamanan;
* melakukan reverse engineering terhadap sistem internal yang tidak tersedia secara publik.

---

# 35. Kesimpulan

Hipotesis utama proyek:

```text
Order Opportunity
=
Demand/Supply
×
Location Fit
×
Historical Fit
×
Service Fit
×
Time Fit
×
Distance/ETA Fit
×
Performance
×
Online Consistency
```

Model tersebut bukan formula resmi.

Tujuan utama simulator adalah menguji apakah konsep:

```text
"driver yang konsisten dan sangat cocok
dengan pola order lokal"
```

dapat menghasilkan probabilitas order yang lebih tinggi dibanding driver yang hanya memiliki AR/CR tinggi.

Fokus eksperimen adalah **Historical Fit + Demand/Supply + Performance + Location + Time + Service**.

---

## Source Basis

Model ini terutama didasarkan pada materi Gojek Driver yang diberikan dalam percakapan, khususnya bagian:

* faktor yang memengaruhi bid;

* performa Mitra;

* supply-demand;

* kondisi akun/perangkat;

* riwayat 7–14 hari;

* area, layanan, jarak, dan waktu;

* jam ramai;

* pengaruh penerimaan dan penyelesaian;

* perbandingan performa dengan driver lain.

**Status model:** Experimental / Hypothetical / Research Simulator.
