# Stellar-Sim (v5.4)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://www.python.org/)

**Stellar-Sim** is an agent-based, discrete-event simulation engine designed to model the relativistic kinematics, thermodynamic boundaries, and socio-political fragmentation of interstellar civilizations (addressing the Fermi Paradox and the Great Silence).

This software represents the computational foundation of the monograph:
> **Arcipelago Cosmico: Perché le civiltà aliene potrebbero esistere, ma restare isolate e invisibili**  
> *by Giampaolo Maschietti (2026)*

---

## 🌌 Core Features & Theoretical Pillars

- **3D Galactic Graph Topology:** Realistic spatial generation matching the Salpeter/Chabrier Initial Mass Function (IMF) and recent *Kepler/Gaia* exoplanetary demographics.
- **Surface Habitability & Energy Surplus:** Full 4-parameter Earth Similarity Index ($\text{ESI} \ge 0.70$) decoupled from the operational Surface Colonizability Index ($C_{\mathrm{col}}$).
- **Relativistic Governance & The Deborah Number:** Institutional decay and colonial secession driven by the Lorentz causal lag ($\text{De}_{\mathrm{gov}} > 1$).
- **Solution 76 (Colonial Hysteresis & Technological Leapfrogging):** Frontier worlds outperforming mother worlds, leading to endogenous autocannibalization of continuous colonization waves.
- **Game Theory & Thermodynamic Muzzle Flash:** Trade network cooperation vs. Dark Forest predation constrained by relativistic energy dissipation.

---

## 🚀 Quickstart & Installation

Python 3.10 or higher is required.

```bash
git clone https://github.com/stellar-sim/stellar-sim.git
cd stellar-sim
pip install numpy pandas matplotlib plotly networkx tqdm
```

---

## 📂 Repository Structure & Canonical Runs

- `core/`: Physics engine, agent logistics, and diplomatic/game-theory modules.
- `config/`: JSON configuration files governing astrophysical and geopolitical rules.
- `analysis/`: DOE factorial engine ($2^5$), statistical regression OLS/ANOVA, and Targeted Probes.
- `visualization/`: Advanced Plotly 3D interactive mapping engine.
- `outputs/canonical_runs/`: Pre-computed logs, time-series, and 3D interactive maps for the 4 iconic case studies discussed in the book (Runs #844, #167, #371, #126).

---

## 📖 Usage & Reproducibility

To run simulations, explore the interactive Jupyter Notebook:
```bash
jupyter notebook STELLAR-SIM_Lab.ipynb
```

## 📄 License & Open Science

Distributed under the **GNU General Public License v3.0 (GPLv3)**. Experimental datasets are released under **Creative Commons CC BY 4.0**. See `LICENSE` for details.
```
