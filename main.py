################################################################################
# FILE: main.py
################################################################################

import os
import sys
import re
import datetime
import random
import math
from collections import Counter

from utils.config_loader import load_json_config
from utils.logger import ASCIIExplorationLogger, Tee
from core.universe import UniverseGenerator
from core.civilization import determine_civilization_mobility, Planet
from core.diplomacy import DiplomaticRelation
from core.pathfinding import build_galaxy_graph, find_bfs_path, calculate_distance
from core.simulation import ExplorationSimulation
from visualization.plotter_3d import StarMapPlotter
from analysis.log_parser import ExplorationLogParser
from analysis.strategist import StrategicPlanner

CONFIG_DIR = "config"
OUTPUT_BASE = os.path.join("outputs", "single_runs")
LOG_DIR = os.path.join(OUTPUT_BASE, "logs")
PLAN_DIR = os.path.join(OUTPUT_BASE, "mission_plans")
LC_PLOTS_DIR = os.path.join(OUTPUT_BASE, "plots_lc")
HTML_DIR = os.path.join(OUTPUT_BASE, "html_maps")

SIM_CONFIG_PATH = os.path.join(CONFIG_DIR, "sim_config.json")
INTERACTION_CONFIG_PATH = os.path.join(CONFIG_DIR, "interaction_config.json")
NAMING_CONFIG_PATH = os.path.join(CONFIG_DIR, "naming_config.json")
PLOTLY_CONFIG_PATH = os.path.join(CONFIG_DIR, "plotly_config.json")
AI_DIPLOMACY_CONFIG_PATH = os.path.join(CONFIG_DIR, "ai_diplomacy_config.json")

