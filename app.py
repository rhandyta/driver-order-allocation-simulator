import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import sys

# Ensure root directory is in sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.models import ScoringWeights, HistorySubWeights, Driver, Order, Market
from src.simulation import Simulator, generate_random_driver, generate_random_order, generate_random_market, AREAS, SERVICE_TYPES
from src.eligibility import filter_eligible
from src.scoring import score_all_candidates, get_score_breakdown
from src.allocator import allocate_order, softmax_probabilities
from src.ml_model import AllocationDatasetGenerator, AllocationMLModel
from src.explainability import FeatureExplainer
from src.calibration import ScoringCalibrator

st.set_page_config(
    page_title="Driver Order Allocation Simulator",
    page_icon="🚕",
    layout="wide"
)

st.title("🚕 Driver Order Allocation Simulator — Interactive Dashboard")
st.caption("Eksperimen & Simulasi Rekonstruksi Mekanisme Alokasi Driver (Berdasarkan Fitur Cek Kondisi Akun Driver)")

# ==================== SIDEBAR CONFIGURATION ====================
st.sidebar.header("⚙️ Scoring Weights & Parameters")

with st.sidebar.expander("📊 Factor Weights (Total 100)", expanded=True):
    w_demand = st.slider("Demand / Supply", 0, 50, 30, help="Faktor rasio permintaan dibanding ketersediaan driver")
    w_history = st.slider("Historical Fit (Area/Time/Svc)", 0, 50, 20, help="Kesesuaian riwayat 14 hari terakhir")
    w_service = st.slider("Service Fit", 0, 30, 15, help="Histori jenis layanan (GoRide, GoFood, GoSend)")
    w_time = st.slider("Time Fit", 0, 30, 10, help="Histori jam aktif aktifitas")
    w_distance = st.slider("Location / Distance Fit", 0, 30, 10, help="Jarak penjemputan (Haversine)")
    w_eta = st.slider("ETA Fit", 0, 20, 5, help="Estimasi waktu tiba penjemputan")
    w_cr = st.slider("Completion Rate (CR)", 0, 20, 5, help="Tingkat penyelesaian trip")
    w_ar = st.slider("Acceptance Rate (AR)", 0, 20, 3, help="Tingkat penerimaan bid")
    w_oc = st.slider("Online Consistency", 0, 20, 2, help="Konsistensi jam & hari online 14 hari")

total_w = w_demand + w_history + w_service + w_time + w_distance + w_eta + w_cr + w_ar + w_oc
if total_w != 100:
    st.sidebar.warning(f"⚠️ Total bobot: **{total_w}** (disarankan total = 100)")

weights = ScoringWeights(
    demand=w_demand, history=w_history, service=w_service,
    time=w_time, distance=w_distance, eta=w_eta,
    completion_rate=w_cr, acceptance_rate=w_ar, online_consistency=w_oc
)

with st.sidebar.expander("🕹️ Simulation Settings"):
    sim_days = st.number_input("Days", min_value=1, max_value=30, value=14)
    num_drivers = st.number_input("Number of Drivers", min_value=5, max_value=200, value=30)
    orders_per_day = st.number_input("Orders per Day", min_value=5, max_value=100, value=20)
    weather_cond = st.selectbox("Weather Condition (Surge)", ["clear", "rainy", "heavy_rain"], help="Rainy weather triggers 2.5x - 3.5x demand surge")
    use_osrm = st.checkbox("Enable OSRM Real Road Routing", value=False, help="Hitung jarak jalan & durasi navigasi riil OSRM menggantikan Haversine")
    temperature = st.slider("Softmax Temperature (T)", 0.5, 20.0, 5.0, step=0.5)
    alloc_method = st.selectbox("Allocation Method", ["softmax", "deterministic"])
    eligibility_mode = st.selectbox("Device Eligibility Mode", ["hard", "soft"])

config = {
    "scoring_weights": {
        "demand": w_demand, "history": w_history, "service": w_service,
        "time": w_time, "distance": w_distance, "eta": w_eta,
        "completion_rate": w_cr, "acceptance_rate": w_ar, "online_consistency": w_oc
    },
    "history_sub_weights": {"service": 0.35, "area": 0.30, "time": 0.20, "distance": 0.15},
    "allocation": {"temperature": temperature, "method": alloc_method},
    "eligibility": {"device_status_mode": eligibility_mode},
    "simulation": {"rolling_window_days": 14},
    "routing": {"use_osrm": use_osrm}
}


# ==================== MAIN DASHBOARD TABS ====================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Live Simulation & Inspector",
    "🤖 Machine Learning & Calibration Studio",
    "🧪 Experiment Lab",
    "👤 Driver Profile Explorer",
    "⏱️ Micro-Simulation View"
])


