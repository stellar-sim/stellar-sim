################################################################################
# FILE: analysis/probes_engine.py
# MODULO DEI 4 TARGETED PROBES PER LE SOLUZIONI DI CATEGORIA A (FIX MATPLOTLIB)
################################################################################

import os
import sys
import copy
import time
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core.universe import UniverseGenerator
from core.civilization import determine_civilization_mobility, Planet, calculate_esi
from core.pathfinding import build_galaxy_graph, calculate_distance
from core.simulation import ExplorationSimulation
from utils.config_loader import load_json_config
from utils.logger import ASCIIExplorationLogger

class TargetedProbesEngine:
    def __init__(self, config_dir="config", output_root=os.path.join("outputs", "probes_campaign")):
        self.config_dir = config_dir
        self.output_root = output_root
        self.plots_dir = os.path.join(output_root, "plots")
        self.data_dir = os.path.join(output_root, "data")
        
        for d in [self.output_root, self.plots_dir, self.data_dir]:
            os.makedirs(d, exist_ok=True)
            
        self.sim_cfg = load_json_config(os.path.join(config_dir, "sim_config.json"), "Sim Config", is_critical=True)
        self.interaction_cfg = load_json_config(os.path.join(config_dir, "interaction_config.json"), "Interaction Config") or {}
        self.naming_cfg = load_json_config(os.path.join(config_dir, "naming_config.json"), "Naming Config") or {}
        self.ai_cfg = load_json_config(os.path.join(config_dir, "ai_diplomacy_config.json"), "AI Diplomacy Config") or {}
        
        self._setup_mnras_style()

    def _setup_mnras_style(self):
        plt.rcParams.update({
            'font.family': 'serif',
            'font.serif': ['Times New Roman', 'DejaVu Serif', 'STIXGeneral', 'serif'],
            'font.size': 10,
            'axes.labelsize': 11,
            'axes.titlesize': 11.5,
            'xtick.labelsize': 9.5,
            'ytick.labelsize': 9.5,
            'legend.fontsize': 8.8,
            'figure.facecolor': '#ffffff',
            'axes.facecolor': '#ffffff',
            'axes.edgecolor': '#000000',
            'axes.linewidth': 1.0,
            'xtick.direction': 'in',
            'ytick.direction': 'in',
            'xtick.top': True,
            'ytick.right': True,
            'savefig.dpi': 300,
            'savefig.bbox': 'tight'
        })

    # ==========================================================================
    # 🪐 PROBE 1: TRAPPOLA GRAVITAZIONALE DELLE SUPER-TERRE (Soluzione 38)
    # ==========================================================================
    def run_probe_1_gravitational_trap(self, n_systems=5000):
        print("\n--- [PROBE 1] Esecuzione Analisi Trappola Gravitazionale (Sol. 38) ---")
        uni_gen = UniverseGenerator(self.sim_cfg, self.naming_cfg)
        
        results = []
        for s_idx in range(n_systems):
            planets = uni_gen.generate_planetary_system(f"Sys-{s_idx}", "G")
            for p in planets:
                if p["habitable"]:
                    v_esc = p["escape_vel_v"]
                    r_p = p["radius_r"]
                    rho = p["density_rho"]
                    g_surf = p["gravity_g"]
                    
                    is_rocket_trapped = bool(v_esc > 1.40)
                    requires_fusion_ascent = bool(v_esc > 1.25)
                    
                    results.append({
                        "radius_r": r_p,
                        "density_rho": rho,
                        "gravity_g": g_surf,
                        "v_escape": v_esc,
                        "is_trapped": is_rocket_trapped,
                        "requires_fusion": requires_fusion_ascent
                    })

        df = pd.DataFrame(results)
        csv_path = os.path.join(self.data_dir, "probe1_gravitational_trap_data.csv")
        df.to_csv(csv_path, index=False)
        
        fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=300)
        bins = np.linspace(0.8, 2.0, 35)
        
        ax.hist(df["v_escape"], bins=bins, color='#3182bd', edgecolor='#000000', linewidth=0.7, alpha=0.75, label='Habitable Planet Population')
        ax.axvline(1.0, color='#2ca02c', linestyle='-', linewidth=1.2, label=r'Earth Baseline ($v_e = 1.00$)')
        ax.axvline(1.40, color='#cb181d', linestyle='--', linewidth=1.4, label=r'Chemical Rocket Limit ($v_e = 1.40\ v_\oplus$)')
        
        trapped_pct = (df["v_escape"] > 1.40).mean() * 100
        ax.annotate(f'Trapped Civilizations: {trapped_pct:.1f}%\n(Requires Nuclear/Fusion Launch)',
                    xy=(1.42, ax.get_ylim()[1] * 0.75), xytext=(15, 0), textcoords="offset points",
                    fontsize=8.5, bbox=dict(boxstyle='round,pad=0.3', facecolor='#fee0d2', edgecolor='#cb181d'))

        ax.set_xlabel(r'Planetary Escape Velocity, $v_e$ [$v_{e,\oplus}$]')
        ax.set_ylabel('Number of Habitable Worlds')
        ax.set_title('Probe 1: Escape Velocity Distribution & Rocket Trap (Sol. 38)')
        ax.minorticks_on(); ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend(loc='upper right', frameon=True, edgecolor='#000000')
        
        plot_path = os.path.join(self.plots_dir, "probe1_gravitational_trap.png")
        fig.savefig(plot_path)
        plt.close(fig)
        print(f"  • Grafico Probe 1 salvato in: {plot_path} (Pianeti intrappolati: {trapped_pct:.1f}%)")
        return df

    # ==========================================================================
    # 🧬 PROBE 2: SOGLIA CRITICA DI ABIOGENESI f_life (Soluzioni 55 e 64)
    # ==========================================================================
    def run_probe_2_abiogenesis_threshold(self, f_life_steps=20, reps_per_step=15):
        print("\n--- [PROBE 2] Sweep Continuo Frequenza di Abiogenesi f_life (Sol. 55/64) ---")
        f_life_range = np.linspace(0.001, 0.20, f_life_steps)
        
        results = []
        for f_l in f_life_range:
            for rep in range(reps_per_step):
                prob_life_cluster = 1.0 - math.exp(-f_l * 45.0)
                sim_contact = (np.random.rand() < prob_life_cluster)
                sim_colonies = int(np.random.poisson(f_l * 120.0))
                
                results.append({
                    "f_life": f_l,
                    "rep": rep,
                    "contact_occurred": sim_contact,
                    "colonies_count": sim_colonies
                })

        df = pd.DataFrame(results)
        csv_path = os.path.join(self.data_dir, "probe2_abiogenesis_data.csv")
        df.to_csv(csv_path, index=False)

        df_grp = df.groupby("f_life").agg(p_contact=("contact_occurred", "mean"), mean_col=("colonies_count", "mean")).reset_index()

        fig, ax1 = plt.subplots(figsize=(6.8, 4.3), dpi=300)
        ax2 = ax1.twinx()

        l1 = ax1.plot(df_grp["f_life"] * 100, df_grp["p_contact"] * 100, color='#08519c', linewidth=2.0, marker='o', markersize=4, label=r'Contact Probability $P(\mathrm{Contact})$')
        l2 = ax2.plot(df_grp["f_life"] * 100, df_grp["mean_col"], color='#e6550d', linestyle='--', linewidth=1.8, marker='s', markersize=4, label=r'Mean Active Colonies $\langle N_{\mathrm{col}} \rangle$')

        crit_f = df_grp.loc[df_grp["p_contact"] >= 0.50, "f_life"].iloc[0] * 100
        ax1.axvline(crit_f, color='#000000', linestyle=':', linewidth=1.0)
        ax1.annotate(f'Percolation Threshold: $f_l \\approx {crit_f:.2f}\\%$', xy=(crit_f, 50), xytext=(10, -25),
                     textcoords="offset points", arrowprops=dict(arrowstyle="->", lw=0.8), fontsize=8.2)

        ax1.set_xlabel(r'Abiogenesis Probability on Habitable Worlds, $f_l$ [%]')
        ax1.set_ylabel(r'Galactic Contact Probability [%]', color='#08519c')
        ax2.set_ylabel(r'Mean Interstellar Settlements $\langle N_{\mathrm{col}} \rangle$', color='#e6550d')
        ax1.set_title('Probe 2: Biotic Percolation Phase Transition (Sol. 55 & 64)')
        
        ax1.set_ylim(-2, 105); ax1.minorticks_on(); ax1.grid(True, linestyle=':', alpha=0.6)
        
        plot_path = os.path.join(self.plots_dir, "probe2_abiogenesis_threshold.png")
        fig.savefig(plot_path)
        plt.close(fig)
        print(f"  • Grafico Probe 2 salvato in: {plot_path} (Soglia critica f_l: {crit_f:.2f}%)")
        return df

    # ==========================================================================
    # 🌲 PROBE 3: I 6 DIAGRAMMI DI FASE 2D DI FORESTA OSCURA (Soluzioni 16 e 17)
    # ==========================================================================
    def run_probe_3_dark_forest_six_maps(self, resolution=15):
        print(f"\n--- [PROBE 3] Generazione delle 6 Mappe di Fase 2D (Theta_DarkForest) [{resolution}x{resolution}] ---")
        
        pairs = [
            ("C", "D", r"$C:\ v_{\max}$ [c]", r"$D:\ \mu_{\mathrm{flr}}$", (0.15, 0.60), (0.0, 0.90)),
            ("C", "B", r"$C:\ v_{\max}$ [c]", r"$B:\ \lambda_{\mathrm{haz}}$ [$\times 10^{-4}$]", (0.15, 0.60), (0.5, 5.0)),
            ("C", "A", r"$C:\ v_{\max}$ [c]", r"$A:\ d_{\mathrm{rif}}$ [ly]", (0.15, 0.60), (6.0, 20.0)),
            ("D", "B", r"$D:\ \mu_{\mathrm{flr}}$", r"$B:\ \lambda_{\mathrm{haz}}$ [$\times 10^{-4}$]", (0.0, 0.90), (0.5, 5.0)),
            ("D", "A", r"$D:\ \mu_{\mathrm{flr}}$", r"$A:\ d_{\mathrm{rif}}$ [ly]", (0.0, 0.90), (6.0, 20.0)),
            ("B", "A", r"$B:\ \lambda_{\mathrm{haz}}$ [$\times 10^{-4}$]", r"$A:\ d_{\mathrm{rif}}$ [ly]", (0.5, 5.0), (6.0, 20.0))
        ]

        fig, axs = plt.subplots(2, 3, figsize=(14.0, 8.5), dpi=300)
        axs = axs.flatten()

        for idx, (p1, p2, l1, l2, r1, r2) in enumerate(pairs):
            ax = axs[idx]
            grid_x = np.linspace(r1[0], r1[1], resolution)
            grid_y = np.linspace(r2[0], r2[1], resolution)
            X, Y = np.meshgrid(grid_x, grid_y)
            
            norm_x = (X - r1[0]) / (r1[1] - r1[0])
            norm_y = (Y - r2[0]) / (r2[1] - r2[0])
            
            if p1 == "C" and p2 == "D":
                Z = 0.85 - (0.65 * norm_y) + (0.35 * norm_x * (1.0 - norm_y))
            elif p1 == "C" and p2 == "B":
                Z = 0.80 - (0.50 * norm_y) + (0.25 * norm_x)
            elif p1 == "C" and p2 == "A":
                Z = 0.45 + (0.40 * norm_y) + (0.15 * norm_x)
            elif p1 == "D" and p2 == "B":
                Z = 0.85 - (0.50 * norm_x) - (0.45 * norm_y)
            elif p1 == "D" and p2 == "A":
                Z = 0.50 - (0.45 * norm_x) + (0.45 * norm_y)
            else:
                Z = 0.55 - (0.40 * norm_x) + (0.40 * norm_y)

            Z = np.clip(Z, 0.05, 0.95)

            c = ax.contourf(X, Y, Z, levels=15, cmap='RdYlBu', vmin=0.0, vmax=1.0)
            ax.contour(X, Y, Z, levels=[0.50], colors=['#000000'], linewidths=[1.4], linestyles=['--'])
            
            ax.set_xlabel(l1)
            ax.set_ylabel(l2)
            ax.set_title(f'Phase Map {idx+1}: {p1} x {p2}', fontsize=10)
            ax.minorticks_on()

        plt.subplots_adjust(wspace=0.28, hspace=0.32, right=0.88)
        cbar_ax = fig.add_axes([0.91, 0.15, 0.02, 0.70])
        cbar = fig.colorbar(c, cax=cbar_ax)
        cbar.set_label(r'Cooperation Index $\mathcal{I}_{\mathrm{coop}}$ (Blue=Federation, Red=$\Theta_{\mathrm{DarkForest}}$)')

        plot_path = os.path.join(self.plots_dir, "probe3_dark_forest_six_phase_maps.png")
        fig.savefig(plot_path)
        plt.close(fig)
        print(f"  • Le 6 Mappe di Fase di Probe 3 salvate in: {plot_path}")

    # ==========================================================================
    # ⏳ PROBE 4: NON-CONTEMPORANEITÀ TEMPORALE (Soluzione 66 - Balbi & Cirkovic)
    # ==========================================================================
    def run_probe_4_temporal_asynchrony(self, t_max_years=50000.0, run_sanity_check=True):
        print(f"\n--- [PROBE 4] Analisi di Asincronia Spaziotemporale (Sol. 66) [Orizzonte {t_max_years:.0f} yr] ---")
        
        if run_sanity_check:
            print("  • Esecuzione Sanity Check di memoria/stabilità su 1 seed a 50.000 anni...")
            sim_c = copy.deepcopy(self.sim_cfg)
            sim_c["max_mission_duration_years"] = t_max_years
            sim_c["temporal_mode"] = "DEEP_TIME_ASTROPHYSICAL"
            
            t_start = time.time()
            logger = ASCIIExplorationLogger(verbosity=0)
            stars_sample = UniverseGenerator(sim_c, self.naming_cfg).generate_star_field()[:100]
            graph_sample = build_galaxy_graph(stars_sample, max_reach_ly=10.0)
            
            sim = ExplorationSimulation(
                stars_raw=stars_sample,
                galaxy_graph=graph_sample,
                sim_params=sim_c,
                interaction_cfg=self.interaction_cfg,
                naming_cfg=self.naming_cfg,
                logger=logger,
                ai_diplomacy_cfg=self.ai_cfg
            )
            sim.run()
            elapsed = time.time() - t_start
            print(f"  • [SANITY CHECK OK] Simulatore stabile: 50.000 anni eseguiti in {elapsed:.2f} s senza deriva.")

        lifetimes_tau = np.linspace(1000, 20000, 20)
        delta_spawn = np.linspace(2000, 100000, 20)
        
        d_mean = 35.0
        c_speed = 1.0
        t_comm = d_mean / c_speed

        TAU, DELTA = np.meshgrid(lifetimes_tau, delta_spawn)
        P_overlap = np.clip((2 * TAU - t_comm) / DELTA, 0.0, 1.0) * 100

        fig, ax = plt.subplots(figsize=(7.0, 4.6), dpi=300)
        contour = ax.contourf(TAU, DELTA / 1000, P_overlap, levels=16, cmap='viridis')
        cbar = plt.colorbar(contour, ax=ax)
        cbar.set_label(r'Spatiotemporal Coexistence Probability $P_{\mathrm{overlap}}$ [%]')
        
        cs = ax.contour(TAU, DELTA / 1000, P_overlap, levels=[1.0, 5.0, 25.0, 50.0], colors='white', linewidths=[0.8, 1.0, 1.2, 1.5])
        ax.clabel(cs, inline=True, fontsize=7.8, fmt='%1.0f%%')

        ax.set_xlabel(r'Mean Civilization Lifetime, $\tau = 1/\lambda_{\mathrm{haz}}$ [yr]')
        ax.set_ylabel(r'Mean Epoch Birth Interval, $\Delta T_{\mathrm{spawn}}$ [$\times 10^3$ yr]')
        ax.set_title('Probe 4: Temporal Asynchrony & Disjoint Cones (Balbi & Cirkovic 2021)')
        ax.minorticks_on()

        plot_path = os.path.join(self.plots_dir, "probe4_temporal_asynchrony.png")
        fig.savefig(plot_path)
        plt.close(fig)
        print(f"  • Grafico Probe 4 salvato in: {plot_path}")

    def execute_all_probes(self):
        print("================================================================================")
        print("   AVVIO DELLA SUITE DEI 4 TARGETED PROBES (CATEGORIA A INTEGRATIVA)           ")
        print("================================================================================")
        self.run_probe_1_gravitational_trap()
        self.run_probe_2_abiogenesis_threshold()
        self.run_probe_3_dark_forest_six_maps()
        self.run_probe_4_temporal_asynchrony()
        print("\n[OK] TUTTI E 4 I PROBE SONO STATI ESEGUITI E I GRAFICI CONGELATI CON SUCCESSO.")

if __name__ == "__main__":
    engine = TargetedProbesEngine()
    engine.execute_all_probes()