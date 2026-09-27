################################################################################
# FILE: analysis/montecarlo.py
################################################################################

import os
import csv
import time
import datetime
import random
import sys
import multiprocessing
from collections import Counter

from core.universe import UniverseGenerator
from core.civilization import determine_civilization_mobility, Planet
from core.pathfinding import build_galaxy_graph
from core.simulation import ExplorationSimulation
from utils.logger import ASCIIExplorationLogger

def run_single_monte_carlo_iteration(iteration_args):
    run_id, total_runs, sim_cfg, interaction_cfg, naming_cfg, ai_cfg, log_output_dir, verbosity = iteration_args
    
    run_seed = sim_cfg.get("base_seed", 42) + run_id
    random.seed(run_seed)
    
    local_sim_cfg = dict(sim_cfg)
    local_sim_cfg["seed"] = run_seed

    if not os.path.exists(log_output_dir):
        os.makedirs(log_output_dir, exist_ok=True)
        
    log_filepath = os.path.join(log_output_dir, f"monte_carlo_run_{run_id}_seed_{run_seed}.log")
    log_file_handle = open(log_filepath, 'w', encoding='utf-8')
    
    run_logger = ASCIIExplorationLogger(verbosity=verbosity)

    original_stdout = sys.stdout
    sys.stdout = log_file_handle

    sim_completed_normally = False
    result_row = None

    try:
        universe_gen = UniverseGenerator(local_sim_cfg, naming_cfg)
        stars_data = universe_gen.generate_star_field()

        mobility = determine_civilization_mobility(local_sim_cfg)
        ship_speed = mobility["ship_speed_ly_per_year"]
        max_reach = mobility["max_reach_ly"]

        galaxy_graph = build_galaxy_graph(stars_data, max_reach)

        sim = ExplorationSimulation(
            stars_raw=stars_data,
            galaxy_graph=galaxy_graph,
            sim_params={**local_sim_cfg, "ship_speed_ly_per_year": ship_speed, "max_reach_ly": max_reach},
            interaction_cfg=interaction_cfg,
            naming_cfg=naming_cfg,
            logger=run_logger,
            ai_diplomacy_cfg=ai_cfg
        )
        
        sim.run()
        
        final_year = sim.logger.simulation_time_hours / (24 * 365.25)
        
        if final_year > 0:
            sim_completed_normally = True

            # Astrobiologia & Drake ESI
            total_surveyed_planets = [p for s in sim.stars.values() for p in s.planets if p.is_explored_for_life]
            n_habitable = sum(1 for p in total_surveyed_planets if p.is_potentially_habitable())
            n_life = sum(1 for p in total_surveyed_planets if p.has_life)
            n_intel = sum(1 for p in total_surveyed_planets if p.has_life and p.life_is_intelligent)
            n_space = sum(1 for p in total_surveyed_planets if p.has_life and p.life_is_intelligent and (p.civilization_level or 0.0) >= 1.0)
            
            n_prime_directive_protected = sum(
                1 for p in total_surveyed_planets 
                if p.has_life and p.life_is_intelligent and 0.20 <= (p.civilization_level or 0.0) < 1.0
            )

            # Riferimento alla Terra (Madrepatria)
            earth_p = next(
                (p for s in sim.stars.values() if s.is_sol for p in s.planets if p.original_name_from_gen == sim.earth_planet_name), 
                None
            )
            earth_final_lc = round(earth_p.civilization_level, 4) if (earth_p and earth_p.civilization_level) else 1.0

            # Esclusione rigorosa della Terra dal pool delle colonie extraterrestri
            earth_colonies = [
                p for s in sim.stars.values() for p in s.planets 
                if (p.is_colonized or p.colony_stage > 0) and p.mother_faction == "Federazione Terrestre" and p != earth_p
            ]
            
            n_colonies_active = len(earth_colonies)
            n_sovereign = sum(1 for p in earth_colonies if p.colony_stage == Planet.STAGE_SOVEREIGN)
            n_secession_hostile = sum(
                1 for p in earth_colonies 
                if p.colony_stage == Planet.STAGE_SOVEREIGN and p.colony_disposition in ["Ostile", "Predatoria", "Diffidente"]
            )
            n_secession_loyal = sum(
                1 for p in earth_colonies 
                if p.colony_stage == Planet.STAGE_SOVEREIGN and p.colony_disposition in ["Collaborativa", "Leale a Sol", "Leale alla Madrepatria", "Pacifica"]
            )
            
            # Popolazione cumulativa umana: Terra + colonie extraterrestri
            colony_pop = sum(p.population_millions for p in earth_colonies)
            earth_pop = earth_p.population_millions if earth_p else 0.0
            total_human_pop_millions = round(earth_pop + colony_pop, 2)

            # Divergenza tecnologica tra le colonie extraterrestri e la Terra
            colony_lcs = [p.civilization_level for p in earth_colonies if p.civilization_level is not None]
            if colony_lcs:
                max_colony_lc = round(max(colony_lcs), 4)
                delta_lc_max = round(max_colony_lc - earth_final_lc, 4)
                colony_surpassed = bool(max_colony_lc > earth_final_lc)
            else:
                max_colony_lc = earth_final_lc
                delta_lc_max = 0.0
                colony_surpassed = False

            total_fleets_activated = len(sim.agents)
            total_starbases = sum(1 for s in sim.stars.values() if s.has_starbase)
            fallen_starbases = sum(1 for s in sim.stars.values() if s.has_starbase and s.starbase_status != "Leale")
            trade_routes_count = len(sim.diplomacy.trade_routes)
            total_wars = len(sim.diplomacy.relations) if hasattr(sim, 'diplomacy') else 0
            total_systems_explored = len(sim.visited_system_ids)

            result_row = {
                "run_id": run_id,
                "seed": run_seed,
                "num_stars": len(stars_data),
                "ship_speed_c": round(mobility["ship_speed_c"], 3),
                "max_reach_ly": round(max_reach, 2),
                "first_contact_occurred": sim.first_contact_occurred,
                "contact_type": sim.first_contact_type,
                "time_to_first_contact_years": sim.first_contact_year,
                "contact_distance_ly": sim.first_contact_distance_ly,
                "contact_disposition": sim.first_contact_disposition or "Nessuna",
                "systems_before_contact": sim.systems_explored_before_contact if sim.first_contact_occurred else total_systems_explored,
                "archeological_relics_found": sim.archeological_sites_discovered,
                "total_systems_explored": total_systems_explored,
                "max_expansion_radius_ly": sim.max_heliocentric_distance_reached_ly,
                
                # Astrobiologia & Drake ESI
                "planets_habitable_surveyed": n_habitable,
                "planets_with_life_surveyed": n_life,
                "planets_with_intel_surveyed": n_intel,
                "planets_with_spacefaring_surveyed": n_space,
                "prime_directive_encounters": n_prime_directive_protected,
                
                # Colonie & Flotte V4.0 (Depurate da Sol)
                "colonies_founded": sim.total_colonies_founded,
                "colonies_active": n_colonies_active,
                "total_earth_colonies": n_colonies_active,
                "colonies_collapsed": sim.total_colonies_collapsed,
                "colonies_sovereign": n_sovereign,
                "colonies_secession_hostile": n_secession_hostile,
                "colonies_secession_loyal": n_secession_loyal,
                "total_human_pop_millions": total_human_pop_millions,
                "total_fleets_activated": total_fleets_activated,
                
                # Tecnologia & Geopolitica
                "earth_final_lc": round(earth_final_lc, 3),
                "max_colony_lc": round(max_colony_lc, 3),
                "delta_lc_max": delta_lc_max,
                "colony_surpassed_earth": colony_surpassed,
                "total_starbases": total_starbases,
                "fallen_starbases": fallen_starbases,
                "total_trade_routes": trade_routes_count,
                "total_wars": total_wars,
                "simulation_duration_years": round(final_year, 2),
                "log_filename": os.path.basename(log_filepath)
            }
            
            run_logger.close_log()

    except Exception as e:
        print(f"\n[ERRORE CRITICO RUN #{run_id}]: {e}")
        sim_completed_normally = False
        result_row = None
        
    finally:
        sys.stdout = original_stdout
        log_file_handle.close()

    if not sim_completed_normally or result_row is None:
        return None

    return result_row