# -------------------- TAB 1: LIVE SIMULATION --------------------
with tab1:
    st.subheader("Simulasi & Alokasi Real-Time")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Parameter Weights", f"{total_w}/100")
    with col2:
        st.metric("Simulation Window", f"{sim_days} Days")
    with col3:
        st.metric("Active Drivers Population", f"{num_drivers} Drivers")
    with col4:
        st.metric("Weather Surge State", weather_cond.upper())
        
    if st.button("🚀 Jalankan Simulasi", type="primary"):
        with st.spinner("Menjalankan simulasi alokasi order..."):
            sim = Simulator(config)
            results = sim.run_simulation(days=sim_days, num_drivers=num_drivers, orders_per_day=orders_per_day)
            st.session_state["sim_results"] = results
            st.session_state["simulator"] = sim
            st.success(f"Simulasi selesai! Total alokasi berhasil: {len(results)} order.")


    if "simulator" in st.session_state:
        sim = st.session_state["simulator"]
        results = st.session_state["sim_results"]
        
        st.markdown("---")
        st.write("### 📍 Visualisasi Spasial Posisi Driver & Order (Bandung)")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        # Draw drivers
        drv_lats = [d.location[0] for d in sim.drivers]
        drv_lons = [d.location[1] for d in sim.drivers]
        ax.scatter(drv_lons, drv_lats, c='blue', alpha=0.6, label='Drivers', s=50, marker='o')
        
        # Sample 15 orders for visualization
        sample_results = results[:15]
        for r in sample_results:
            ax.annotate(r.driver_id, (sim.drivers[0].location[1], sim.drivers[0].location[0]), fontsize=8)
            
        ax.set_title("Distribusi Geografis Driver & Titik Penjemputan")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.5)
        st.pyplot(fig)
        plt.close(fig)
        
        st.markdown("---")
        st.write("### 📊 Statistik Perolehan Order Driver")
        stats = sim.get_driver_statistics()
        df_stats = pd.DataFrame([
            {
                "Driver ID": did,
                "Total Orders": s["total_orders"],
                "Completed": s["completed"],
                "Cancelled": s["cancelled"],
                "Avg Score": round(s["avg_score"], 2),
                "Win Probability (%)": round(s["order_probability"] * 100, 2)
            }
            for did, s in stats.items()
        ]).sort_values("Total Orders", ascending=False)
        
        st.dataframe(df_stats, use_container_width=True)

# -------------------- TAB 2: ML & CALIBRATION --------------------
with tab2:
    st.subheader("Fase 4 & Fase 5 — ML Prediction & Weight Calibration")
    st.markdown("Gunakan modul ini untuk melatih model Machine Learning (*Logistic Regression* & *Random Forest*) serta melakukan kalibrasi bobot scoring otomatis.")
    
    col_ml1, col_ml2 = st.columns(2)
    
    with col_ml1:
        if st.button("🧠 Latih Model ML (Logistic & Random Forest)", use_container_width=True):
            with st.spinner("Mengekstrak data simulasi & melatih model ML..."):
                sim = Simulator(config)
                sim.run_simulation(days=14, num_drivers=30, orders_per_day=20)
                sample_orders = [generate_random_order(f"O{i+1:04d}") for i in range(50)]
                markets = [generate_random_market(a) for a in AREAS]
                
                generator = AllocationDatasetGenerator()
                X, y = generator.build_dataset_from_simulation(sim.drivers, sample_orders, markets, sim.results)
                
                if len(X) > 0 and len(np.unique(y)) > 1:
                    rf_model = AllocationMLModel("rf")
                    rf_model.train(X, y)
                    eval_res = rf_model.evaluate(X, y)
                    
                    st.success(f"Model Random Forest Berhasil Dilatih!")
                    st.metric("Model ROC-AUC", f"{eval_res['roc_auc']:.4f}")
                    st.metric("Model Accuracy", f"{eval_res['accuracy']:.4f}")
                    
                    explainer = FeatureExplainer(rf_model)
                    imp_df = explainer.generate_explainability_report(X, y, output_dir="results")
                    st.session_state["feature_imp"] = imp_df
                else:
                    st.info("Dataset simulasi berhasil dibuat!")

    with col_ml2:
        if st.button("⚖️ Jalankan Kalibrasi Bobot (Scipy Minimize)", use_container_width=True):
            with st.spinner("Mengoptimasi bobot scoring..."):
                calibrator = ScoringCalibrator()
                sample_driver = generate_random_driver("D001")
                sample_order = generate_random_order("O001")
                sample_market = generate_random_market("area_B")
                calib_dataset = [(sample_order, [sample_driver], sample_market, [1.0])]
                
                opt_weights = calibrator.calibrate(calib_dataset)
                st.success("Kalibrasi Bobot Selesai!")
                st.json({
                    "Demand": round(opt_weights.demand, 2),
                    "History": round(opt_weights.history, 2),
                    "Service": round(opt_weights.service, 2),
                    "Time": round(opt_weights.time, 2),
                    "Distance": round(opt_weights.distance, 2),
                    "ETA": round(opt_weights.eta, 2),
                    "Completion Rate": round(opt_weights.completion_rate, 2),
                    "Acceptance Rate": round(opt_weights.acceptance_rate, 2),
                    "Online Consistency": round(opt_weights.online_consistency, 2)
                })

    if "feature_imp" in st.session_state:
        st.markdown("---")
        st.write("### 📈 Permutation Feature Importance Analysis (Phase 6)")
        st.dataframe(st.session_state["feature_imp"], use_container_width=True)

