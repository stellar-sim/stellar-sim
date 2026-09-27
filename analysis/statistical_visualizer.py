################################################################################
# FILE: analysis/statistical_visualizer.py
################################################################################

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class StatisticalVisualizer:
    def __init__(self, dataset_csv_path="outputs/batch_runs/monte_carlo_runs_dataset.csv", output_dir="outputs/batch_runs"):
        self.dataset_path = dataset_csv_path
        self.output_dir = output_dir
        self.df = None
        self._setup_mnras_style()

    def _setup_mnras_style(self):
        """Imposta i parametri grafici editoriali MNRAS / A&A."""
        plt.rcParams.update({
            'font.family': 'serif',
            'font.serif': ['Times New Roman', 'DejaVu Serif', 'STIXGeneral', 'serif'],
            'mathtext.fontset': 'stix',
            'font.size': 11,
            'axes.labelsize': 12,
            'axes.titlesize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 9.5,
            
            'figure.facecolor': '#ffffff',
            'axes.facecolor': '#ffffff',
            'axes.edgecolor': '#000000',
            'axes.linewidth': 1.0,
            'axes.labelcolor': '#000000',
            
            'xtick.direction': 'in',
            'ytick.direction': 'in',
            'xtick.top': True,
            'ytick.right': True,
            'xtick.major.size': 5.0,
            'xtick.minor.size': 2.5,
            'ytick.major.size': 5.0,
            'ytick.minor.size': 2.5,
            'xtick.major.width': 0.8,
            'xtick.minor.width': 0.6,
            'ytick.major.width': 0.8,
            'ytick.minor.width': 0.6,
            'xtick.color': '#000000',
            'ytick.color': '#000000',
            
            'grid.color': '#d3d3d3',
            'grid.linestyle': ':',
            'grid.linewidth': 0.6,
            'grid.alpha': 0.7,
            
            'savefig.dpi': 300,
            'savefig.bbox': 'tight'
        })

    def load_data(self):
        if not os.path.exists(self.dataset_path):
            print(f"[ERRORE ANALISI] Dataset non trovato a '{self.dataset_path}'.")
            return False
        
        self.df = pd.read_csv(self.dataset_path)
        print(f"[ANALISI] Caricati dati di {len(self.df)} simulazioni Monte Carlo.")
        return True

    def generate_all_reports(self):
        if not self.load_data():
            return

        os.makedirs(self.output_dir, exist_ok=True)
        
        self.plot_cumulative_contact_probability()
        self.plot_distance_vs_time_scatter()
        self.plot_great_filter_demographics()
        self.plot_alien_disposition_breakdown()
        
        self.plot_drake_equation_funnel()
        self.plot_colonial_lifecycle_secession()
        self.plot_technological_divergence_lc()
        self.plot_galactic_spatial_diffusion()
        
        print(f"[ANALISI] Tutti gli 8 grafici scientifici MNRAS/A&A salvati in '{self.output_dir}/'.")

    def plot_cumulative_contact_probability(self, filename="1_curva_paradosso_fermi.png"):
        df_success = self.df[self.df["first_contact_occurred"] == True].dropna(subset=["time_to_first_contact_years"])
        total_runs = len(self.df)

        if df_success.empty or total_runs == 0: return

        max_years = int(self.df["simulation_duration_years"].max() if "simulation_duration_years" in self.df else 1000)
        time_steps = np.arange(1, max_years + 1)

        cumulative_probs = [len(df_success[df_success["time_to_first_contact_years"] <= t]) / total_runs for t in time_steps]

        fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=300)
        ax.plot(time_steps, cumulative_probs, color='#08306b', linewidth=1.8, label=r'$\mathrm{Empirical\ ECDF}\ P(T \leq t)$')
        ax.fill_between(time_steps, 0, cumulative_probs, color='#08306b', alpha=0.08)

        median_time = df_success["time_to_first_contact_years"].median()
        saturation_prob = cumulative_probs[-1]

        ax.axvline(median_time, color='#b2182b', linestyle='--', linewidth=1.2, label=rf'$\mathrm{{Median}}\ T_{{50}} = {median_time:.1f}\,\mathrm{{yr}}$')
        ax.axhline(saturation_prob, color='#525252', linestyle=':', linewidth=1.1, label=rf'$\mathrm{{Saturation}}\ P_\infty = {saturation_prob*100:.1f}\%$')

        ax.set_xlabel(r'$\mathrm{Mission\ Elapsed\ Time,}\ t\ [\mathrm{yr}]$')
        ax.set_ylabel(r'$\mathrm{Cumulative\ Detection\ Probability,}\ P(T \leq t)$')
        ax.set_xlim(0, max_years); ax.set_ylim(-0.01, 1.03)
        ax.minorticks_on(); ax.grid(True)
        leg = ax.legend(loc='lower right', frameon=True, edgecolor='#000000', facecolor='#ffffff', framealpha=1.0, labelcolor='#000000')
        leg.get_frame().set_linewidth(0.8)

        fig.savefig(os.path.join(self.output_dir, filename)); plt.close(fig)

    def plot_distance_vs_time_scatter(self, filename="2_orizzonte_distanza_primo_contatto.png"):
        df_contact = self.df[self.df["first_contact_occurred"] == True].dropna(subset=["time_to_first_contact_years", "contact_distance_ly"])
        if df_contact.empty: return

        fig, ax = plt.subplots(figsize=(6.8, 4.5), dpi=300)
        scatter = ax.scatter(df_contact["contact_distance_ly"], df_contact["time_to_first_contact_years"],
                             c=df_contact["systems_before_contact"], cmap='viridis', s=32, alpha=0.85, edgecolors='#333333', linewidths=0.5)

        cbar = plt.colorbar(scatter, ax=ax, pad=0.02)
        cbar.set_label(r'$\mathrm{Surveyed\ Systems\ Prior\ to\ Contact}\ N_{\mathrm{sys}}$', color='#000000')
        cbar.ax.tick_params(direction='in', size=3, labelcolor='#000000')

        try:
            z = np.polyfit(df_contact["contact_distance_ly"], df_contact["time_to_first_contact_years"], 1)
            p = np.poly1d(z)
            x_vals = np.linspace(df_contact["contact_distance_ly"].min(), df_contact["contact_distance_ly"].max(), 100)
            eff_v = (1.0 / z[0]) if abs(z[0]) > 1e-5 else 0.45
            ax.plot(x_vals, p(x_vals), color='#b2182b', linestyle='-', linewidth=1.4, label=rf'$\mathrm{{Mean\ Frontier\ Velocity}}\ (v_{{\mathrm{{eff}}}} = {eff_v:.2f}\,c)$')
        except Exception: pass

        ax.set_xlabel(r'$\mathrm{Heliocentric\ Distance\ at\ First\ Contact,}\ d\ [\mathrm{ly}]$')
        ax.set_ylabel(r'$\mathrm{Detection\ Epoch,}\ t_{\mathrm{contact}}\ [\mathrm{yr}]$')
        ax.minorticks_on(); ax.grid(True)
        leg = ax.legend(loc='upper left', frameon=True, edgecolor='#000000', facecolor='#ffffff', framealpha=1.0, labelcolor='#000000')
        leg.get_frame().set_linewidth(0.8)
        fig.savefig(os.path.join(self.output_dir, filename)); plt.close(fig)

    def plot_great_filter_demographics(self, filename="3_grande_filtro_archeologia.png"):
        fig, ax = plt.subplots(figsize=(6.2, 4.0), dpi=300)
        c_live = (self.df["first_contact_occurred"] == True).sum()
        r_only = ((self.df["first_contact_occurred"] == False) & (self.df["archeological_relics_found"] > 0)).sum()
        silence = ((self.df["first_contact_occurred"] == False) & (self.df["archeological_relics_found"] == 0)).sum()

        cats = ['Active Spacefaring\nCivilization', 'Extinct Relics Only\n(Great Filter)', 'Complete Cosmic\nSolitude']
        counts = [c_live, r_only, silence]
        bars = ax.bar(cats, counts, color=['#2166ac', '#d6604d', '#4d4d4d'], edgecolor='#000000', linewidth=0.8, width=0.45)

        for bar in bars:
            h = bar.get_height(); pct = (h / len(self.df)) * 100
            ax.annotate(f'{h}\n({pct:.1f}%)', xy=(bar.get_x() + bar.get_width() / 2.0, h), xytext=(0, 3),
                        textcoords="offset points", ha='center', va='bottom', fontsize=9.0, color='#000000')

        ax.set_ylabel(r'$\mathrm{Number\ of\ Monte\ Carlo\ Realizations}$')
        ax.set_ylim(0, max(counts) * 1.22 if max(counts) > 0 else 10)
        ax.minorticks_on(); ax.grid(axis='y')
        fig.savefig(os.path.join(self.output_dir, filename)); plt.close(fig)

    def plot_alien_disposition_breakdown(self, filename="4_profili_diplomatici_alieni.png"):
        df_contact = self.df[self.df["first_contact_occurred"] == True]
        if df_contact.empty or "contact_disposition" not in df_contact.columns: return

        disp_counts = df_contact["contact_disposition"].value_counts()
        disp_counts = disp_counts[disp_counts.index != "Nessuna"]
        if disp_counts.empty: return

        fig, ax = plt.subplots(figsize=(6.8, 4.0), dpi=300)
        academic_labels = {'Collaborativa': 'Collaborative', 'Esplorativa': 'Exploratory', 'Cauta': 'Cautious',
                           'Pacifica': 'Peaceful', 'Diffidente': 'Wary', 'Predatoria': 'Predatory', 'Ostile': 'Hostile'}
        labels = [academic_labels.get(k, k) for k in disp_counts.index]
        palette = ['#08519c', '#3182bd', '#6baed6', '#9ecae1', '#e6550d', '#de2d26', '#a50f15']

        bars = ax.bar(labels, disp_counts.values, color=[palette[i % len(palette)] for i in range(len(disp_counts))],
                      edgecolor='#000000', linewidth=0.8, width=0.55)

        for bar in bars:
            h = bar.get_height(); pct = (h / len(df_contact)) * 100
            ax.annotate(f'{h}\n({pct:.1f}%)', xy=(bar.get_x() + bar.get_width() / 2.0, h), xytext=(0, 3),
                        textcoords="offset points", ha='center', va='bottom', fontsize=8.5, color='#000000')

        ax.set_ylabel(r'$\mathrm{Frequency\ of\ Occurrence}$')
        ax.set_ylim(0, max(disp_counts.values) * 1.25)
        ax.minorticks_on(); ax.grid(axis='y')
        plt.xticks(rotation=20, ha='right')
        fig.savefig(os.path.join(self.output_dir, filename)); plt.close(fig)

    def plot_drake_equation_funnel(self, filename="5_decomposizione_equazione_drake.png"):
        tot_hab = int(self.df.get("planets_habitable_surveyed", pd.Series([0])).sum())
        tot_life = int(self.df.get("planets_with_life_surveyed", pd.Series([0])).sum())
        tot_intel = int(self.df.get("planets_with_intel_surveyed", pd.Series([0])).sum())
        tot_space = int(self.df.get("planets_with_spacefaring_surveyed", pd.Series([0])).sum())

        if tot_hab == 0 and tot_life == 0: 
            return

        # Frazioni rigorose condizionali Drake (Opzione A)
        f_l = (tot_life / max(1, tot_hab)) * 100
        f_i = (tot_intel / max(1, tot_life)) * 100
        f_c = (tot_space / max(1, tot_intel)) * 100

        fig, ax = plt.subplots(figsize=(6.8, 4.4), dpi=300)
        
        labels = [
            r'$\mathrm{Habitable\ (n_e)}$', 
            r'$\mathrm{Life\ (f_l)}$', 
            r'$\mathrm{Intelligent\ (f_i)}$', 
            r'$\mathrm{Spacefaring\ (f_c)}$'
        ]
        totals = [tot_hab, tot_life, tot_intel, tot_space]
        colors = ['#4393c3', '#92c5de', '#f4a582', '#d6604d']

        bars = ax.bar(labels, totals, color=colors, edgecolor='#000000', linewidth=0.8, width=0.52)

        ax.annotate(rf'$N = {tot_hab}$' + '\n' + r'$(100\%)$', xy=(0, tot_hab), xytext=(0, 6), 
                    textcoords="offset points", ha='center', fontsize=8.0, color='#000000')
        ax.annotate(rf'$N = {tot_life}$' + '\n' + rf'$(f_l = {min(100.0, f_l):.1f}\%)$', xy=(1, tot_life), xytext=(0, 6), 
                    textcoords="offset points", ha='center', fontsize=8.0, color='#000000')
        ax.annotate(rf'$N = {tot_intel}$' + '\n' + rf'$(f_i = {min(100.0, f_i):.1f}\%)$', xy=(2, tot_intel), xytext=(0, 6), 
                    textcoords="offset points", ha='center', fontsize=8.0, color='#000000')
        ax.annotate(rf'$N = {tot_space}$' + '\n' + rf'$(f_c = {min(100.0, f_c):.1f}\%)$', xy=(3, tot_space), xytext=(0, 6), 
                    textcoords="offset points", ha='center', fontsize=8.0, color='#000000')

        ax.set_yscale('log')
        ax.set_ylabel(r'$\mathrm{Cumulative\ Celestial\ Bodies\ Log_{10}(N)}$')
        ax.set_ylim(1, max(totals) * 12 if max(totals) > 0 else 100)
        ax.minorticks_on(); ax.grid(True, which='both', axis='y', linestyle=':', alpha=0.5)
        
        fig.savefig(os.path.join(self.output_dir, filename))
        plt.close(fig)

    def plot_colonial_lifecycle_secession(self, filename="6_ciclo_vitale_colonie_secessione.png"):
        mean_founded = self.df.get("colonies_founded", self.df.get("total_earth_colonies", pd.Series([0]))).mean()
        mean_active = self.df.get("colonies_active", self.df.get("total_earth_colonies", pd.Series([0]))).mean()
        mean_collapsed = self.df.get("colonies_collapsed", pd.Series([0])).mean()
        mean_sovereign = self.df.get("colonies_sovereign", pd.Series([0])).mean()
        mean_hostile = self.df.get("colonies_secession_hostile", pd.Series([0])).mean()
        mean_loyal = self.df.get("colonies_secession_loyal", pd.Series([0])).mean()

        fig, ax = plt.subplots(figsize=(6.8, 4.2), dpi=300)
        cats = ['Founded\nTotal', 'Surviving\nActive', 'Collapsed\nIsolated', 'Sovereign\n(Stage 4)', 'Secession\n(Hostile)', 'Secession\n(Loyal)']
        vals = [mean_founded, mean_active, mean_collapsed, mean_sovereign, mean_hostile, mean_loyal]
        colors = ['#2171b5', '#41ab5d', '#cb181d', '#88419d', '#e6550d', '#238b45']

        bars = ax.bar(cats, vals, color=colors, edgecolor='#000000', linewidth=0.8, width=0.5)

        for bar in bars:
            h = bar.get_height()
            ax.annotate(f'{h:.1f}', xy=(bar.get_x() + bar.get_width() / 2.0, h), xytext=(0, 3),
                        textcoords="offset points", ha='center', va='bottom', fontsize=9.0, color='#000000')

        ax.set_ylabel(r'$\mathrm{Mean\ Colonies\ per\ Realization\ }\langle N \rangle$')
        ax.set_ylim(0, max(vals) * 1.25 if max(vals) > 0 else 1)
        ax.minorticks_on(); ax.grid(axis='y')
        fig.savefig(os.path.join(self.output_dir, filename)); plt.close(fig)

    def plot_technological_divergence_lc(self, filename="7_divergenza_tecnologica_lc.png"):
        fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=300)

        earth_lc = self.df.get("earth_final_lc", pd.Series([1.0]*len(self.df)))
        colony_max_lc = self.df.get("max_colony_lc", pd.Series([1.0]*len(self.df)))

        bins = np.linspace(0.8, 1.6, 30)
        ax.hist(earth_lc, bins=bins, color='#08519c', alpha=0.6, label=r'$\mathrm{Earth\ Final\ LC}$', edgecolor='#000000', linewidth=0.6)
        ax.hist(colony_max_lc, bins=bins, color='#e6550d', alpha=0.6, label=r'$\mathrm{Top\ Colony\ LC\ (Superpower)}$', edgecolor='#000000', linewidth=0.6)

        pct_surpassed = (self.df.get("colony_surpassed_earth", pd.Series([False])) == True).mean() * 100

        ax.axvline(1.0, color='#000000', linestyle='--', linewidth=1.0, label=r'$\mathrm{Earth\ Baseline\ LC_0 = 1.0}$')
        ax.annotate(rf'$\mathrm{{Colonies\ Surpassing\ Earth:}}\ {pct_surpassed:.1f}\%$',
                    xy=(0.52, 0.78), xycoords='axes fraction', fontsize=9.0, color='#000000',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='#ffffff', edgecolor='#000000', lw=0.8))

        ax.set_xlabel(r'$\mathrm{Civilization\ Level\ Metric,}\ \mathrm{LC}$')
        ax.set_ylabel(r'$\mathrm{Frequency\ of\ Realizations}$')
        ax.minorticks_on(); ax.grid(True)
        leg = ax.legend(loc='upper left', frameon=True, edgecolor='#000000', facecolor='#ffffff', framealpha=1.0, labelcolor='#000000')
        leg.get_frame().set_linewidth(0.8)
        fig.savefig(os.path.join(self.output_dir, filename)); plt.close(fig)

    def plot_galactic_spatial_diffusion(self, filename="8_diffusione_spaziale_frontiera.png"):
        fig, ax = plt.subplots(figsize=(6.8, 4.5), dpi=300)

        rad_col = "max_expansion_radius_ly" if "max_expansion_radius_ly" in self.df.columns else "contact_distance_ly"
        col_col = "total_earth_colonies" if "total_earth_colonies" in self.df.columns else "colonies_active"
        
        df_valid = self.df[self.df[rad_col] > 0]
        if df_valid.empty: 
            df_valid = self.df

        colonies_data = df_valid[col_col] if col_col in df_valid.columns else np.zeros(len(df_valid))

        scatter = ax.scatter(df_valid["total_systems_explored"], df_valid[rad_col],
                             c=colonies_data, cmap='coolwarm', s=25, alpha=0.75, edgecolors='#333333', linewidths=0.4)

        cbar = plt.colorbar(scatter, ax=ax, pad=0.02)
        cbar.set_label(r'$\mathrm{Established\ Colonies}\ N_{\mathrm{col}}$', color='#000000')
        cbar.ax.tick_params(direction='in', size=3, labelcolor='#000000')

        try:
            valid_mask = (df_valid["total_systems_explored"] > 0) & (df_valid[rad_col] > 0)
            if valid_mask.sum() >= 3:
                log_x = np.log(df_valid.loc[valid_mask, "total_systems_explored"])
                log_y = np.log(df_valid.loc[valid_mask, rad_col])
                z = np.polyfit(log_x, log_y, 1)
                x_trend = np.linspace(df_valid.loc[valid_mask, "total_systems_explored"].min(), df_valid.loc[valid_mask, "total_systems_explored"].max(), 100)
                y_trend = np.exp(z[1]) * (x_trend ** z[0])
                ax.plot(x_trend, y_trend, color='#b2182b', linestyle='-', linewidth=1.5, label=rf'$\mathrm{{Scaling\ Law:}}\ R \propto N^{{{z[0]:.2f}}}$')
        except Exception: 
            pass

        ax.set_xlabel(r'$\mathrm{Total\ Surveyed\ Systems}\ N_{\mathrm{sys}}$')
        ax.set_ylabel(r'$\mathrm{Maximum\ Frontier\ Horizon,}\ R_{\max}\ [\mathrm{ly}]$')
        ax.minorticks_on(); ax.grid(True)
        leg = ax.legend(loc='upper left', frameon=True, edgecolor='#000000', facecolor='#ffffff', framealpha=1.0, labelcolor='#000000')
        leg.get_frame().set_linewidth(0.8)
        fig.savefig(os.path.join(self.output_dir, filename)); plt.close(fig)