class MonteCarloBatchEngine:
    def __init__(self, sim_cfg, interaction_cfg, naming_cfg, ai_cfg, base_folder=None, custom_timestamp=None):
        self.sim_cfg = sim_cfg
        self.interaction_cfg = interaction_cfg
        self.naming_cfg = naming_cfg
        self.ai_cfg = ai_cfg
        
        target_base = base_folder or os.path.join("outputs", "batch_runs")
        ts = custom_timestamp or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = os.path.join(target_base, f"batch_monte_carlo_{ts}")
        self.log_dir = os.path.join(self.output_dir, "logs")

    def run_batch(self, num_iterations=500, processes=None, verbosity=1):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)

        if processes is None:
            processes = max(1, multiprocessing.cpu_count() - 2)

        mode_str = "CRONACA COMPLETA (verbosity=1)" if verbosity >= 1 else "SILENTE / SOLO CSV (verbosity=0)"
        print("================================================================================")
        print(f"   AVVIO MOTORE MONTE CARLO BATCH V4.0 ({num_iterations} Run su {processes} Core CPU)")
        print(f"   Modalità Log: {mode_str}")
        print(f"   📂 Output Batch salvato in: {os.path.abspath(self.output_dir)}/")
        print("================================================================================")

        args_list = [
            (i + 1, num_iterations, self.sim_cfg, self.interaction_cfg, self.naming_cfg, self.ai_cfg, self.log_dir, verbosity)
            for i in range(num_iterations)
        ]

        start_time = time.time()
        results = []

        with multiprocessing.Pool(processes=processes) as pool:
            completed = 0
            for res in pool.imap_unordered(run_single_monte_carlo_iteration, args_list):
                completed += 1
                if res:
                    results.append(res)
                sys.stdout.write(f"\rEsecuzione Monte Carlo V4.0: {completed} / {num_iterations} run completate...")
                sys.stdout.flush()

        elapsed_time = time.time() - start_time
        print(f"\n\n[MONTE CARLO V4.0] Batch completato in {elapsed_time:.2f} s ({elapsed_time/num_iterations:.3f} s/run).")

        dataset_path = os.path.join(self.output_dir, "monte_carlo_runs_dataset.csv")
        if results:
            keys = results[0].keys()
            with open(dataset_path, 'w', newline='', encoding='utf-8') as output_file:
                dict_writer = csv.DictWriter(output_file, fieldnames=keys)
                dict_writer.writeheader()
                dict_writer.writerows(results)
            print(f"[DATASET] Tabella riassuntiva salvata in: {dataset_path}")

        return results