# -------------------- TAB 3: EXPERIMENT LAB --------------------
with tab3:
    st.subheader("Laboratorium Eksperimen (Exp A — Exp G)")
    
    exp_choice = st.selectbox("Pilih Eksperimen", [
        "acceptance_rate", "completion_rate", "history", "demand", "online", "combined", "ml"
    ])
    
    if st.button("🧪 Jalankan Eksperimen Skenario", type="primary"):
        with st.spinner(f"Menjalankan eksperimen {exp_choice}..."):
            import importlib
            exp_map = {
                "acceptance_rate": "experiments.experiment_ar",
                "completion_rate": "experiments.experiment_cr",
                "history": "experiments.experiment_history",
                "demand": "experiments.experiment_demand",
                "online": "experiments.experiment_online",
                "combined": "experiments.experiment_combined",
                "ml": "experiments.experiment_ml"
            }
            mod = importlib.import_module(exp_map[exp_choice])
            if exp_choice == "ml":
                mod.run_ml_experiment(config, output_dir="results")
            else:
                mod.run_experiment(config, output_dir="results")
            st.success(f"Eksperimen {exp_choice} berhasil dijalankan! Hasil tersimpan di results/")

# -------------------- TAB 4: DRIVER PROFILE --------------------
with tab4:
    st.subheader("👤 Driver Profile & 14-Day History Explorer")
    
    dummy_drv = generate_random_driver("D007")
    from src.spatial_h3 import H3SpatialManager
    h3_cell = H3SpatialManager.coord_to_h3(dummy_drv.location)
    
    st.write(f"**Driver ID:** `{dummy_drv.id}` | **H3 Cell ID (Res 8):** `{h3_cell}`")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Acceptance Rate", f"{dummy_drv.acceptance_rate * 100:.1f}%")
    c2.metric("Completion Rate", f"{dummy_drv.completion_rate * 100:.1f}%")
    c3.metric("Online Hours (14d)", f"{dummy_drv.online_hours:.1f} hrs")
    c4.metric("Online Days (14d)", f"{dummy_drv.online_days} days")
    
    st.write("#### 📜 Rolling History Profile (Services, H3 Cells, Areas, Slots)")
    st.json(dummy_drv.history)

# -------------------- TAB 5: MICRO-SIMULATION VIEW --------------------
with tab5:
    st.subheader("⏱️ Event-Driven Micro-Simulation View (Real-Time Driver Movement)")
    st.markdown("Simulasi detik-demi-detik pergerakan posisi driver dan transisi state machine (`IDLE` $\\rightarrow$ `EN_ROUTE_PICKUP` $\\rightarrow$ `TRIP_IN_PROGRESS` $\\rightarrow$ `IDLE`).")
    
    if st.button("▶️ Jalankan Micro-Simulation (300 Detik / 60 Ticks)", type="primary"):
        with st.spinner("Menjalankan event loop pergerakan driver detik-demi-detik..."):
            from src.microsimulation import MicroSimulationEngine, DriverState
            drivers = [generate_random_driver(f"D{i+1:03d}") for i in range(15)]
            engine = MicroSimulationEngine(drivers, config)
            
            # Generate tick events
            ticks_data = []
            for t in range(60):
                # 5-second ticks
                orders = [generate_random_order(f"O_micro_{t}_{i}") for i in range(1)] if t % 10 == 0 else None
                engine.tick(delta_seconds=5.0, new_orders=orders)
                
                states_summary = {}
                for md in engine.micro_drivers:
                    states_summary[md.state.value] = states_summary.get(md.state.value, 0) + 1
                    
                ticks_data.append({
                    "Time (sec)": int(engine.clock_seconds),
                    **states_summary
                })
                
            st.success("Micro-simulation 300 detik selesai!")
            df_ticks = pd.DataFrame(ticks_data).fillna(0)
            
            st.write("#### 📈 Transisi State Driver Seiring Waktu")
            st.line_chart(df_ticks.set_index("Time (sec)"))
            
            st.write("#### 📋 Log Alokasi Micro-Simulation")
            st.write(f"Total order dialokasikan: **{len(engine.allocation_log)}**")


