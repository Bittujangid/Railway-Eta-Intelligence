# Railway ETA Intelligence

> **Technically validated hackathon prototype** developed for the Smart India Hackathon (Problem Statement: **SIH26028**).  
> **Status**: Demo Ready

---

## Problem

**Dynamic Forecast of Expected Time of Arrival (ETA) for Coaching Trains**  
**Problem Statement ID**: SIH26028

Conventional train tracking interfaces present static delays based only on the train's current position (e.g., *"Train 12951 is running 16 minutes late"*). However, a train's delay is dynamic: as operating conditions evolve across route sections, delays can be recovered using timetable slack, maintained within corridor tolerances, or compounded by track congestion and junction bottlenecks.

This prototype solves the challenge by:
- Recognizing that static/current ETAs change dynamically as operating conditions evolve across route sections.
- Forecasting multi-station delay evolution and dynamic station-by-station ETAs.
- Deriving passenger journey feasibility and connection margins directly from predicted arrival uncertainty.

---

## Solution

The system combines statistical machine learning with physical train kinematics to deliver physically consistent, non-exploding arrival forecasts:

```
Railway Data
    ↓
Feature Processing
    ↓
XGBoost Forecasting
    ↓
Kinematic Constraints
    ↓
Physics-Informed ML Fusion
    ↓
Delay Trajectory
    ↓
Dynamic ETA
    ↓
Uncertainty
    ↓
Journey Feasibility
    ↓
Network Impact
```

1. **Railway Data**: Ingests route topology, genuine station coordinates, timetable schedules, and operational parameters.
2. **Feature Processing**: Computes speed, scheduled dwell, remaining distance, temporal peak factors, and corridor interaction density without temporal leakage.
3. **XGBoost Forecasting**: Predicts station-to-station delay delta using gradient-boosted decision trees.
4. **Kinematic Constraints**: Bounds maximum delay recovery and running capability using physical track limits and sectional run times.
5. **Physics-Informed ML Fusion**: Fuses the machine learning forecast with kinematic constraints to guarantee dimensional consistency and prevent unrealistic acceleration or delay explosion.
6. **Delay Trajectory**: Recursively rolls out arrival times station-by-station until the destination.
7. **Dynamic ETA**: Computes arrival timestamps adjusted for predicted sectional delays.
8. **Uncertainty**: Calculates empirical confidence intervals derived from held-out validation residuals.
9. **Journey Feasibility**: Evaluates whether a passenger can reach their destination before a required deadline with an adequate safety buffer.
10. **Network Impact**: Estimates downstream delay propagation risk on interconnected corridor traffic.

---

## Key Features

- **Dynamic Station-Wise ETA**: Station-by-station predicted arrival times computed along the entire remaining route.
- **Future Delay Trajectory**: Sequential multi-stop delay forecast curve showing how delay evolves over distance and time.
- **Recover / Maintain / Increase Delay Evolution**: Automatic classification of delay trend based on corridor timetable slack and sectional congestion.
- **Validation-Based ETA Uncertainty**: Empirical quantile intervals ($Q_{05}$ to $Q_{95}$) derived from model residuals on held-out validation data.
- **Journey Feasibility**: Deterministic passenger feasibility score ($0$ to $100$) and status (`FEASIBLE`, `UNCERTAIN`, `LOW_FEASIBILITY`).
- **Passenger-Required Arrival & Minimum Buffer**: Interactive calculator allowing passengers to set their target arrival time and required buffer margin.
- **Network Propagation Risk**: Schedule-derived headway and route congestion heuristic flagging downstream operational impact.
- **Scenario Simulation**: Interactive toggle across `NORMAL`, `CONGESTION`, and `SEVERE_DELAY` operational states triggering real-time recalculations.
- **Railway Route Visualization**: Interactive map displaying genuine station coordinates, route polyline, and train position.
- **Data & Model Transparency**: Honest, explicit breakdown of provenance, model metrics, feature importances, and validation methodology.

---

## Technology

### Backend
- **Python**: Core programming language.
- **FastAPI**: Asynchronous high-performance REST API.
- **XGBoost**: Gradient-boosted regression trees for delay delta prediction.
- **Scikit-learn**: Feature pre-processing, metrics evaluation, and validation splits.
- **Pandas**: Tabular data manipulation and feature engineering.
- **NumPy & SciPy**: Vectorized arithmetic, Haversine distance, and statistical quantile computation.
- **SQLite**: Local relational database indexing stations, trains, schedules, and route distances.

### Frontend
- **React**: Component-based user interface.
- **Vite**: Modern frontend build tooling and development server.
- **Recharts**: Responsive charting engine for the multi-station delay trajectory hero chart.
- **Leaflet & React-Leaflet**: Interactive map rendering route paths and station markers.
- **OpenStreetMap**: Map tile provider for spatial visualization.
- **Tailwind CSS**: Utility-first enterprise UI styling.
- **IBM Plex Sans**: Standard typography for clean, readable operations dashboard presentation.

