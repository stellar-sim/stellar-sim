################################################################################
# FILE: visualization/plotter_3d.py
################################################################################

import os
import re
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
from collections import Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from core.civilization import Planet

class StarMapPlotter:
    def __init__(self, sim_params, plotly_cfg):
        self.sim_params = sim_params
        self.plotly_cfg = plotly_cfg
        
        self.spectral_colors = {
            "O": "rgb(0, 102, 255)", "B": "rgb(100, 149, 237)", "A": "rgb(0, 206, 209)",
            "F": "rgb(235, 235, 80)", "G": "rgb(255, 215, 0)", "K": "rgb(255, 140, 0)", 
            "M": "rgb(220, 50, 50)"
        }
        
        self.faction_colors = [
            "rgb(0, 190, 255)", "rgb(255, 50, 50)", "rgb(50, 220, 50)", 
            "rgb(255, 140, 0)", "rgb(180, 50, 255)", "rgb(255, 215, 0)", 
            "rgb(255, 90, 180)", "rgb(0, 240, 190)", "rgb(160, 210, 255)"
        ]

    def _hex_or_rgb_to_faint_rgba(self, rgb_str, alpha=0.30):
        return rgb_str.replace("rgb", "rgba").replace(")", f", {alpha})")

    def _create_sphere_mesh(self, center, radius, color_rgb, opacity=0.10):
        u = np.linspace(0, 2 * np.pi, 16)
        v = np.linspace(0, np.pi, 12)
        x = center[0] + radius * np.outer(np.cos(u), np.sin(v))
        y = center[1] + radius * np.outer(np.sin(u), np.sin(v))
        z = center[2] + radius * np.outer(np.ones(np.size(u)), np.cos(v))

        return go.Surface(
            x=x, y=y, z=z,
            colorscale=[[0, color_rgb], [1, color_rgb]],
            opacity=opacity,
            showscale=False,
            hoverinfo='none',
            showlegend=False
        )

    def plot_colonies_routes(
        self,
        stars_dict,
        galaxy_graph,
        routes_details,
        homeworld_id=None,
        homeworld_name="Madrepatria",
        assigned_names_map=None,
        filename="rotta_colonie_3d.html",
        output_dir="outputs/single_runs/html_maps",
        **kwargs
    ):
        if homeworld_id is None:
            homeworld_id = kwargs.get("sol_id", "Sol")
        if assigned_names_map is None:
            assigned_names_map = kwargs.get("assigned_names_map", {})

        print(f"[PLOTLY] Generazione Mappa Logistica ({filename}) da '{assigned_names_map.get(homeworld_id, homeworld_id)}'...")
        colony_star_ids = set()
        colony_info_map = {}

        for r in routes_details:
            if r.get("path_ids"):
                dest_id = r["path_ids"][-1]
                colony_star_ids.add(dest_id)
                colony_info_map[dest_id] = r

        data_traces = []

        for idx, route in enumerate(routes_details):
            legs = route.get("detailed_legs", [])
            is_sb = route.get("is_starbase", False)
            
            color = "rgb(0, 255, 220)" if is_sb else self.faction_colors[idx % len(self.faction_colors)]
            width = 4.5 if is_sb else 3.8
            dash_style = 'dash' if is_sb else 'solid'
            
            rx, ry, rz = [], [], []
            for leg in legs:
                f_data = stars_dict.get(leg["from_id"]); t_data = stars_dict.get(leg["to_id"])
                if f_data and t_data:
                    rx.extend([f_data["position"][0], t_data["position"][0], None])
                    ry.extend([f_data["position"][1], t_data["position"][1], None])
                    rz.extend([f_data["position"][2], t_data["position"][2], None])
            if rx:
                data_traces.append(go.Scatter3d(
                    x=rx, y=ry, z=rz, mode='lines',
                    line=dict(color=color, width=width, dash=dash_style),
                    hoverinfo='none',
                    showlegend=False
                ))

        x_stars, y_stars, z_stars = [], [], []
        marker_sizes, marker_colors, marker_symbols, hover_texts = [], [], [], []
        annotations_3d = []

        for star_id, star in stars_dict.items():
            pos = star['position']
            x_stars.append(pos[0]); y_stars.append(pos[1]); z_stars.append(pos[2])
            is_homeworld = (star_id == homeworld_id)
            is_colony = (star_id in colony_star_ids)
            assigned_name = assigned_names_map.get(star_id, star_id)
            
            sb_owner = star.get('starbase_owner', '')
            has_sb = star.get('has_starbase', False) and (sb_owner == homeworld_name or homeworld_name in str(sb_owner))
            sb_status = star.get('starbase_status', 'Leale')

            if is_homeworld:
                symbol = "diamond"; size = 15; s_color = "rgb(0, 220, 255)"
                annotations_3d.append(dict(
                    x=pos[0], y=pos[1], z=pos[2], text=f"🏛️ <b>{assigned_name} (Capitale)</b>",
                    showarrow=True, arrowhead=2, ax=20, ay=-25,
                    font=dict(color="#111111", size=10),
                    bgcolor="rgba(0, 220, 255, 0.95)", bordercolor="cyan", borderpad=3
                ))
            elif has_sb:
                if sb_status == "Leale":
                    symbol = "diamond"; size = 12; s_color = "rgb(0, 255, 180)"
                    bg_col = "rgba(180, 255, 220, 0.95)"
                    border_col = "teal"
                    sb_icon = "🛰️"
                else:
                    symbol = "diamond"; size = 13; s_color = "rgb(255, 120, 30)"
                    bg_col = "rgba(255, 200, 150, 0.95)"
                    border_col = "darkorange"
                    sb_icon = "🔥"

                annotations_3d.append(dict(
                    x=pos[0], y=pos[1], z=pos[2],
                    text=f"{sb_icon} <b>Starbase {assigned_name}</b>",
                    showarrow=True, arrowhead=2, ax=18, ay=-22,
                    font=dict(color="#002211", size=9),
                    bgcolor=bg_col, bordercolor=border_col, borderpad=2
                ))
                hover_texts.append(f"<b>Starbase {assigned_name}</b><br>• Presidio: {sb_owner}<br>• Status: {sb_status}")
            elif is_colony:
                c_info = colony_info_map.get(star_id, {})
                c_name = c_info.get("colony_name", assigned_name)
                is_emancipated = c_info.get("is_emancipated", False)
                is_hostile = c_info.get("is_hostile", False)
                stage_name = c_info.get("stage_name", "")

                if not is_emancipated:
                    symbol = "circle"; size = 10; s_color = "rgb(255, 235, 100)"
                    bg_col = "rgba(255, 248, 196, 0.95)"
                    border_col = "rgb(212, 177, 6)"
                    label_icon = "🔬"
                elif is_hostile:
                    symbol = "square"; size = 12; s_color = "rgb(255, 140, 40)"
                    bg_col = "rgba(255, 176, 79, 0.95)"
                    border_col = "rgb(204, 85, 0)"
                    label_icon = "⚔️"
                else:
                    symbol = "circle"; size = 11; s_color = "rgb(80, 220, 100)"
                    bg_col = "rgba(200, 247, 197, 0.95)"
                    border_col = "rgb(46, 158, 46)"
                    label_icon = "🏛️"

                annotations_3d.append(dict(
                    x=pos[0], y=pos[1], z=pos[2],
                    text=f"{label_icon} <b>{c_name}</b>",
                    showarrow=True, arrowhead=2, ax=18, ay=-20,
                    font=dict(color="#111111", size=9),
                    bgcolor=bg_col, bordercolor=border_col, borderpad=2
                ))
                hover_texts.append(f"<b>{c_name}</b> ({assigned_name})<br>• Stato: {stage_name}<br>• Assetto: {'Ostile' if is_hostile else 'Non Ostile'}")
            else:
                symbol = "circle"; size = 2.0; s_color = "rgba(180, 180, 180, 0.15)"
                hover_texts.append(f"<b>{assigned_name}</b> (ID: {star_id})")

            marker_symbols.append(symbol)
            marker_sizes.append(size)
            marker_colors.append(s_color)

        data_traces.append(go.Scatter3d(
            x=x_stars, y=y_stars, z=z_stars, mode='markers',
            marker=dict(size=marker_sizes, color=marker_colors, symbol=marker_symbols, opacity=0.9),
            text=hover_texts, hoverinfo='text',
            showlegend=False
        ))

        data_traces.append(go.Scatter3d(
            x=[None], y=[None], z=[None], mode='markers',
            marker=dict(size=12, color='rgb(0, 220, 255)', symbol='diamond'),
            name='Capitale / Pianeta Madre'
        ))
        data_traces.append(go.Scatter3d(
            x=[None], y=[None], z=[None], mode='markers',
            marker=dict(size=11, color='rgb(0, 255, 180)', symbol='diamond'),
            name='🛰️ Starbase Orbitale (Presidio)'
        ))
        data_traces.append(go.Scatter3d(
            x=[None], y=[None], z=[None], mode='markers',
            marker=dict(size=10, color='rgb(255, 235, 100)', symbol='circle'),
            name='🟡 Colonia in Sviluppo (Non Emancipata)'
        ))
        data_traces.append(go.Scatter3d(
            x=[None], y=[None], z=[None], mode='markers',
            marker=dict(size=10, color='rgb(80, 220, 100)', symbol='circle'),
            name='🟢 Governo Sovrano (Non Ostile / Alleato)'
        ))
        data_traces.append(go.Scatter3d(
            x=[None], y=[None], z=[None], mode='markers',
            marker=dict(size=10, color='rgb(255, 140, 40)', symbol='square'),
            name='🟠 Governo Sovrano (Ostile / Secessione)'
        ))
        data_traces.append(go.Scatter3d(
            x=[None], y=[None], z=[None], mode='lines',
            line=dict(color='rgb(100, 200, 255)', width=3),
            name='Rotte di Rifornimento Logistico'
        ))

        fig = go.Figure(data=data_traces)
        self._apply_layout(fig, f"Mappa Logistica delle Colonie da '{assigned_names_map.get(homeworld_id, homeworld_id)}'", annotations_3d)
        
        if os.path.isabs(filename) or os.path.dirname(filename):
            save_path = filename
        else:
            os.makedirs(output_dir, exist_ok=True)
            save_path = os.path.join(output_dir, filename)
            
        fig.write_html(save_path, auto_open=False)
        print(f"[PLOTLY] Salvata Mappa Logistica in: {save_path}")

    def plot_simulation_plotly(self, stars_dict, galaxy_graph, sol_star_id, agents_list=None, trade_routes=None, output_dir="outputs/single_runs/html_maps"):
        data_traces = []
        annotations_3d = []
        homeworld_stars = {}

        if agents_list:
            for idx, ag in enumerate(agents_list):
                f_color = self.faction_colors[idx % len(self.faction_colors)]
                homeworld_stars[ag.origin_system_id] = {
                    "faction": ag.faction_name, "color": f_color, "is_earth": ag.is_terrestrial,
                    "max_reach": ag.max_reach, "visited": list(set(ag.visited_path))
                }

        if agents_list:
            for ag_hw_id, ag_info in homeworld_stars.items():
                reach_radius = ag_info["max_reach"]
                f_color = ag_info["color"]
                for visited_sid in ag_info["visited"]:
                    v_star = stars_dict.get(visited_sid)
                    if v_star:
                        is_hw = (visited_sid == ag_hw_id)
                        r = reach_radius if is_hw else reach_radius * 0.85
                        op = 0.08 if is_hw else 0.04
                        data_traces.append(self._create_sphere_mesh(v_star['position'], r, f_color, opacity=op))

        if agents_list:
            for idx, ag in enumerate(agents_list):
                path = ag.visited_path
                base_color = self.faction_colors[idx % len(self.faction_colors)]
                if len(path) > 1:
                    lx, ly, lz = [], [], []
                    for i in range(len(path) - 1):
                        f_node = stars_dict.get(path[i]); t_node = stars_dict.get(path[i+1])
                        if f_node and t_node:
                            lx.extend([f_node["position"][0], t_node["position"][0], None])
                            ly.extend([f_node["position"][1], t_node["position"][1], None])
                            lz.extend([f_node["position"][2], t_node["position"][2], None])
                    data_traces.append(go.Scatter3d(
                        x=lx, y=ly, z=lz, mode='lines',
                        line=dict(color=base_color, width=3.8),
                        name=f"Albero: {ag.ship_name}", hoverinfo='none'
                    ))

        x_stars, y_stars, z_stars = [], [], []
        marker_sizes, marker_colors, marker_symbols, hover_texts = [], [], [], []

        for star_id, star in stars_dict.items():
            pos = star['position']
            x_stars.append(pos[0]); y_stars.append(pos[1]); z_stars.append(pos[2])
            s_type = star.get('type', 'G')
            s_color = self.spectral_colors.get(s_type, "rgb(180, 180, 180)")
            has_sb = star.get('has_starbase', False)

            if star_id in homeworld_stars:
                hw = homeworld_stars[star_id]
                symbol = "diamond" if hw["is_earth"] else "square"
                size = 14 if hw["is_earth"] else 11
                s_color = hw["color"]
                annotations_3d.append(dict(
                    x=pos[0], y=pos[1], z=pos[2], text=f"<b>{hw['faction']}</b>",
                    showarrow=True, arrowhead=2, ax=20, ay=-20,
                    font=dict(color="#ffffff", size=9),
                    bgcolor="rgba(15, 20, 35, 0.95)", bordercolor=hw["color"], borderpad=2
                ))
            elif has_sb:
                symbol = "diamond"; size = 11; s_color = "rgb(0, 255, 180)"
                annotations_3d.append(dict(
                    x=pos[0], y=pos[1], z=pos[2], text=f"🛰️ <b>Starbase {star['id']}</b>",
                    showarrow=True, arrowhead=2, ax=15, ay=-15,
                    font=dict(color="#111111", size=8),
                    bgcolor="rgba(180, 255, 220, 0.95)", bordercolor="teal", borderpad=2
                ))
            else:
                symbol = "circle"; size = 3.0
                s_color = s_color.replace("rgb", "rgba").replace(")", ", 0.4)")

            marker_symbols.append(symbol)
            marker_sizes.append(size)
            marker_colors.append(s_color)
            hover_texts.append(f"<b>{star['id']}</b> (Classe: {s_type})")

        data_traces.append(go.Scatter3d(
            x=x_stars, y=y_stars, z=z_stars, mode='markers',
            marker=dict(size=marker_sizes, color=marker_colors, symbol=marker_symbols, opacity=0.9),
            text=hover_texts, hoverinfo='text', name='Sistemi Stellari'
        ))

        fig = go.Figure(data=data_traces)
        self._apply_layout(fig, "Mappa Galattica V4.0 - Alberi di Espansione e Geopolitica Globale", annotations_3d)
        
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, "mappa_geopolitica_3d.html")
        fig.write_html(save_path, auto_open=False)
        print(f"[PLOTLY] Salvata Mappa Geopolitica 3D in: {save_path}")

    def plot_trade_network_3d(self, stars_dict, trade_routes, sol_id, assigned_names_map, output_dir="outputs/single_runs/html_maps"):
        data_traces = []
        annotations_3d = []
        trade_node_counts = Counter()
        for tr in trade_routes:
            trade_node_counts[tr.source_star_id] += 1
            trade_node_counts[tr.target_star_id] += 1

        for tr in trade_routes:
            s1 = stars_dict.get(tr.source_star_id); s2 = stars_dict.get(tr.target_star_id)
            if s1 and s2:
                data_traces.append(go.Scatter3d(
                    x=[s1['position'][0], s2['position'][0]],
                    y=[s1['position'][1], s2['position'][1]],
                    z=[s1['position'][2], s2['position'][2]],
                    mode='lines', line=dict(color='rgb(255, 215, 0)', width=4.0, dash='dash'),
                    hoverinfo='text',
                    text=f"<b>Rotta Commerciale</b><br>• {tr.faction_a} <-> {tr.faction_b}<br>• Dist: {tr.distance_ly:.1f} ly (+15% Surplus)",
                    showlegend=False
                ))

        x_stars, y_stars, z_stars = [], [], []
        marker_sizes, marker_colors, marker_symbols, hover_texts = [], [], [], []

        for star_id, star in stars_dict.items():
            pos = star['position']
            x_stars.append(pos[0]); y_stars.append(pos[1]); z_stars.append(pos[2])
            routes_count = trade_node_counts[star_id]
            assigned_name = assigned_names_map.get(star_id, star_id)
            is_sol = (star_id == sol_id)

            if is_sol:
                symbol = "diamond"; size = 15; color = "rgb(0, 220, 255)"
                annotations_3d.append(dict(
                    x=pos[0], y=pos[1], z=pos[2], text=f"🏛️ <b>Sol (Terra)</b><br>{routes_count} Rotte",
                    showarrow=True, arrowhead=2, ax=20, ay=-25,
                    font=dict(color="#111111", size=10),
                    bgcolor="rgba(0, 220, 255, 0.95)", bordercolor="cyan", borderpad=2
                ))
            elif routes_count >= 4:
                symbol = "diamond"; size = 12 + routes_count; color = "rgb(255, 215, 0)"
                annotations_3d.append(dict(
                    x=pos[0], y=pos[1], z=pos[2], text=f"💰 <b>Hub: {assigned_name}</b><br>({routes_count} Rotte)",
                    showarrow=True, arrowhead=2, ax=20, ay=-20,
                    font=dict(color="#111111", size=9),
                    bgcolor="rgba(255, 235, 150, 0.95)", bordercolor="gold", borderpad=2
                ))
            elif routes_count > 0:
                symbol = "circle"; size = 6 + (routes_count * 1.2); color = "rgb(255, 180, 50)"
            else:
                symbol = "circle"; size = 2.0; color = "rgba(100, 120, 160, 0.15)"

            marker_symbols.append(symbol)
            marker_sizes.append(size)
            marker_colors.append(color)
            hover_texts.append(f"<b>{assigned_name}</b><br>• Rotte Commerciali: {routes_count}")

        data_traces.append(go.Scatter3d(
            x=x_stars, y=y_stars, z=z_stars, mode='markers',
            marker=dict(size=marker_sizes, color=marker_colors, symbol=marker_symbols, opacity=0.9),
            text=hover_texts, hoverinfo='text', name='Nodi Mercantili'
        ))

        fig = go.Figure(data=data_traces)
        self._apply_layout(fig, f"Mappa 3D della Rete Commerciale Interstellare ({len(trade_routes)} Rotte Attive)", annotations_3d)
        
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, "rotte_commerciali_3d.html")
        fig.write_html(save_path, auto_open=False)
        print(f"[PLOTLY] Salvato grafico commerciale in: {save_path}")

    def plot_conflict_zones_3d(self, stars_dict, diplomacy_mgr, combat_sectors_counter, sol_id, assigned_names_map, output_dir="outputs/single_runs/html_maps"):
        data_traces = []
        annotations_3d = []
        top_war_sectors = combat_sectors_counter.most_common(6) if combat_sectors_counter else []
        name_to_star_map = {assigned_names_map.get(sid, sid): stars_dict[sid] for sid in stars_dict}
        
        for sector_name, battles_count in top_war_sectors:
            star_obj = name_to_star_map.get(sector_name)
            if star_obj:
                radius = min(12.0, 4.0 + (battles_count * 0.12))
                sphere_mesh = self._create_sphere_mesh(
                    center=star_obj['position'], radius=radius, color_rgb="rgb(255, 30, 30)", opacity=0.18
                )
                data_traces.append(sphere_mesh)

        x_stars, y_stars, z_stars = [], [], []
        marker_sizes, marker_colors, marker_symbols, hover_texts = [], [], [], []

        for star_id, star in stars_dict.items():
            pos = star['position']
            x_stars.append(pos[0]); y_stars.append(pos[1]); z_stars.append(pos[2])
            assigned_name = assigned_names_map.get(star_id, star_id)
            battles = combat_sectors_counter.get(assigned_name, 0) if combat_sectors_counter else 0
            is_sol = (star_id == sol_id)

            if is_sol:
                symbol = "diamond"; size = 12; color = "rgb(0, 190, 255)"
            elif battles >= 15:
                symbol = "square"; size = 13 + min(10, battles * 0.2); color = "rgb(255, 20, 20)"
                annotations_3d.append(dict(
                    x=pos[0], y=pos[1], z=pos[2], text=f"⚔️ <b>{assigned_name}</b><br>{battles} Battaglie",
                    showarrow=True, arrowhead=2, ax=20, ay=-25,
                    font=dict(color="#ffffff", size=9),
                    bgcolor="rgba(180, 10, 10, 0.95)", bordercolor="red", borderpad=2
                ))
            elif battles > 0:
                symbol = "circle"; size = 6 + (battles * 0.3); color = "rgb(255, 120, 0)"
            else:
                symbol = "circle"; size = 2.0; color = "rgba(100, 120, 160, 0.15)"

            marker_symbols.append(symbol)
            marker_sizes.append(size)
            marker_colors.append(color)
            hover_texts.append(f"<b>{assigned_name}</b><br>• Schermaglie Totali: {battles}")

        data_traces.append(go.Scatter3d(
            x=x_stars, y=y_stars, z=z_stars, mode='markers',
            marker=dict(size=marker_sizes, color=marker_colors, symbol=marker_symbols, opacity=0.9),
            text=hover_texts, hoverinfo='text', name='Teatri di Guerra'
        ))

        fig = go.Figure(data=data_traces)
        total_skirmishes = sum(combat_sectors_counter.values()) if combat_sectors_counter else 0
        self._apply_layout(fig, f"Mappa Tattica dei Conflitti Galattici ({total_skirmishes} Schermaglie Totali)", annotations_3d)
        
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, "aree_di_conflitto_3d.html")
        fig.write_html(save_path, auto_open=False)
        print(f"[PLOTLY] Salvato grafico conflitti in: {save_path}")

    def plot_lc_evolution_timelines(self, sim_instance, output_dir="outputs/single_runs/plots_lc"):
        os.makedirs(output_dir, exist_ok=True)
        max_t = getattr(sim_instance, 'max_duration_years', 1000.0)
        
        plt.rcParams.update({
            'font.family': 'serif',
            'font.serif': ['Times New Roman', 'DejaVu Serif', 'STIXGeneral', 'serif'],
            'mathtext.fontset': 'stix',
            'font.size': 9.5,
            'axes.labelsize': 10.5,
            'axes.titlesize': 11.0,
            'xtick.labelsize': 9.0,
            'ytick.labelsize': 9.0,
            'legend.fontsize': 7.6,
            'xtick.direction': 'in',
            'ytick.direction': 'in',
            'xtick.top': True,
            'ytick.right': True,
            'savefig.dpi': 300,
            'savefig.bbox': 'tight'
        })

        primordial_factions = {}
        for ag in sim_instance.agents:
            if "Flotta di" not in ag.ship_name and ag.faction_name not in primordial_factions:
                primordial_factions[ag.faction_name] = {
                    "homeworld": None,
                    "colonies": []
                }

        # Correzione BUG-05: Assegnazione diretta e univoca dell'Homeworld per ogni fazione
        for ag in sim_instance.agents:
            if "Flotta di" not in ag.ship_name and ag.faction_name in primordial_factions:
                if primordial_factions[ag.faction_name]["homeworld"] is None:
                    hw_sys = sim_instance.stars.get(ag.origin_system_id)
                    if hw_sys:
                        if hw_sys.is_sol:
                            hw_p = next((p for p in hw_sys.planets if p.original_name_from_gen == sim_instance.earth_planet_name), hw_sys.planets[0] if hw_sys.planets else None)
                        else:
                            hw_p = next((p for p in hw_sys.planets if p.colony_stage == Planet.STAGE_SOVEREIGN and (p.faction_name == ag.faction_name or p.mother_faction == ag.faction_name)), hw_sys.planets[0] if hw_sys.planets else None)
                        primordial_factions[ag.faction_name]["homeworld"] = hw_p

        # Raccoglie le colonie in modo rigorosamente disgiunto (esclude sempre l'homeworld)
        for s_obj in sim_instance.stars.values():
            for p in s_obj.planets:
                if p.is_colonized and p.mother_faction in primordial_factions:
                    hw = primordial_factions[p.mother_faction]["homeworld"]
                    if p != hw and p not in primordial_factions[p.mother_faction]["colonies"]:
                        primordial_factions[p.mother_faction]["colonies"].append(p)

        for mf_name, data in primordial_factions.items():
            hw = data["homeworld"]
            colonies = data["colonies"]
            
            if not hw:
                continue

            fig, ax = plt.subplots(figsize=(7.4, 4.6), dpi=300)
            all_lc_points = [0.85, 1.0]

            emancipated_colonies = [c for c in colonies if c.emancipation_year is not None or c.colony_stage == Planet.STAGE_SOVEREIGN]
            minor_colonies = [c for c in colonies if c not in emancipated_colonies]

            if minor_colonies:
                for col in minor_colonies:
                    if col.lc_history and len(col.lc_history) >= 2:
                        t_vals, lc_vals = zip(*col.lc_history)
                        ax.plot(t_vals, lc_vals, color='#b0bec5', linewidth=0.7, alpha=0.35, zorder=2)
                        all_lc_points.extend(lc_vals)
                
                ax.plot([], [], color='#b0bec5', linewidth=1.2, alpha=0.7, linestyle='-', 
                        label=rf'$\mathrm{{Avamposti\ Dipendenti\ (N={len(minor_colonies)})}}$')

            if hw and hw.lc_history and len(hw.lc_history) >= 2:
                t_hw, lc_hw = zip(*hw.lc_history)
                ax.plot(t_hw, lc_hw, color='#08306b', linewidth=2.4, zorder=5, 
                        label=rf'$\mathbf{{{hw.assigned_name}\ (Madrepatria)}}$')
                all_lc_points.extend(lc_hw)

            distinct_colors = ['#d95f02', '#7570b3', '#e7298a', '#1b9e77', '#e6ab02', '#a6761d']
            has_star_label = False

            for idx, col in enumerate(emancipated_colonies):
                if not col.lc_history or len(col.lc_history) < 2:
                    continue
                
                t_col, lc_col = zip(*col.lc_history)
                col_color = distinct_colors[idx % len(distinct_colors)]
                all_lc_points.extend(lc_col)
                
                ax.plot(t_col, lc_col, color=col_color, linewidth=1.8, linestyle='-', zorder=6, 
                        label=rf'$\mathrm{{Colonia:\ {col.assigned_name}}}$')

                eman_t = col.emancipation_year or t_col[0]
                eman_lc = col.emancipation_lc or lc_col[0]

                star_lbl = r'$\mathrm{Emancipazione\ Sovrana}\ (\bigstar)$' if not has_star_label else ""
                ax.scatter(
                    [eman_t], [eman_lc],
                    color='#ffd700', edgecolor='#000000', linewidth=0.9,
                    s=120, marker='*', zorder=10,
                    label=star_lbl
                )
                has_star_label = True
                
                ax.annotate(
                    rf"$\mathbf{{{col.assigned_name}}}$",
                    xy=(eman_t, eman_lc),
                    xytext=(6, 4), textcoords="offset points",
                    fontsize=7.8, color='#111111',
                    bbox=dict(boxstyle='round,pad=0.25', facecolor='#ffffff', edgecolor='#888888', alpha=0.92),
                    zorder=11
                )

            min_y = min(all_lc_points)
            max_y = max(all_lc_points)
            delta_y = max(0.20, max_y - min_y)
            y_bottom = max(0.0, min_y - (delta_y * 0.12))
            y_top = max_y + (delta_y * 0.14)
            ax.set_ylim(y_bottom, y_top)

            # Linee di Soglia V4.0
            if y_bottom <= 0.20 <= y_top:
                ax.axhline(0.20, color='#c0392b', linestyle=':', linewidth=0.75, zorder=3)
                ax.text(max_t * 0.99, 0.205, r'$\mathrm{Direttiva\ Primaria\ (LC=0.20)}$', 
                        ha='right', va='bottom', fontsize=6.8, color='#c0392b', style='italic')

            if y_bottom <= 0.50 <= y_top:
                ax.axhline(0.50, color='#7f8c8d', linestyle=':', linewidth=0.70, zorder=3)
                ax.text(max_t * 0.99, 0.505, r'$\mathrm{Soglia\ Industriale\ (LC=0.50)}$', 
                        ha='right', va='bottom', fontsize=6.8, color='#7f8c8d', style='italic')

            if y_bottom <= 0.80 <= y_top:
                ax.axhline(0.80, color='#d35400', linestyle=':', linewidth=0.70, zorder=3)
                ax.text(max_t * 0.99, 0.805, r'$\mathrm{Era\ Atomica/Orbitale\ (LC=0.80)}$', 
                        ha='right', va='bottom', fontsize=6.8, color='#d35400', style='italic')

            if y_bottom <= 1.00 <= y_top:
                ax.axhline(1.00, color='#444444', linestyle='--', linewidth=0.85, zorder=3)
                ax.text(max_t * 0.99, 1.005, r'$\mathrm{Spaziale\ Interstellare\ (LC_0=1.00)}$', 
                        ha='right', va='bottom', fontsize=6.8, color='#444444', style='italic')

            if y_bottom <= 1.20 <= y_top:
                ax.axhline(1.20, color='#2980b9', linestyle=':', linewidth=0.75, zorder=3)
                ax.text(max_t * 0.99, 1.205, r'$\mathrm{Flotte\ Multiple\ (LC=1.20)}$', 
                        ha='right', va='bottom', fontsize=6.8, color='#2980b9', style='italic')

            if y_bottom <= 1.40 <= y_top:
                ax.axhline(1.40, color='#27ae60', linestyle=':', linewidth=0.75, zorder=3)
                ax.text(max_t * 0.99, 1.405, r'$\mathrm{Terraformazione\ Accelerata\ (LC=1.40)}$', 
                        ha='right', va='bottom', fontsize=6.8, color='#27ae60', style='italic')

            if y_bottom <= 1.60 <= y_top:
                ax.axhline(1.60, color='#8e44ad', linestyle=':', linewidth=0.75, zorder=3)
                ax.text(max_t * 0.99, 1.585, r'$\mathrm{Soft\text{-}Cap\ Galattico\ (LC=1.60)}$', 
                        ha='right', va='top', fontsize=6.8, color='#8e44ad', style='italic')

            clean_title = mf_name.replace("_", " ").replace("FederazioneTerrestre", "Federazione Terrestre")
            ax.set_title(rf'$\mathrm{{Evoluzione\ Tecnologica\ (LC)\ -\ {clean_title}}}$', pad=9)
            ax.set_xlabel(r'$\mathrm{Tempo\ di\ Missione,}\ t\ [\mathrm{yr}]$')
            ax.set_ylabel(r'$\mathrm{Civilization\ Level\ Metric,}\ \mathrm{LC}$')
            
            ax.set_xlim(0, max_t)
            ax.minorticks_on()
            ax.grid(True, linestyle=':', alpha=0.45)

            handles, labels = ax.get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            n_cols = min(3, max(1, len(by_label)))

            ax.legend(
                by_label.values(), by_label.keys(),
                loc='upper center',
                bbox_to_anchor=(0.5, -0.16),
                ncol=n_cols,
                frameon=True,
                edgecolor='#000000',
                fontsize=7.6,
                framealpha=0.95
            )

            safe_name = re.sub(r'[\W_]+', '_', mf_name).strip('_')
            filepath = os.path.join(output_dir, f"lc_timeline_{safe_name}.png")
            fig.savefig(filepath, bbox_inches='tight')
            plt.close(fig)
            print(f"[PLOT] Salvato grafico LC Primigenio ({clean_title}) in: {filepath}")

    def plot_astrophysical_demographics(self, sim_instance, output_dir="outputs/single_runs/plots_lc", filename="astro_demographics_stars_planets.png"):
        os.makedirs(output_dir, exist_ok=True)
        
        plt.rcParams.update({
            'font.family': 'serif',
            'font.serif': ['Times New Roman', 'DejaVu Serif', 'STIXGeneral', 'serif'],
            'mathtext.fontset': 'stix',
            'font.size': 10.0,
            'axes.labelsize': 11.0,
            'axes.titlesize': 11.5,
            'xtick.labelsize': 9.0,
            'ytick.labelsize': 9.0,
            'legend.fontsize': 8.0,
            'xtick.direction': 'in',
            'ytick.direction': 'in',
            'xtick.top': True,
            'ytick.right': True,
            'savefig.dpi': 300,
            'savefig.bbox': 'tight'
        })

        star_counts = Counter(s.type for s in sim_instance.stars.values())
        spectral_order = ['O', 'B', 'A', 'F', 'G', 'K', 'M']
        star_vals = [star_counts.get(st, 0) for st in spectral_order]
        tot_stars = sum(star_vals)
        
        spectral_palette = ['#0066ff', '#6495ed', '#00ced1', '#ebeb50', '#ffd700', '#ff8c00', '#dc3232']

        all_planets = [p for s in sim_instance.stars.values() for p in s.planets]
        tot_planets = len(all_planets)
        
        planet_type_order = ["Terrestre", "Super-Terra", "Mondo Oceanico", "Roccioso", "Gigante Gassoso", "Gigante Ghiacciato"]
        
        total_p_counts = Counter(p.type for p in all_planets)
        colonized_p_counts = Counter(p.type for p in all_planets if p.is_colonized or p.colony_stage > 0)
        
        gen_vals = [total_p_counts.get(pt, 0) for pt in planet_type_order]
        col_vals = [colonized_p_counts.get(pt, 0) for pt in planet_type_order]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.6), dpi=300)
        
        # Pannello 1: Stelle
        bars1 = ax1.bar(spectral_order, star_vals, color=spectral_palette, edgecolor='#000000', linewidth=0.8, width=0.55)
        for bar in bars1:
            h = bar.get_height()
            pct = (h / max(1, tot_stars)) * 100
            ax1.annotate(f'{h}\n({pct:.1f}%)', xy=(bar.get_x() + bar.get_width() / 2.0, h), xytext=(0, 4),
                         textcoords="offset points", ha='center', va='bottom', fontsize=7.8, color='#000000')

        ax1.set_title(rf'$\mathrm{{Distribuzione\ Spettrale\ Stellare\ (N_{{tot}}={tot_stars})}}$', pad=10)
        ax1.set_xlabel(r'$\mathrm{Classe\ Spettrale\ (IMF)}$')
        ax1.set_ylabel(r'$\mathrm{Numero\ di\ Sistemi\ Stellari}$')
        ax1.set_ylim(0, max(star_vals) * 1.25 if star_vals else 10)
        ax1.minorticks_on(); ax1.grid(axis='y', linestyle=':', alpha=0.5)

        # Pannello 2: Pianeti
        x_indices = np.arange(len(planet_type_order))
        ax2.bar(x_indices, gen_vals, color='#b0bec5', edgecolor='#455a64', linewidth=0.8, width=0.55, 
                label=r'$\mathrm{Pianeti\ Totali\ Generati}$')
        ax2.bar(x_indices, col_vals, color='#2e7d32', edgecolor='#000000', linewidth=0.9, width=0.55, 
                label=r'$\mathrm{Sede\ di\ Avamposto\ /\ Colonia}$')

        for i, (gen, col) in enumerate(zip(gen_vals, col_vals)):
            pct_col = (col / max(1, gen)) * 100
            txt = f"Tot: {gen}\nCol: {col} ({pct_col:.1f}%)" if col > 0 else f"Tot: {gen}\nCol: 0"
            ax2.annotate(txt, xy=(x_indices[i], max(gen, col)), xytext=(0, 4),
                         textcoords="offset points", ha='center', va='bottom', fontsize=7.2, color='#111111')

        ax2.set_title(rf'$\mathrm{{Demografia\ Planetaria\ e\ Tasso\ di\ Colonizzazione\ (N_{{tot}}={tot_planets})}}$', pad=10)
        ax2.set_xlabel(r'$\mathrm{Archetipo\ Planetario}$')
        ax2.set_ylabel(r'$\mathrm{Numero\ di\ Corpi\ Celesti\ [Log_{10}]}$')
        ax2.set_xticks(x_indices)
        ax2.set_xticklabels(["Terrestre", "Super-Terra", "Oceanico", "Roccioso", "Gigante Gas", "Gigante Ice"], rotation=15, ha='right')
        
        ax2.set_yscale('log')
        ax2.set_ylim(0.5, max(gen_vals) * 15 if gen_vals else 100)
        ax2.minorticks_on(); ax2.grid(True, which='both', axis='y', linestyle=':', alpha=0.45)
        ax2.legend(loc='upper right', frameon=True, edgecolor='#000000', framealpha=0.95)

        plt.subplots_adjust(wspace=0.28, bottom=0.18)
        
        filepath = os.path.join(output_dir, filename)
        fig.savefig(filepath, bbox_inches='tight')
        plt.close(fig)
        print(f"[PLOT] Salvato Report Demografia Astrofisica in: {filepath}")

    def _apply_layout(self, fig, title_text, annotations_3d):
        sim_volume_side = self.sim_params.get('simulation_volume_side_ly', 50.0)
        half_side = sim_volume_side / 2.0
        theme_cfg = self.plotly_cfg.get("theme", {})

        paper_bg = theme_cfg.get("paper_bgcolor", "#0a0c14")
        scene_bg = theme_cfg.get("scene_bgcolor", "#0f1322")
        grid_col = theme_cfg.get("grid_color", "rgba(100, 120, 160, 0.20)")
        zero_col = theme_cfg.get("zeroline_color", "rgba(140, 160, 200, 0.40)")
        font_col = theme_cfg.get("font_color", "#e0e6ed")
        tick_col = theme_cfg.get("tickfont_color", "#a0b0c5")

        axis_settings = dict(
            range=[-half_side, half_side],
            backgroundcolor=scene_bg, gridcolor=grid_col, zerolinecolor=zero_col,
            showbackground=True, tickfont=dict(color=tick_col, size=10)
        )

        fig.update_layout(
            title=dict(text=title_text, font=dict(size=15, color=font_col), x=0.5),
            scene=dict(
                xaxis_title='X (ly)', yaxis_title='Y (ly)', zaxis_title='Z (ly)',
                xaxis=axis_settings, yaxis=axis_settings, zaxis=axis_settings,
                aspectmode='cube', annotations=annotations_3d,
                camera=dict(eye=dict(x=1.4, y=1.4, z=1.0))
            ),
            margin=dict(l=10, r=10, b=10, t=60),
            paper_bgcolor=paper_bg, font_color=font_col, showlegend=True,
            legend=dict(
                x=0.01, y=0.99, bgcolor="rgba(15, 20, 35, 0.85)",
                bordercolor="rgba(255, 255, 255, 0.15)", borderwidth=1,
                font=dict(color=font_col, size=10)
            )
        )