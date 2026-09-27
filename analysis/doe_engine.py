################################################################################
# FILE: analysis/doe_engine.py
################################################################################

import os
import sys
import copy
import time
import datetime
import itertools
import multiprocessing
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from utils.config_loader import load_json_config
from analysis.montecarlo import run_single_monte_carlo_iteration

DOE_FACTORS_SPEC = {
    "A": {
        "name": "Overstretch Threshold (d_rif)",
        "unit": "ly",
        "levels": {-1: 6.0, 0: 10.0, 1: 20.0},
        "target": ("ai", "imperial_overstretch", "reference_distance_ly")
    },
    "B": {
        "name": "Poisson Hazard Rate (lambda)",
        "unit": "yr^-1",
        "levels": {-1: 0.5e-4, 0: 1.8e-4, 1: 5.0e-4},
        "target": ("ai", "poisson_great_filter", "base_annual_hazard_rate")
    },
    "C": {
        "name": "Cruise Speed (v_max)",
        "unit": "c",
        "levels": {-1: 0.15, 0: 0.35, 1: 0.60},
        "target": ("sim", "max_exploration_speed_c")
    },
    "D": {
        "name": "M-Dwarf Flare Penalty",
        "unit": "prob",
        "levels": {-1: 0.0, 0: 0.5, 1: 0.9},
        "target": ("sim", "m_dwarf_flare_penalty")
    },
    "E": {
        "name": "Alien Initial Maturity (LC_0)",
        "unit": "LC",
        "levels": {
            -1: [0.50, 0.95],
             0: [0.85, 1.25],
             1: [1.25, 1.60]
        },
        "target": ("sim", "initial_alien_lc_range")
    }
}

def build_full_factorial_matrix():
    levels = [-1, 1]
    full_factorial = list(itertools.product(levels, repeat=5))
    matrix = [list(row) for row in full_factorial]
    matrix.append([0, 0, 0, 0, 0])
    matrix.append([0, 0, 0, 0, 0])
    return matrix

DOE_FULL_DESIGN_MATRIX = build_full_factorial_matrix()