---

## Model Validation

Validation was conducted on a held-out temporal dataset evaluated strictly on chronological forward dates to prevent temporal leakage:

- **Training rows**: 73,106
- **Held-out validation rows**: 26,584
- **Mean Absolute Error (MAE)**: **2.67 minutes**
- **Root Mean Squared Error (RMSE)**: **5.35 minutes**
- **Residual Quantiles**: $Q_{05} = -5.19\text{ min}$, $Q_{95} = +5.69\text{ min}$
- **Automated Backend Tests**: **19/19 passed**

> **Note on Training Data**: The training distribution is a **calibrated synthetic corpus** generated using authentic Indian Railways timetable and corridor parameters, and is not live Indian Railways operational telemetry.

---

## Data Transparency

| Component | Source / Provenance | Description |
|---|---|---|
| **Railway Network & Timetable** | Public Community Source (DataMeet) | Authentic station names, coordinates, distances, and published timetable schedules. |
| **Historical Telemetry** | Calibrated Synthetic | Synthesized using physical speed distributions, scheduled buffers, and section congestion parameters. |
| **Live Train State** | Simulated | High-fidelity telemetry simulator delivering position, speed, and current delay. |
| **Forecast Model** | XGBoost Regressor | Station-to-station delay delta prediction with kinematic safety constraints. |
| **ETA Uncertainty** | Validation Residuals | Empirical $Q_{05}$ and $Q_{95}$ residuals from held-out temporal evaluation. |
| **Network Propagation** | Prototype Heuristic | Schedule-derived headway density and track occupancy risk model. |

> **IMPORTANT DISCLOSURE**:  
> Live Indian Railways production feeds such as NTES/RTIS/COA are not directly integrated in this prototype.  
> The prototype demonstrates the algorithmic forecasting engine and operational user experience using authentic network topology and simulated live feeds.

---

## Running Locally

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup

```bash
# Navigate to the project root
cd railway-eta

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI backend server
python -m uvicorn backend.main:app --port 8000 --reload
```

### 2. Frontend Setup

```bash
# Navigate to the frontend directory
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```

### Expected URLs
- **Backend API**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Backend Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- **Interactive API Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)

---

## Testing

Execute the automated test suite from the project root:

```bash
python -m pytest backend/tests -v
```

**Expected Result**:
```
======================= 19 passed, 2 warnings in 7.99s =======================
```

The test suite validates:
- Health and train list endpoints
- Monotonic distance progression along routes
- Speed and status consistency
- Trajectory prediction and delay evolution
- Feasibility score bounds and deterministic calculation
- Real backend scenario switching
- Physical bounds and absence of delay explosion
- Destination ETA time arithmetic and midnight rollover handling
- Dimensional consistency of kinematic equations
- Active XGBoost model perturbation response
- Delay trend card mathematical consistency ($\Delta = \text{Next} - \text{Current}$)

---

## Production Build

To verify and compile the frontend production bundle:

```bash
cd frontend
npm run build
```

**Expected Output**: Clean build producing static assets in `frontend/dist/` with 0 compilation errors.

---

## Demo Scenarios

The dashboard provides an interactive scenario switcher in the top navigation bar to demonstrate how dynamic ETAs adjust to changing conditions:

- **Normal**: Nominal corridor operations with scheduled slack absorbing minor variations. Delay evolution typically shows `RECOVER`.
- **Congestion**: Sectional traffic density increases, leading to cautionary signaling and minor speed reductions. Delay evolution shifts to `MAINTAIN` or `INCREASE`.
- **Severe Delay**: Major corridor disruption with cascading hold-ups and junction queueing. Delay evolution flags `INCREASE`, and journey feasibility scores reflect tight or breached margins.

---

## Limitations

- **No Live Indian Railways Production API Integration**: The system does not connect to internal CRIS/NTES/COA feeds; live train telemetry is simulated.
- **Simulated Live Train State**: Telemetry messages are generated to demonstrate real-time reactivity without requiring authenticated rail network access.
- **Synthetic/Calibrated Training Distribution**: Model weights were trained on a calibrated synthetic dataset reflecting railway operational physics rather than multi-year historical logs.
- **Validation-Based Uncertainty**: Confidence bounds reflect validation residuals ($Q_{05}, Q_{95}$) rather than full Bayesian posterior distributions.
- **Heuristic Network Propagation**: Downstream propagation estimates track occupancy risk using schedule density heuristics rather than dynamic signaling block simulations.
- **Prototype / Demo Scope**: Designed as an advanced hackathon prototype to demonstrate feasibility and decision-support value.
