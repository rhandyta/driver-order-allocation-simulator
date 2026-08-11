# Panduan Penggunaan Driver Order Allocation Simulator

Dokumen ini berisi panduan lengkap penggunaan **Driver Order Allocation Simulator**, struktur file proyek, cara menjalankan simulasi, eksperimen, Machine Learning, serta peluncuran Web Dashboard interaktif.

---

## 📁 1. Struktur File Proyek

```text
driver-order-allocation-simulator/
├── README.md                  # Dokumentasi umum & dasar konseptual model
├── USAGE.md                   # Panduan penggunaan lengkap
├── requirements.txt           # Package Python (numpy, pandas, scipy, scikit-learn, streamlit, h3, dll.)
├── app.py                     # Interactive Web Dashboard (Streamlit UI)
├── config/
│   └── weights.yaml           # Konfigurasi bobot awal & parameter simulasi
├── data/
│   ├── drivers.json           # Data sampel 10 driver (Bandung)
│   ├── orders.json            # Data sampel 5 customer order
│   └── market.json            # Data sampel kondisi pasar
├── src/
│   ├── __init__.py
│   ├── models.py              # Class Data Model (Driver, Order, Market, ScoringWeights)
│   ├── eligibility.py         # Eligibility filter (Hard/Soft & Trip Settings)
│   ├── features.py            # Feature extraction (Haversine, Service Fit, Time Fit, H3 Area Fit)
│   ├── spatial_h3.py          # Uber H3 Hexagonal Spatial Indexing Manager
│   ├── market_dynamic.py      # Dynamic Market Generator (Jam sibuk, Hujan, Event surge)
│   ├── scoring.py             # Engine perhitungan skor berbobot (0-100)
│   ├── allocator.py           # Softmax probabilistic allocation & ranking
│   ├── history.py             # History Manager (Rolling window 14 hari)
│   ├── calibration.py         # Parameter Calibration Engine (Scipy minimize)
│   ├── ml_model.py            # Dataset Generator & Model ML (Logistic & Random Forest)
│   ├── explainability.py      # Feature Importance & Permutation Analysis
│   ├── simulation.py          # Simulation Engine utama
│   └── main.py                # Command Line Interface (CLI) entry point
├── experiments/
│   ├── experiment_ar.py       # Eksperimen A: Acceptance Rate
│   ├── experiment_cr.py       # Eksperimen B: Completion Rate
│   ├── experiment_history.py  # Eksperimen C & D: Historical Fit & Area
│   ├── experiment_demand.py   # Eksperimen E: Demand / Supply
│   ├── experiment_online.py   # Eksperimen F: Online Consistency
│   ├── experiment_combined.py # Eksperimen G: Profil Kombinasi Driver
│   ├── experiment_ml.py       # Eksperimen Fase 4-6 (ML, Calibration & Explainability)
│   ├── monte_carlo.py         # Simulasi Monte Carlo (10,000+ iterasi)
│   └── sensitivity.py         # Sensitivity Analysis
├── tests/
│   ├── test_scoring.py        # Unit test perhitungan skor
│   ├── test_history.py        # Unit test rolling window 14 hari
│   ├── test_allocator.py      # Unit test softmax allocation
│   ├── test_trip_settings.py  # Unit test filter trip settings
│   ├── test_calibration.py   # Unit test optimizer kalibrasi
│   ├── test_ml.py             # Unit test model ML
│   ├── test_spatial_h3.py     # Unit test Uber H3 spatial indexing
│   └── test_market_dynamic.py # Unit test pasar dinamis & lonjakan hujan
└── results/
    ├── csv/                   # Hasil ekspor statistik dalam format CSV
    └── charts/                # Grafik visualisasi dalam format PNG
```

---

## 🚀 2. Cara Menjalankan Aplikasi & CLI