class DOEManager:
    def __init__(self, base_sim_cfg, base_interaction_cfg, base_naming_cfg, base_ai_cfg, output_root=None):
        self.sim_cfg = base_sim_cfg
        self.interaction_cfg = base_interaction_cfg
        self.naming_cfg = base_naming_cfg
        self.ai_cfg = base_ai_cfg
        
        target_root = output_root or os.path.join("outputs", "doe_campaign")
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(target_root, f"doe_full_factorial_{ts}")
        self.plots_dir = os.path.join(self.output_dir, "plots")
        self.logs_dir = os.path.join(self.output_dir, "logs")
        self._setup_mnras_style()

    def _setup_mnras_style(self):
        plt.rcParams.update({
            'font.family': 'serif',
            'font.serif': ['Times New Roman', 'DejaVu Serif', 'STIXGeneral', 'serif'],
            'mathtext.fontset': 'stix',
            'font.size': 10,
            'axes.labelsize': 11,
            'axes.titlesize': 11.5,
            'xtick.labelsize': 9.5,
            'ytick.labelsize': 9.0,
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

    def _inject_doe_factors(self, factor_levels_row, active_temporal_mode="TACTICAL_ACCELERATED"):
        sim_c = copy.deepcopy(self.sim_cfg)
        inter_c = copy.deepcopy(self.interaction_cfg)
        ai_c = copy.deepcopy(self.ai_cfg)

        # Iniezione del Dual-Mode Temporale
        is_deep = (active_temporal_mode == "DEEP_TIME_ASTROPHYSICAL")
        sim_c["temporal_mode"] = active_temporal_mode
        sim_c["max_mission_duration_years"] = 10000.0 if is_deep else 1000.0

        factors_order = ["A", "B", "C", "D", "E"]
        for idx, f_key in enumerate(factors_order):
            lvl = factor_levels_row[idx]
            spec = DOE_FACTORS_SPEC[f_key]
            real_val = spec["levels"][lvl]
            target_path = spec["target"]

            if target_path[0] == "sim":
                if len(target_path) == 2:
                    sim_c[target_path[1]] = real_val
            elif target_path[0] == "ai":
                if len(target_path) == 3:
                    if target_path[1] not in ai_c:
                        ai_c[target_path[1]] = {}
                    ai_c[target_path[1]][target_path[2]] = real_val

        return sim_c, inter_c, ai_c

    def execute_doe_campaign(self, runs_per_treatment=30, processes=None, temporal_mode=None):
        for d in [self.output_dir, self.plots_dir, self.logs_dir]:
            os.makedirs(d, exist_ok=True)

        if processes is None:
            processes = max(1, multiprocessing.cpu_count() - 1)

        active_temporal_mode = temporal_mode or self.sim_cfg.get("temporal_mode", "TACTICAL_ACCELERATED")
        is_deep = (active_temporal_mode == "DEEP_TIME_ASTROPHYSICAL")
        horizon_years = 10000.0 if is_deep else 1000.0

        total_runs = len(DOE_FULL_DESIGN_MATRIX) * runs_per_treatment
        print("================================================================================")
        print(f"   AVVIO FULL FACTORIAL DOE 2^5 [{active_temporal_mode}]")
        print(f"   Orizzonte Temporale: {horizon_years:.0f} ANNI | {total_runs} SIMULAZIONI SU {processes} CORE")
        print(f"   34 Configurazioni Sperimentali x {runs_per_treatment} Ripetizioni Monte Carlo")
        print(f"   📂 Output Directory: {os.path.abspath(self.output_dir)}/")
        print("================================================================================")

        all_args = []
        global_run_id = 1

        for treat_idx, factor_row in enumerate(DOE_FULL_DESIGN_MATRIX):
            sim_c, inter_c, ai_c = self._inject_doe_factors(factor_row, active_temporal_mode=active_temporal_mode)
            
            for rep in range(runs_per_treatment):
                args = (
                    global_run_id,
                    total_runs,
                    sim_c,
                    inter_c,
                    self.naming_cfg,
                    ai_c,
                    self.logs_dir,
                    0
                )
                all_args.append((args, treat_idx, factor_row))
                global_run_id += 1

        start_time = time.time()
        results = []
        pool_args = [item[0] for item in all_args]
        
        with multiprocessing.Pool(processes=processes) as pool:
            completed = 0
            for res in pool.imap_unordered(run_single_monte_carlo_iteration, pool_args):
                completed += 1
                if res:
                    results.append(res)
                if completed % 25 == 0 or completed == total_runs:
                    sys.stdout.write(f"\rProgresso Full Factorial [{active_temporal_mode}]: {completed} / {total_runs} run...")
                    sys.stdout.flush()

        elapsed = time.time() - start_time
        print(f"\n\n[DOE FULL] Campagna completata in {elapsed:.2f} s ({elapsed/total_runs:.3f} s/run).")

        df_res = pd.DataFrame(results)
        
        run_to_factors = {
            item[0][0]: {
                "treatment_id": item[1] + 1,
                "factor_A": item[2][0],
                "factor_B": item[2][1],
                "factor_C": item[2][2],
                "factor_D": item[2][3],
                "factor_E": item[2][4]
            }
            for item in all_args
        }
        
        df_factors = pd.DataFrame.from_dict(run_to_factors, orient='index')
        df_factors.index.name = "run_id"
        df_factors.reset_index(inplace=True)

        df_final = pd.merge(df_factors, df_res, on="run_id")
        
        csv_path = os.path.join(self.output_dir, "doe_full_factorial_dataset.csv")
        df_final.to_csv(csv_path, index=False)
        print(f"[DATASET] Master dataset salvato in: {csv_path}")

        self.compute_anova_and_pareto(df_final)
        return df_final

    def compute_anova_and_pareto(self, df):
        print("\n--- ANALISI ANOVA OLS MULTIVARIATA CON INTERAZIONI A 2 FATTORI ---")
        
        responses = {
            "first_contact_occurred": ("Tasso di Primo Contatto (Fermi)", "Y1"),
            "colonies_sovereign": ("Numero Colonie Sovrane", "Y2"),
            "delta_lc_max": ("Massima Divergenza LC Coloniale", "Y3"),
            "total_wars": ("Frequenza Conflitti Armati", "Y4"),
            "max_expansion_radius_ly": ("Orizzonte di Espansione (ly)", "Y5")
        }

        factors = ["factor_A", "factor_B", "factor_C", "factor_D", "factor_E"]
        labels_main = [
            r"$A:\ d_{\mathrm{rif}}$",
            r"$B:\ \lambda_{\mathrm{haz}}$",
            r"$C:\ v_{\max}$",
            r"$D:\ \mu_{\mathrm{flr}}$",
            r"$E:\ \mathrm{LC}_0$"
        ]

        interaction_pairs = list(itertools.combinations(range(5), 2))
        labels_inter = [
            rf"${labels_main[i].split(':')[0].replace('$', '')} \times {labels_main[j].split(':')[0].replace('$', '')}$"
            for i, j in interaction_pairs
        ]

        all_labels = labels_main + labels_inter
        is_interaction = [False] * 5 + [True] * len(interaction_pairs)

        X_main = df[factors].values
        X_inter_cols = []
        for i, j in interaction_pairs:
            X_inter_cols.append(X_main[:, i] * X_main[:, j])
        X_inter = np.column_stack(X_inter_cols)

        X_full = np.column_stack([np.ones(len(df)), X_main, X_inter])

        for y_col, (y_name, y_code) in responses.items():
            if y_col not in df.columns:
                continue

            y = df[y_col].fillna(0).astype(float).values
            
            try:
                beta, residuals, rank, s = np.linalg.lstsq(X_full, y, rcond=None)
                effects = beta[1:]

                n = len(y)
                p = len(effects) + 1
                sse = np.sum((y - X_full @ beta)**2)
                mse = sse / max(1, (n - p))
                
                inv_xtx = np.linalg.inv(X_full.T @ X_full).diagonal()
                var_beta = mse * inv_xtx
                t_stats = np.abs(effects) / np.sqrt(np.maximum(1e-9, var_beta[1:]))

                fig, ax = plt.subplots(figsize=(7.5, 5.8), dpi=300)
                
                sorted_indices = np.argsort(t_stats)
                sorted_t = t_stats[sorted_indices]
                sorted_labels = [all_labels[i] for i in sorted_indices]
                sorted_is_inter = [is_interaction[i] for i in sorted_indices]

                bar_colors = ['#e6550d' if is_int else '#2171b5' for is_int in sorted_is_inter]

                bars = ax.barh(range(len(sorted_t)), sorted_t, color=bar_colors, edgecolor='#000000', linewidth=0.75, height=0.62)
                
                for bar, t_val in zip(bars, sorted_t):
                    w = bar.get_width()
                    ax.annotate(f'{w:.2f}', xy=(w, bar.get_y() + bar.get_height() / 2.0),
                                xytext=(4, 0), textcoords="offset points", ha='left', va='center', fontsize=8.0, color='#000000')

                t_crit = 1.96
                ax.axvline(t_crit, color='#cb181d', linestyle='--', linewidth=1.2, label=rf'$\mathrm{{Significance\ Threshold}}\ (p=0.05,\ t={t_crit})$')

                ax.barh([0], [0], color='#2171b5', edgecolor='#000000', label=r'$\mathrm{Main\ Effects}$')
                ax.barh([0], [0], color='#e6550d', edgecolor='#000000', label=r'$\mathrm{2\text{-}Factor\ Interactions}$')

                ax.set_yticks(range(len(sorted_t)))
                ax.set_yticklabels(sorted_labels, fontsize=8.8)
                ax.set_xlabel(r'$\mathrm{Standardized\ Effect\ }|t\text{-statistic}|$')
                ax.set_title(rf'$\mathrm{{{y_code}:\ {y_name}\ -\ Full\ Factorial\ 2^5\ (15\ Effects)}}$', pad=10)
                ax.set_xlim(0, max(max(sorted_t) * 1.25, t_crit * 1.5))
                ax.minorticks_on(); ax.grid(True, linestyle=':', alpha=0.6, axis='x')
                ax.legend(loc='lower right', frameon=True, edgecolor='#000000', facecolor='#ffffff')

                plt.tight_layout()
                plot_file = os.path.join(self.plots_dir, f"pareto_full_factorial_{y_code}_{y_col}.png")
                fig.savefig(plot_file)
                plt.close(fig)
                print(f"  • Grafico Pareto Full salvato ({y_code}): {plot_file}")

            except Exception as e:
                print(f"[ERRORE ANOVA FULL per {y_col}]: {e}")