def main():
    print("================================================================================")
    print("      STELLAR_SIM V4.0 - SIMULATORE MULTI-AGENTE & GEOPOLITICA 3D               ")
    print("================================================================================")
    
    sim_cfg = load_json_config(SIM_CONFIG_PATH, "Sim Config", is_critical=True)
    if "earth_star_name" in sim_cfg and "sol_star_id" not in sim_cfg:
        sim_cfg["sol_star_id"] = sim_cfg["earth_star_name"]

    interaction_cfg = load_json_config(INTERACTION_CONFIG_PATH, "Interaction Config", is_critical=False) or {"interaction_rules": {"earth_lc_start": 1.0}}
    naming_cfg = load_json_config(NAMING_CONFIG_PATH, "Naming Config", is_critical=False) or {}
    plotly_cfg = load_json_config(PLOTLY_CONFIG_PATH, "Plotly Config", is_critical=False) or {}
    ai_cfg = load_json_config(AI_DIPLOMACY_CONFIG_PATH, "AI Diplomacy Config", is_critical=False) or {}

    for d in [LOG_DIR, PLAN_DIR, LC_PLOTS_DIR, HTML_DIR]:
        os.makedirs(d, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filepath = os.path.join(LOG_DIR, f"exploration_console_output_{timestamp}.txt")
    
    original_stdout = sys.stdout
    log_file_handle = open(log_filepath, 'w', encoding='utf-8')
    sys.stdout = Tee(sys.stdout, log_file_handle)
    
    VERBOSITY_LEVEL = 1
    simulation_logger = ASCIIExplorationLogger(verbosity=VERBOSITY_LEVEL)

    sim = None
    stars_data = []
    galaxy_graph = {}

    try:
        universe_gen = UniverseGenerator(sim_cfg, naming_cfg)
        stars_data = universe_gen.generate_star_field()
        print(f"[UNIVERSO] Generati {len(stars_data)} sistemi stellari con parametri ESI e astrofisici.")

        mobility = determine_civilization_mobility(sim_cfg)
        ship_speed = mobility["ship_speed_ly_per_year"]
        max_reach = mobility["max_reach_ly"]

        print(f"\n[PARAMETRI TERRESTRI ESTRATTI]")
        print(f" • Velocità di crociera: {mobility['ship_speed_c']:.3f} c ({mobility['ship_speed_ly_per_year']:.3f} ly/anno)")
        print(f" • Portata massima singolo salto: {max_reach:.2f} ly\n")

        galaxy_graph = build_galaxy_graph(stars_data, max_reach)

        sim = ExplorationSimulation(
            stars_raw=stars_data,
            galaxy_graph=galaxy_graph,
            sim_params={**sim_cfg, "ship_speed_ly_per_year": ship_speed, "max_reach_ly": max_reach},
            interaction_cfg=interaction_cfg,
            naming_cfg=naming_cfg,
            logger=simulation_logger,
            ai_diplomacy_cfg=ai_cfg
        )
        
        sim.run()

    except Exception as e:
        print(f"\n[ERRORE CRITICO DURANTE LA SIMULAZIONE]: {e}")
        import traceback
        traceback.print_exc(file=sys.stdout)
    finally:
        sys.stdout = original_stdout
        log_file_handle.close()
        print(f"\n[LOG] Sessione salvata in: {log_filepath}")

    if sim and stars_data:
        print("\n--- AVVIO GENERAZIONE VISUALIZZAZIONI 3D PLOTLY & REPORT ---")
        
        stars_dict = {
            sid: {
                'id': sid, 'position': s_obj.position, 'type': s_obj.type,
                'has_starbase': s_obj.has_starbase, 'starbase_owner': s_obj.starbase_owner,
                'starbase_status': s_obj.starbase_status, 'starbase_name': s_obj.starbase_name,
                'assigned_name': s_obj.assigned_name
            }
            for sid, s_obj in sim.stars.items()
        }
        
        sol_id = sim_cfg['sol_star_id']
        assigned_names_map = {sid: sys_obj.assigned_name for sid, sys_obj in sim.stars.items()}

        plotter = StarMapPlotter(sim_cfg, plotly_cfg)

        plotter.plot_simulation_plotly(stars_dict, galaxy_graph, sol_id, sim.agents, sim.diplomacy.trade_routes, output_dir=HTML_DIR)
        plotter.plot_trade_network_3d(stars_dict, sim.diplomacy.trade_routes, sol_id, assigned_names_map, output_dir=HTML_DIR)
        combat_counter = getattr(sim, 'cumulative_combat_sectors', Counter())
        plotter.plot_conflict_zones_3d(stars_dict, sim.diplomacy, combat_counter, sol_id, assigned_names_map, output_dir=HTML_DIR)

        logistics_graph = build_galaxy_graph(stars_data, max_reach_ly=12.0)
        initial_homeworlds = {ag.origin_system_id: ag.faction_name for ag in sim.agents if "Flotta di" not in ag.ship_name}

        for hw_id, hw_faction in initial_homeworlds.items():
            routes_details = []
            for s_id, sys_obj in sim.stars.items():
                if s_id == hw_id: continue

                if sys_obj.has_starbase and (sys_obj.starbase_owner == hw_faction or hw_faction in str(sys_obj.starbase_owner)):
                    path_ids = find_bfs_path(logistics_graph, hw_id, sys_obj.original_id) or [hw_id, sys_obj.original_id]
                    legs = [{"from_id": path_ids[i], "to_id": path_ids[i+1]} for i in range(len(path_ids)-1)]
                    routes_details.append({
                        "colony_name": f"Starbase {sys_obj.assigned_name}", "stage_name": "Starbase Orbitale",
                        "is_emancipated": False, "is_hostile": (sys_obj.starbase_status != "Leale"),
                        "is_starbase": True, "path_ids": path_ids, "detailed_legs": legs
                    })

                for p in sys_obj.planets:
                    if (p.is_colonized or p.colony_stage > 0) and (p.mother_faction == hw_faction or hw_faction in str(p.faction_name)):
                        path_ids = find_bfs_path(logistics_graph, hw_id, sys_obj.original_id) or [hw_id, sys_obj.original_id]
                        legs = [{"from_id": path_ids[i], "to_id": path_ids[i+1]} for i in range(len(path_ids)-1)]
                        is_emancipated = (p.colony_stage == Planet.STAGE_SOVEREIGN or p.is_independent)
                        rel_with_mother = sim.diplomacy.get_relation(hw_faction, p.faction_name)
                        is_hostile = is_emancipated and (p.colony_disposition in ["Ostile", "Predatoria"] or rel_with_mother == DiplomaticRelation.GUERRA)
                        
                        routes_details.append({
                            "colony_name": p.assigned_name, "stage_name": p.colony_stage_name,
                            "is_emancipated": is_emancipated, "is_hostile": is_hostile,
                            "is_starbase": False, "path_ids": path_ids, "detailed_legs": legs
                        })

            safe_name = re.sub(r'[\W_]+', '_', hw_faction).strip('_')
            filename = os.path.join(HTML_DIR, f"rotta_colonie_{safe_name}_3d.html")
            plotter.plot_colonies_routes(stars_dict, logistics_graph, routes_details, hw_id, hw_faction, assigned_names_map, filename)

        print("\n--- GENERAZIONE GRAFICI TEMPORALI LC (MNRAS / A&A) ---")
        plotter.plot_lc_evolution_timelines(sim, output_dir=LC_PLOTS_DIR)

        print("\n--- GENERAZIONE REPORT DEMOGRAFIA STELLE & PIANETI ---")
        plotter.plot_astrophysical_demographics(sim, output_dir=LC_PLOTS_DIR)

    print("\n--- PIANIFICAZIONE STRATEGICA POST-ESPLORAZIONE ---")
    parser = ExplorationLogParser(LOG_DIR, "exploration_console_output_")
    log_files = parser.list_log_files()
    if log_files:
        latest_log = os.path.join(LOG_DIR, log_files[0])
        summary_lines = parser.parse_summary_from_file(latest_log)
        planets_parsed = parser.extract_planets_data(summary_lines)
        planner = StrategicPlanner(interaction_cfg)
        strategic_plan = planner.generate_plan(planets_parsed)
        planner.save_plan_to_file(strategic_plan, PLAN_DIR)

    print("\nEsecuzione completata con successo.")

if __name__ == "__main__":
    main()