Seluruh fungsi dapat dijalankan melalui file [src/main.py](file:///d:/Project/python/driver-order-allocation-simulator/src/main.py) atau file [app.py](file:///d:/Project/python/driver-order-allocation-simulator/app.py).

### 🖥️ A. Meluncurkan Interactive Web Dashboard (Rekomendasi Utama)

Untuk melihat simulasi visual secara langsung, mengubah slider bobot, serta menguji model ML melalui browser:

```bash
python -m src.main dashboard
```

atau menggunakan perintah Streamlit langsung:

```bash
python -m streamlit run app.py
```

*Dashboard akan otomatis terbuka di browser pada alamat `http://localhost:8501`.*

---

### 📊 B. Menjalankan Simulasi Standar via CLI

Untuk menjalankan simulasi alokasi order selama $N$ hari:

```bash
python -m src.main simulate --days 14 --drivers 100 --orders 50
```

**Output:**
- Hasil statistik order disimpan ke file CSV: [results/csv/allocation.csv](file:///d:/Project/python/driver-order-allocation-simulator/results/csv/allocation.csv) dan [results/csv/driver_statistics.csv](file:///d:/Project/python/driver-order-allocation-simulator/results/csv/driver_statistics.csv).

---

### 🧪 C. Menjalankan Eksperimen Skenario (A – G)

Proyek menyediakan 7 skenario eksperimen khusus:

```bash
# Exp A — Pengaruh Acceptance Rate (AR)
python -m src.main experiment --name acceptance_rate

# Exp B — Pengaruh Completion Rate (CR)
python -m src.main experiment --name completion_rate

# Exp C & D — Pengaruh Historical Fit & Area
python -m src.main experiment --name history

# Exp E — Pengaruh Demand / Supply Ratio
python -m src.main experiment --name demand

# Exp F — Pengaruh Konsistensi Jam/Hari Online
python -m src.main experiment --name online

# Exp G — Perbandingan Combined Driver Profile
python -m src.main experiment --name combined

# Exp ML — Pelatihan Machine Learning & Calibration Engine
python -m src.main experiment --name ml
```

**Output:**
- Data CSV disimpan di `results/csv/experiment_*.csv`.
- Grafik PNG diproduksi di `results/charts/experiment_*.png`.

---

### 🤖 D. Menjalankan Pelatihan ML & Kalibrasi Bobot (Fase 4 & 5)

Untuk melatih model Machine Learning (*Logistic Regression* & *Random Forest*) dan melakukan analisis *Permutation Feature Importance*:

```bash
python -m src.main ml-train
```

**Output:**
- Evaluasi akurasi & ROC-AUC di: [results/csv/ml_evaluation.csv](file:///d:/Project/python/driver-order-allocation-simulator/results/csv/ml_evaluation.csv)
- Feature Importance di: [results/csv/feature_importance.csv](file:///d:/Project/python/driver-order-allocation-simulator/results/csv/feature_importance.csv)
- Grafik Feature Importance di: [results/charts/feature_importance.png](file:///d:/Project/python/driver-order-allocation-simulator/results/charts/feature_importance.png)

---

### 🎲 E. Menjalankan Simulasi Monte Carlo & Sensitivity Analysis

Untuk melakukan simulasi stokastik ribuan kali dan analisis sensitivitas variabel:

```bash
# Monte Carlo (10,000 iterasi)
python -m src.main monte-carlo --iterations 10000

# Sensitivity Analysis
python -m src.main sensitivity
```

---

### 🧪 F. Menjalankan Unit Tests Otomatis

Untuk memverifikasi kebenaran seluruh fungsi:

```bash
python -m pytest tests/
```

*(Saat ini 34/34 unit test lulus 100%)*

---

### ⚡ G. Menjalankan Engine Simulasi Performa Tinggi Bahasa Go

Untuk simulasi Monte Carlo skala masif (100,000+ iterasi per detik) memanfaatkan *goroutines*:

```bash
# Menjalankan simulasi Go (100,000 iterasi dengan 8 worker goroutines)
go run cmd/simulator/main.go --iterations 100000 --workers 8

# Menjalankan unit test Go
go test ./...
```

---

### 🌐 H. Menjalankan Service REST API Server (FastAPI)

Untuk meluncurkan HTTP REST API Server yang dapat diakses oleh sistem/aplikasi eksternal via JSON payload:

```bash
# Meluncurkan REST API server pada port 8000
python -m src.main serve --port 8000
```

- **Healthcheck Endpoint**: `GET http://localhost:8000/health`
- **Scoring Breakdown**: `POST http://localhost:8000/score`
- **Order Allocation**: `POST http://localhost:8000/allocate`
- **ML Probability Prediction**: `POST http://localhost:8000/predict-ml`
- **Dokumentasi Swagger UI Interaktif**: Open `http://localhost:8000/docs` di browser.

---

### 🎬 I. Merender Animasi Visual Trajektori Driver (GIF)

Untuk merender animasi pergerakan driver secara real-time dari micro-simulation ke file GIF:

```bash
# Merender animasi pergerakan driver (40 ticks pada 8 FPS)
python -m src.main animate --ticks 40 --fps 8
```

- **Output File**: Animasi GIF disimpan di [results/charts/driver_movement.gif](file:///d:/Project/python/driver-order-allocation-simulator/results/charts/driver_movement.gif).
- Animasi juga dapat dirender dan ditonton secara interaktif pada **Tab 5 Web Dashboard**.

---

## ⚙️ 3. Mengubah Konfigurasi & Data Input

- **Bobot Scoring Engine**: Edit file [config/weights.yaml](file:///d:/Project/python/driver-order-allocation-simulator/config/weights.yaml) untuk mengubah bobot `demand`, `history`, `distance`, dll.
- **Profil Driver**: Edit file [data/drivers.json](file:///d:/Project/python/driver-order-allocation-simulator/data/drivers.json) untuk menambah/mengubah kriteria driver.
- **Kondisi Pasar**: Edit file [data/market.json](file:///d:/Project/python/driver-order-allocation-simulator/data/market.json) untuk mengubah rasio demand/supply wilayah.



