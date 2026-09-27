################################################################################
# FILE: core/simulation.py
# VERSIONE V5.4 - OTTIMIZZATA PER DEEP TIME CON MEMOIZATION BFS E SPATIAL HASHING
################################################################################

import random
import copy
import os
import json
import math
from collections import Counter, defaultdict

from core.civilization import StarSystem, Planet
from core.pathfinding import calculate_distance, build_galaxy_graph, find_bfs_path
from core.agents import AgentShip
from core.diplomacy import DiplomaticManager, DiplomaticRelation, HeuristicAIDiplomacyAgent
from utils.news_feed import GalacticNewsNetwork
from utils.logger import ASCIIExplorationLogger

ACTION_DURATIONS = {
    "travel_interstellar": lambda dist, speed: (dist / speed) * 365.25 * 24, 
    "scan_system": 24 * 7, 
    "explore_planet_surface": 24 * 14, 
    "establish_colony_base": 24 * 30 * 6, 
    "build_starbase_depot": 24 * 30 * 4,
    "trade_exchange": 24 * 5
}

class ExplorationSimulation:
    def __init__(
        self,
        stars_raw,
        galaxy_graph,
        sim_params,
        interaction_cfg=None,
        naming_cfg=None,
        logger=None,
        ai_diplomacy_cfg=None
    ):
        self.logger = logger if isinstance(logger, ASCIIExplorationLogger) else ASCIIExplorationLogger(verbosity=1)
        self.ai_diplomacy_cfg = ai_diplomacy_cfg if isinstance(ai_diplomacy_cfg, dict) else {}

        if not self.ai_diplomacy_cfg:
            ai_path = os.path.join("config", "ai_diplomacy_config.json")
            if os.path.exists(ai_path):
                try:
                    with open(ai_path, 'r', encoding='utf-8') as f:
                        self.ai_diplomacy_cfg = json.load(f)
                except Exception:
                    self.ai_diplomacy_cfg = {}

        self.sim_params = sim_params or {}
        self.interaction_cfg = interaction_cfg or {}
        self.naming_cfg = naming_cfg or {}
        
        # Dual-Mode temporale
        self.temporal_mode = self.sim_params.get("temporal_mode", "TACTICAL_ACCELERATED")
        is_deep_time = (self.temporal_mode == "DEEP_TIME_ASTROPHYSICAL")
        
        default_duration = 10000.0 if is_deep_time else 1000.0
        self.max_duration_years = float(self.sim_params.get('max_mission_duration_years', default_duration))
        self.geopolitics_interval_years = 50.0 if is_deep_time else 5.0
        gnn_broadcast_interval = 500.0 if is_deep_time else 50.0

        self.stars = {s['id']: StarSystem(s) for s in stars_raw}
        self.galaxy_graph = galaxy_graph
        self.sol_id = self.sim_params.get('sol_star_id', 'Sol')
        self.earth_planet_name = self.sim_params.get('earth_planet_name', 'Terra')
        
        self.box_side_ly = float(self.sim_params.get('simulation_volume_side_ly', 70.0))
        self.box_half_side_ly = self.box_side_ly / 2.0
        self.max_spawn_radius_ly = float(self.sim_params.get('civilization_max_spawn_radius_ly', 18.0))
        
        watchdog_cfg = self.sim_params.get('edge_watchdog', {})
        self.watchdog_enabled = watchdog_cfg.get('enabled', True)
        self.watchdog_buffer_margin_ly = float(watchdog_cfg.get('buffer_margin_ly', 4.0))
        self.watchdog_repulsion = watchdog_cfg.get('apply_repulsion_penalty', True)
        self.logged_edge_warnings = set()

        ai_engine = HeuristicAIDiplomacyAgent(self.ai_diplomacy_cfg)
        self.diplomacy = DiplomaticManager(ai_agent=ai_engine)

        self.mechanics = self.sim_params.get('ship_mechanics', {})
        self.fuel_base = self.mechanics.get('fuel_consumption_base', 0.08)
        self.fuel_per_ly = self.mechanics.get('fuel_consumption_per_ly', 0.006)
        self.health_per_ly = self.mechanics.get('health_decay_per_ly', 0.0015)
        self.colony_refuel = self.mechanics.get('colony_refuel_fuel', 0.75)
        self.colony_repair = self.mechanics.get('colony_repair_health', 0.5)

        rules_cfg = self.interaction_cfg.get('interaction_rules', {})
        self.prime_directive_threshold = rules_cfg.get('prime_directive_absolute_lc_threshold', 0.20)

        gnn_cfg = self.interaction_cfg.get('gnn_settings', {})
        self.gnn_enabled = gnn_cfg.get('enabled', True)
        self.gnn = GalacticNewsNetwork(gnn_broadcast_interval)

        gf_cfg = self.interaction_cfg.get('great_filter', {})
        self.filter_chance = gf_cfg.get('extinction_chance_on_civ', 0.30)
        self.cataclysms = gf_cfg.get('cataclysm_types', [
            "Collasso Ecologico e Climatico", 
            "Guerra Termonucleare Globale", 
            "Inverno da Impatto Asteroideo",
            "Crisi dell'Intelligenza Artificiale Ostile",
            "Pandemia Sintetica Incontrollata"
        ])
        self.relic_fuel_bonus = gf_cfg.get('archeological_relic_fuel_bonus', 0.40)
        self.relic_health_bonus = gf_cfg.get('archeological_relic_health_bonus', 0.25)

        self.colony_disp_weights = self.interaction_cfg.get('colony_independence_disposition', {"Ostile": 25, "Diffidente": 30, "Neutrale": 25, "Collaborativa": 20})

        self.visited_system_ids = set()
        self.assigned_star_names = set()
        self.active_colonies = []
        self.existing_planet_names = set()
        self.resolved_encounters = set()
        self.known_wars_logged = set()
        self.known_starbase_losses = set()
        self.unlocked_secondary_fleets = set()
        self.logged_planet_contacts = set()
        
        self.cumulative_combat_sectors = Counter()
        
        self.first_contact_occurred = False
        self.first_contact_year = None
        self.first_contact_type = "Solitudine / Nessun Contatto"
        self.first_contact_civ_name = None
        self.first_contact_distance_ly = None
        self.first_contact_disposition = None
        self.systems_explored_before_contact = 0
        self.archeological_sites_discovered = 0
        
        self.total_colonies_founded = 0
        self.total_colonies_collapsed = 0
        self.max_heliocentric_distance_reached_ly = 0.0
        
        self.latin_numerals = self.naming_cfg.get("planet_naming", {}).get("latin_numerals", ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"])
        self.earth_lc = self.interaction_cfg.get("interaction_rules", {}).get("earth_lc_start", 1.0)
        
        self.last_colony_check_year = 0.0
        self.last_geopolitics_check_year = 0.0
        self.agents = []

        # ======================================================================
        # OTTIMIZZAZIONI DI PERFORMANCE V5.4 PER DEEP TIME
        # ======================================================================
        self._path_cache = {}          # Caching BFS per rotte di rifornimento
        self._system_hab_cache = {}    # Cache statica dell'abitabilità dei sistemi
        self._precompute_system_habitability()

        self._init_sol_system()
        self._init_agents()

    def _precompute_system_habitability(self):
        """Pre-calcola l'abitabilità potenziale dei sistemi stellari per velocizzare il pathfinding."""
        for sid, s_obj in self.stars.items():
            self._system_hab_cache[sid] = s_obj.has_habitable_candidate()

    def _cached_find_bfs_path(self, start_id, target_id):
        """Versione con memoization della ricerca cammino minimo per le linee logistiche."""
        if start_id == target_id:
            return [start_id]
        key = (start_id, target_id)
        if key in self._path_cache:
            return self._path_cache[key]
        
        path = find_bfs_path(self.galaxy_graph, start_id, target_id)
        if path:
            self._path_cache[key] = path
            rev_key = (target_id, start_id)
            if rev_key not in self._path_cache:
                self._path_cache[rev_key] = list(reversed(path))
        return path

    def _init_sol_system(self):
        sol = self.stars.get(self.sol_id)
        if sol:
            sol.assigned_name = self.sol_id
            self.assigned_star_names.add(self.sol_id)
            sol.controlling_faction = "Federazione Terrestre"
            sol.ensure_planets_star_name(self.latin_numerals)
            
            for p in sol.planets:
                p.is_explored_for_life = True
                p.is_explored_for_surface = True
                if p.original_name_from_gen == self.earth_planet_name:
                    p.has_life = True
                    p.life_is_intelligent = True
                    p.civilization_level = self.earth_lc
                    p.disposition = "Collaborativa"
                    p.civilization_name = "Federazione Terrestre"
                    p.assigned_name = self.earth_planet_name
                    p.has_custom_proper_name = True
                    p.colony_stage = Planet.STAGE_SOVEREIGN
                    p.is_colonized = True
                    p.faction_name = "Federazione Terrestre"
                    p.mother_faction = "Federazione Terrestre"
                    p.homeworld_system_id = self.sol_id
                    p.population_millions = 8500.0
                    self.existing_planet_names.add(self.earth_planet_name)
                    p.record_lc_snapshot(0.0)

    def _init_agents(self):
        earth_speed = self.sim_params.get('ship_speed_ly_per_year', 0.25)
        earth_reach = self.sim_params.get('max_reach_ly', 6.0)
        earth_ship = AgentShip(
            "ISS Enterprise", "Federazione Terrestre", self.sol_id, 
            earth_speed, earth_reach, is_terrestrial=True, disposition="Collaborativa", civilization_level=self.earth_lc
        )
        self.agents.append(earth_ship)
        self.visited_system_ids.add(self.sol_id)
        self.stars[self.sol_id].visited_by_ship = True

        self._spawn_initial_alien_civilizations()

    def _is_near_boundary(self, position):
        limit = self.box_half_side_ly - self.watchdog_buffer_margin_ly
        return any(abs(coord) >= limit for coord in position)

    def _get_boundary_distance(self, position):
        dist_x = self.box_half_side_ly - abs(position[0])
        dist_y = self.box_half_side_ly - abs(position[1])
        dist_z = self.box_half_side_ly - abs(position[2])
        return min(dist_x, dist_y, dist_z)

    def _check_and_log_edge_watchdog(self, agent: AgentShip, system: StarSystem):
        if not self.watchdog_enabled:
            return
        
        if self._is_near_boundary(system.position):
            warning_key = (agent.ship_name, system.original_id)
            if warning_key not in self.logged_edge_warnings:
                self.logged_edge_warnings.add(warning_key)
                min_d = self._get_boundary_distance(system.position)
                time_str = self.logger.get_time_str()
                self.logger.log_raw(
                    f"    [{time_str}] ⚠️ [EDGE WATCHDOG] {agent.ship_name} in avvicinamento al confine galattico su {system.assigned_name} (Margine: {min_d:.1f} ly). Ammortizzatore cinematico attivo.",
                    indent=0, min_verbosity=1
                )

    def _spawn_initial_alien_civilizations(self):
        civ_cfg = self.interaction_cfg.get("civilization_generation", {})
        disp_cfg = self.interaction_cfg.get("disposition_generation", {})
        bio_cfg = self.interaction_cfg.get("biology", {})

        max_possible = self.sim_params.get("max_initial_interstellar_civilizations", 2)
        custom_weights = self.sim_params.get("initial_civilizations_distribution_weights")
        possible_counts = list(range(max_possible + 1))

        if custom_weights and len(custom_weights) == len(possible_counts):
            weights = custom_weights
        else:
            default_curve = [55, 30, 15]
            weights = default_curve[:max_possible + 1]
            if len(weights) < len(possible_counts):
                weights += [2] * (len(possible_counts) - len(weights))

        target_alien_count = random.choices(possible_counts, weights=weights, k=1)[0]

        if target_alien_count == 0:
            print(f"[UNIVERSO] Civiltà aliene attive all'anno zero: 0 (Silenzio Cosmico Assoluto).")
            return

        sol_pos = self.stars[self.sol_id].position

        candidate_stars = [
            (sid, s_obj, [p for p in s_obj.planets if p.is_potentially_habitable()])
            for sid, s_obj in self.stars.items() 
            if sid != self.sol_id 
            and calculate_distance(sol_pos, s_obj.position) <= self.max_spawn_radius_ly
            and [p for p in s_obj.planets if p.is_potentially_habitable()]
        ]

        if not candidate_stars:
            candidate_stars = [
                (sid, s_obj, s_obj.planets) 
                for sid, s_obj in self.stars.items() 
                if sid != self.sol_id and calculate_distance(sol_pos, s_obj.position) <= self.max_spawn_radius_ly and s_obj.planets
            ]

        if not candidate_stars:
            candidate_stars = [
                (sid, s_obj, s_obj.planets) 
                for sid, s_obj in self.stars.items() 
                if sid != self.sol_id and s_obj.planets
            ]

        random.shuffle(candidate_stars)
        selected_homeworlds = candidate_stars[:target_alien_count]

        print(f"[UNIVERSO] Civiltà aliene attive entro la Sfera di Spawn ({self.max_spawn_radius_ly:.1f} ly): {len(selected_homeworlds)}")

        tiers = civ_cfg.get("tiers", [])
        adv_tiers = [t for t in tiers if t.get('lc_min', 0.0) >= 0.90] or tiers

        has_custom_maturity = "initial_alien_lc_range" in self.sim_params
        lc_maturity_range = self.sim_params.get("initial_alien_lc_range", [1.0, 1.35])

        for sid, s_obj, planet_list in selected_homeworlds:
            if s_obj.assigned_name == s_obj.original_id:
                s_obj.assigned_name = self._generate_unique_star_name()
            s_obj.ensure_planets_star_name(self.latin_numerals)

            home_planet = planet_list[0]
            home_planet.assign_proper_name(self.existing_planet_names, self.naming_cfg)
            home_planet.has_life = True
            home_planet.life_is_intelligent = True
            home_planet.is_explored_for_life = True
            home_planet.is_explored_for_surface = True
            
            home_planet.base_life_form = random.choices(
                bio_cfg.get("base_forms", ["Carbonio-Acqua"]),
                weights=bio_cfg.get("base_form_weights", [100]),
                k=1
            )[0]

            if has_custom_maturity:
                home_planet.civilization_level = round(random.uniform(lc_maturity_range[0], lc_maturity_range[1]), 2)
                chosen_tier = next((t for t in sorted(tiers, key=lambda x: x.get('lc_min', 0), reverse=True) 
                                    if home_planet.civilization_level >= t.get('lc_min', 0)), tiers[-1] if tiers else {})
            else:
                chosen_tier = random.choice(adv_tiers) if adv_tiers else {"lc_min": 1.0, "lc_max": 1.35}
                home_planet.civilization_level = round(random.uniform(chosen_tier.get('lc_min', 1.0), chosen_tier.get('lc_max', 1.35)), 2)

            prefix = random.choice(chosen_tier.get('naming_prefixes', ["Impero di", "Dominio di", "Repubblica di"]))
            home_planet.civilization_name = f"{prefix} {home_planet.assigned_name}"
            home_planet.social_structure = random.choice(chosen_tier.get('structures', ["Tradizionale", "Tecnocrazia"]))
            home_planet.dominant_ethic = random.choice(chosen_tier.get('ethics', ["Neutrale", "Espansionista", "Pacifista"]))
            home_planet.unity_level = chosen_tier.get('tier_name', "Spaziale Avanzato")

            disp_dist = disp_cfg.get("distribution", {"Collaborativa": 20, "Cauta": 25, "Diffidente": 30, "Ostile": 25})
            home_planet.disposition = random.choices(list(disp_dist.keys()), weights=list(disp_dist.values()), k=1)[0]
            home_planet.colony_stage = Planet.STAGE_SOVEREIGN
            home_planet.is_colonized = True
            home_planet.population_millions = round(random.uniform(3500.0, 9000.0), 1)
            home_planet.faction_name = home_planet.civilization_name
            home_planet.mother_faction = home_planet.civilization_name
            home_planet.homeworld_system_id = sid
            home_planet.record_lc_snapshot(0.0)

            s_obj.controlling_faction = home_planet.civilization_name

            if home_planet.civilization_level >= 1.0:
                max_c = self.sim_params.get('max_exploration_speed_c', 0.35)
                alien_speed = round(min(max_c, 0.15 + (home_planet.civilization_level * 0.14)), 3)
                alien_reach = round(alien_speed * random.uniform(16.0, 24.0), 2)
                ship_name = f"Ammiraglia di {home_planet.assigned_name}"
                
                alien_ship = AgentShip(
                    ship_name, home_planet.civilization_name, sid,
                    alien_speed, alien_reach, is_terrestrial=False, disposition=home_planet.disposition, civilization_level=home_planet.civilization_level
                )

                sol_sys = self.stars.get(self.sol_id)
                earth_p = next((p for p in sol_sys.planets if p.original_name_from_gen == self.earth_planet_name), None) if sol_sys else None
                earth_disp = earth_p.disposition if earth_p else "Collaborativa"
                self.diplomacy.evaluate_initial_relation("Federazione Terrestre", earth_disp, home_planet.civilization_name, home_planet.disposition)
                
                self.agents.append(alien_ship)
                self.visited_system_ids.add(sid)
                s_obj.visited_by_ship = True
            else:
                home_planet.has_spawned_autonomous_fleet = False

    def _check_and_spawn_multiship_fleets(self):
        current_year = self.logger.simulation_time_hours / (24 * 365.25)
        sovereign_planets = [p for s in self.stars.values() for p in s.planets if p.colony_stage == Planet.STAGE_SOVEREIGN]
        max_c = self.sim_params.get('max_exploration_speed_c', 0.35)
        
        for p in sovereign_planets:
            lc = p.civilization_level or 1.0
            faction = p.faction_name
            # Ottimizzazione O(1): uso del puntatore star_system_id
            orig_sid = p.star_system_id or p.homeworld_system_id

            if lc >= 1.0 and not getattr(p, 'has_spawned_autonomous_fleet', True):
                p.has_spawned_autonomous_fleet = True
                if orig_sid and orig_sid in self.stars:
                    speed = round(min(max_c, 0.15 + (lc * 0.14)), 3)
                    reach = round(speed * random.uniform(16.0, 24.0), 2)
                    ship_name = f"Ammiraglia di {p.assigned_name}"
                    new_ship = AgentShip(
                        ship_name, faction, orig_sid,
                        speed, reach, is_terrestrial=False, disposition=p.disposition or "Collaborativa", civilization_level=lc
                    )
                    self.agents.append(new_ship)
                    self.visited_system_ids.add(orig_sid)
                    self.stars[orig_sid].visited_by_ship = True
                    time_str = f"T + {current_year:6.2f} yr"
                    self.logger.log_raw(f"  [{time_str}] 🚀 [EMERGENZA INTERSTELLARE] {faction} raggiunge LC = {lc:.2f}! Esce dalla Direttiva Primaria e vara '{ship_name}'.", indent=0, min_verbosity=1)

            key_tier2 = (faction, "tier_1_20")
            if lc >= 1.20 and key_tier2 not in self.unlocked_secondary_fleets:
                self.unlocked_secondary_fleets.add(key_tier2)
                if orig_sid and orig_sid in self.stars:
                    speed = round(min(max_c, 0.18 + (lc * 0.10)), 3)
                    reach = round(speed * random.uniform(16.0, 22.0), 2)
                    ship_name = f"Flotta Esplorativa II di {p.assigned_name}"
                    is_earth = ("Terrestre" in faction)
                    
                    new_ship = AgentShip(
                        ship_name, faction, orig_sid, 
                        speed, reach, is_terrestrial=is_earth, disposition=p.disposition or "Collaborativa", civilization_level=lc
                    )
                    self.agents.append(new_ship)
                    time_str = f"T + {current_year:6.2f} yr"
                    self.logger.log_raw(f"  [{time_str}] 🚀 [AVANZAMENTO LC >= 1.20] {faction} sblocca e vara la SECONDA FLOTTA: '{ship_name}'!", indent=0, min_verbosity=1)

            key_tier3 = (faction, "tier_1_40")
            if lc >= 1.40 and key_tier3 not in self.unlocked_secondary_fleets:
                self.unlocked_secondary_fleets.add(key_tier3)
                if orig_sid and orig_sid in self.stars:
                    speed = round(min(max_c, 0.22 + (lc * 0.08)), 3)
                    reach = round(speed * random.uniform(18.0, 25.0), 2)
                    ship_name = f"Flotta Esplorativa III di {p.assigned_name}"
                    is_earth = ("Terrestre" in faction)
                    
                    new_ship = AgentShip(
                        ship_name, faction, orig_sid, 
                        speed, reach, is_terrestrial=is_earth, disposition=p.disposition or "Collaborativa", civilization_level=lc
                    )
                    self.agents.append(new_ship)
                    time_str = f"T + {current_year:6.2f} yr"
                    self.logger.log_raw(f"  [{time_str}] 🌌 [AVANZAMENTO LC >= 1.40] {faction} raggiunge l'Ingegneria Planetaria e vara la TERZA FLOTTA: '{ship_name}'!", indent=0, min_verbosity=1)

    def _determine_life_details(self, planet: Planet):
        if planet.is_explored_for_life:
            return

        if not planet.is_potentially_habitable():
            planet.has_life = False
            planet.is_explored_for_life = True
            planet.update_standard_name(self.latin_numerals)
            return

        life_cfg = self.interaction_cfg.get("life_generation", {})
        civ_cfg = self.interaction_cfg.get("civilization_generation", {})
        disp_cfg = self.interaction_cfg.get("disposition_generation", {})
        bio_cfg = self.interaction_cfg.get("biology", {})
        
        chance = life_cfg.get("base_chance_on_explored_planet", 0.05) + (planet.esi * 0.75)
            
        if random.random() < chance:
            planet.has_life = True
            planet.base_life_form = random.choices(bio_cfg.get("base_forms", ["Carbonio-Acqua"]), weights=bio_cfg.get("base_form_weights", [100]), k=1)[0]
            planet.assign_proper_name(self.existing_planet_names, self.naming_cfg)
            
            if random.random() < civ_cfg.get("chance_if_life_present", 0.15):
                planet.life_is_intelligent = True
                tiers = civ_cfg.get("tiers", [])
                if tiers:
                    chosen_tier = random.choices(tiers, weights=[t.get('weight', 1) for t in tiers], k=1)[0]
                    planet.civilization_level = round(random.uniform(chosen_tier['lc_min'], chosen_tier['lc_max']), 2)
                    prefix = random.choice(chosen_tier.get('naming_prefixes', ["Popoli di", "Regni di"]))
                    planet.civilization_name = f"{prefix} {planet.assigned_name}"
                    planet.social_structure = random.choice(chosen_tier.get('structures', ["Tradizionale"]))
                    planet.dominant_ethic = random.choice(chosen_tier.get('ethics', ["Neutrale"]))
                    planet.unity_level = chosen_tier.get('tier_name', "Standard")
                    
                disp_dist = disp_cfg.get("distribution", {"Collaborativa": 20, "Cauta": 25, "Diffidente": 30, "Ostile": 25})
                planet.disposition = random.choices(list(disp_dist.keys()), weights=list(disp_dist.values()), k=1)[0]
                planet.faction_name = planet.civilization_name

                if random.random() < self.filter_chance:
                    planet.has_life = False
                    planet.life_is_intelligent = False
                    planet.is_archeological_site = True
                    planet.cataclysm_cause = random.choice(self.cataclysms)
            else:
                planet.life_is_intelligent = False
                planet.civilization_level = round(random.uniform(0.01, 0.19), 2)
                planet.disposition = "Biosfera Primitiva"
        else:
            planet.has_life = False
            planet.update_standard_name(self.latin_numerals)

        planet.is_explored_for_life = True

    def _check_colonies_and_supply_lines(self):
        """Ottimizzato con Memoization BFS: evita di rieseguire la ricerca cammino su tutto il grafo."""
        current_year = self.logger.simulation_time_hours / (24 * 365.25)
        delta_years = max(0.01, current_year - self.last_colony_check_year)
        self.last_colony_check_year = current_year
        
        for star_obj, planet in list(self.active_colonies):
            capital_id = planet.homeworld_system_id or (self.sol_id if "Terrestre" in planet.faction_name else star_obj.original_id)
            
            cap_pos = self.stars[capital_id].position if capital_id in self.stars else (0.0, 0.0, 0.0)
            dist_to_cap = calculate_distance(cap_pos, star_obj.position)

            if star_obj.original_id == capital_id:
                is_supplied = True
            else:
                # Utilizzo della BFS con cache memorizzata
                path_to_capital = self._cached_find_bfs_path(star_obj.original_id, capital_id)
                is_supplied = len(path_to_capital) > 1

            event = planet.update_colony_lifecycle(
                current_year, delta_years, is_supplied, self.colony_disp_weights, 
                distance_from_capital=dist_to_cap, temporal_mode=self.temporal_mode,
                ai_diplomacy_cfg=self.ai_diplomacy_cfg
            )
            
            if event:
                evt_type, msg = event
                time_str = f"T + {current_year:6.2f} yr"
                self.logger.log_raw(f"  [{time_str}] [{evt_type}] {msg}", indent=0, min_verbosity=1)
                
                if evt_type in ["EMANCIPAZIONE_STADIO_4", "GUERRA_INDIPENDENZA_STADIO_4", "AUTOSUFFICIENZA_STADIO_3"] and not planet.has_spawned_autonomous_fleet:
                    planet.has_spawned_autonomous_fleet = True
                    
                    if evt_type == "GUERRA_INDIPENDENZA_STADIO_4":
                        self.diplomacy.set_relation(planet.mother_faction, planet.faction_name, DiplomaticRelation.GUERRA)
                    elif evt_type == "EMANCIPAZIONE_STADIO_4":
                        self.diplomacy.evaluate_initial_relation(planet.mother_faction, "Collaborativa", planet.faction_name, planet.colony_disposition)
                    
                    max_c = self.sim_params.get('max_exploration_speed_c', 0.35)
                    speed = round(min(max_c, 0.18 + ((planet.civilization_level or 1.0) * 0.10)), 3)
                    reach = round(speed * random.uniform(16.0, 20.0), 2)
                    
                    ship_name = f"Flotta di {planet.assigned_name}"
                    ship_faction = planet.faction_name if planet.is_independent else planet.mother_faction
                    
                    new_agent = AgentShip(
                        ship_name, ship_faction, star_obj.original_id, 
                        speed, reach, is_terrestrial=False, disposition=planet.colony_disposition, 
                        civilization_level=planet.civilization_level
                    )
                    self.agents.append(new_agent)
                    self.logger.log_raw(f"    |-- [CANTIERISTICA ATTIVA] '{ship_name}' intraprende la navigazione interstellare (V: {speed} c, Raggio: {reach:.1f} ly).", indent=0, min_verbosity=1)
                
                elif evt_type == "COLLASSO":
                    self.total_colonies_collapsed += 1
                    self.active_colonies.remove((star_obj, planet))

    def _process_inter_colony_geopolitics(self):
        """Ottimizzato con Spatial Hashing 3D per abbattere l'O(N^2) delle coppie di mondi sovrani."""
        current_year = self.logger.simulation_time_hours / (24 * 365.25)
        delta_t = max(0.1, current_year - self.last_geopolitics_check_year)
        self.last_geopolitics_check_year = current_year

        sovereign_worlds = [(s, p) for s in self.stars.values() for p in s.planets if p.colony_stage == Planet.STAGE_SOVEREIGN]

        if len(sovereign_worlds) >= 2:
            # Spatial Grid Hashing (Celle cubiche di 18 ly)
            CELL_SIZE = 18.0
            spatial_grid = defaultdict(list)
            for item in sovereign_worlds:
                s_pos = item[0].position
                cell_coord = (int(s_pos[0] // CELL_SIZE), int(s_pos[1] // CELL_SIZE), int(s_pos[2] // CELL_SIZE))
                spatial_grid[cell_coord].append(item)

            checked_pairs = set()
            neighbor_offsets = [
                (dx, dy, dz)
                for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
            ]

            for cell_coord, items_in_cell in spatial_grid.items():
                # Raccoglie i candidati nella cella corrente e nelle 26 celle adiacenti
                candidate_items = []
                for offset in neighbor_offsets:
                    adj_coord = (cell_coord[0] + offset[0], cell_coord[1] + offset[1], cell_coord[2] + offset[2])
                    if adj_coord in spatial_grid:
                        candidate_items.extend(spatial_grid[adj_coord])

                for i in range(len(items_in_cell)):
                    s1, p1 = items_in_cell[i]
                    for s2, p2 in candidate_items:
                        if s1.original_id >= s2.original_id:  # Evita duplicati e auto-confronti
                            continue
                        if p1.faction_name == p2.faction_name:
                            continue

                        pair_key = (s1.original_id, s2.original_id)
                        if pair_key in checked_pairs:
                            continue
                        checked_pairs.add(pair_key)

                        dist = calculate_distance(s1.position, s2.position)
                        if dist <= 18.0:
                            prof1 = p1.get_state_profile()
                            prof2 = p2.get_state_profile()
                            
                            self.diplomacy.evaluate_initial_relation_profiles(prof1, prof2)
                            rel = self.diplomacy.get_relation(p1.faction_name, p2.faction_name)

                            if rel in [DiplomaticRelation.COOPERAZIONE, DiplomaticRelation.NEUTRALE]:
                                route, feedback = self.diplomacy.negotiate_trade_route(s1.original_id, s2.original_id, p1, p2, dist, current_year)
                                if route:
                                    time_str = f"T + {current_year:6.2f} yr"
                                    self.logger.log_raw(f"  [{time_str}] [TRATTATO COMMERCIALE] Nuova rotta: {p1.faction_name} <-> {p2.faction_name} ({dist:.1f} ly).", indent=0, min_verbosity=1)
                                    self._apply_ai_feedback(p1, p2, feedback, current_year)

                            elif rel in [DiplomaticRelation.DIFFIDENZA, DiplomaticRelation.GUERRA]:
                                war_key = tuple(sorted([p1.faction_name, p2.faction_name]))
                                new_rel, feedback = self.diplomacy.resolve_border_friction(s1.original_id, s2.original_id, p1, p2, s1.assigned_name, current_year)
                                
                                if new_rel == DiplomaticRelation.GUERRA and war_key not in self.known_wars_logged:
                                    self.known_wars_logged.add(war_key)
                                    self.cumulative_combat_sectors[s1.assigned_name] += 1
                                    time_str = f"T + {current_year:6.2f} yr"
                                    self.logger.log_raw(f"  [{time_str}] [GUERRA DI CONFINE] Rottura diplomatica tra {p1.faction_name} e {p2.faction_name}!", indent=0, min_verbosity=1)
                                
                                self._apply_ai_feedback(p1, p2, feedback, current_year)

        tech_cfg = self.ai_diplomacy_cfg.get("technology_dynamics", {})
        poisson_cfg = self.ai_diplomacy_cfg.get("poisson_great_filter", {})

        for s, p in sovereign_worlds:
            if p.check_poisson_great_filter(delta_t, poisson_cfg) and not p.is_archeological_site and p.assigned_name != self.earth_planet_name:
                p.has_life = False
                p.life_is_intelligent = False
                p.is_archeological_site = True
                p.colony_stage = Planet.STAGE_ABANDONED
                p.is_colonized = False
                p.cataclysm_cause = random.choice(self.cataclysms)
                time_str = f"T + {current_year:6.2f} yr"
                self.logger.log_raw(f"  [{time_str}] 💀 [GRANDE FILTRO CONTINUO] {p.assigned_name} collassa: estinzione per '{p.cataclysm_cause}'!", indent=0, min_verbosity=1)
                continue

            active_routes = sum(1 for r in self.diplomacy.trade_routes if p.faction_name in (r.faction_a, r.faction_b))
            has_war = self.diplomacy.is_faction_at_war(p.faction_name)
            starbases_count = sum(1 for st in self.stars.values() if st.has_starbase and st.starbase_owner == p.faction_name)
            
            p.update_dynamic_technology(
                delta_t, active_routes, has_war, 
                controlled_starbases_count=starbases_count, tech_cfg=tech_cfg, 
                temporal_mode=self.temporal_mode
            )
            p.record_lc_snapshot(current_year)

        self._check_and_spawn_multiship_fleets()

    def _apply_ai_feedback(self, p1: Planet, p2: Planet, feedback: dict, current_year: float = 0.0):
        if not feedback: return
        if feedback.get("actor_disposition_shift"): p1.colony_disposition = feedback["actor_disposition_shift"]
        if feedback.get("target_disposition_shift"): p2.colony_disposition = feedback["target_disposition_shift"]
        if feedback.get("lc_bonus_actor") and p1.civilization_level:
            p1.civilization_level = round(p1.civilization_level + feedback["lc_bonus_actor"], 4)
            p1.record_lc_snapshot(current_year)
        if feedback.get("lc_bonus_target") and p2.civilization_level:
            p2.civilization_level = round(p2.civilization_level + feedback["lc_bonus_target"], 4)
            p2.record_lc_snapshot(current_year)
        if feedback.get("actor_lc_penalty") and p1.civilization_level:
            p1.civilization_level = round(max(0.1, p1.civilization_level - feedback["actor_lc_penalty"]), 4)
            p1.record_lc_snapshot(current_year)
        if feedback.get("target_lc_penalty") and p2.civilization_level:
            p2.civilization_level = round(max(0.1, p2.civilization_level - feedback["target_lc_penalty"]), 4)
            p2.record_lc_snapshot(current_year)

    def _check_deep_space_encounter(self, current_agent: AgentShip):
        current_system_id = current_agent.current_system_id
        current_year = self.logger.simulation_time_hours / (24 * 365.25)
        
        for other in self.agents:
            if other != current_agent and other.is_active and other.current_system_id == current_system_id and other.faction_name != current_agent.faction_name:
                encounter_pair = tuple(sorted([current_agent.ship_name, other.ship_name])) + (current_system_id,)
                if encounter_pair in self.resolved_encounters:
                    continue
                self.resolved_encounters.add(encounter_pair)
                
                if (current_agent.is_terrestrial or other.is_terrestrial) and not self.first_contact_occurred:
                    self.first_contact_occurred = True
                    self.first_contact_year = round(current_year, 2)
                    self.first_contact_type = "Incontro Flotta Deep-Space"
                    self.first_contact_civ_name = other.faction_name if current_agent.is_terrestrial else current_agent.faction_name
                    self.first_contact_disposition = other.disposition if current_agent.is_terrestrial else current_agent.disposition
                    
                    sol_pos = self.stars[self.sol_id].position
                    curr_pos = self.stars[current_system_id].position
                    self.first_contact_distance_ly = round(calculate_distance(sol_pos, curr_pos), 2)
                    self.systems_explored_before_contact = len(self.visited_system_ids)

                rel = self.diplomacy.get_relation(current_agent.faction_name, other.faction_name)
                sys_name = self.stars[current_system_id].assigned_name
                
                if rel in [DiplomaticRelation.COOPERAZIONE, DiplomaticRelation.FEDERAZIONE]:
                    current_agent.ship_fuel = min(1.0, current_agent.ship_fuel + 0.15)
                    other.ship_fuel = min(1.0, other.ship_fuel + 0.15)
                elif rel in [DiplomaticRelation.GUERRA, DiplomaticRelation.DIFFIDENZA]:
                    other.ship_health = max(0.1, other.ship_health - 0.15)
                    current_agent.ship_health = max(0.1, current_agent.ship_health - 0.10)
                    self.cumulative_combat_sectors[sys_name] += 1

    def _generate_unique_star_name(self):
        star_naming = self.naming_cfg.get("star_naming", {})
        syl1 = star_naming.get("syllables1", ["Astra", "Sol", "Vesper", "Orion", "Zen", "Eld", "Val", "Polaris", "Kael"])
        syl2 = star_naming.get("syllables2", ["Prime", "is", "on", "gard", "antis", "or", "Verara", "eon"])
        prefixes = star_naming.get("prefixes", ["Alpha", "Beta", "Nova", "Apex", "Polaris", "Sigma"])
        
        while True:
            name = f"{random.choice(prefixes)} {random.choice(syl1)}{random.choice(syl2)}" if random.random() < 0.5 else f"{random.choice(syl1).capitalize()}-{random.randint(100, 999)}"
            if name not in self.assigned_star_names:
                self.assigned_star_names.add(name)
                return name

    def _get_next_target_for_agent(self, agent: AgentShip):
        """Ottimizzato: sfrutta la cache di abitabilità pre-calcolata senza iterare i pianeti."""
        curr_id = agent.current_system_id
        if curr_id not in agent.explored_branches:
            agent.explored_branches[curr_id] = set()
            
        neighbors = self.galaxy_graph.get(curr_id, [])
        candidates = []
        curr_pos = self.stars[curr_id].position
        
        for nid in neighbors:
            if nid not in agent.explored_branches[curr_id] and nid in self.stars:
                n_sys = self.stars[nid]
                dist = calculate_distance(curr_pos, n_sys.position)
                if dist <= agent.max_reach:
                    is_near_edge = self._is_near_boundary(n_sys.position)
                    edge_penalty = 1.0 if (is_near_edge and self.watchdog_repulsion) else 0.0
                    has_hab = self._system_hab_cache.get(nid, False)
                    
                    candidates.append({
                        "id": nid, 
                        "dist": dist, 
                        "has_hab": has_hab,
                        "is_near_edge": is_near_edge,
                        "edge_penalty": edge_penalty
                    })
                    
        if not candidates:
            return None
            
        candidates.sort(key=lambda x: (x["edge_penalty"], not x["has_hab"], x["dist"]))
        chosen_id = candidates[0]["id"]
        agent.explored_branches[curr_id].add(chosen_id)
        return chosen_id

    def run(self):
        self.logger.log_header(f"Inizio Simulazione Galattica Multi-Agente V5.4 [{self.temporal_mode}]")
        self.logger.log_event("INIZIALIZZAZIONE", f"Attivate {len(self.agents)} flotte iniziali (Orizzonte: {self.max_duration_years:.0f} yr).", indent=0, min_verbosity=1)

        sol_pos = self.stars[self.sol_id].position

        active = True
        while active:
            active_agents = [ag for ag in self.agents if ag.is_active]
            if not active_agents:
                self.logger.log_event("FINE", "Tutte le flotte di esplorazione hanno completato le rotte.", indent=0, min_verbosity=1)
                break

            min_busy = min(ag.busy_until_hours for ag in active_agents)
            
            if min_busy > self.logger.simulation_time_hours:
                self.logger.simulation_time_hours = min_busy
                self._check_colonies_and_supply_lines()
                
                current_yr = self.logger.simulation_time_hours / (24 * 365.25)
                if (current_yr - self.last_geopolitics_check_year) >= self.geopolitics_interval_years:
                    self._process_inter_colony_geopolitics()

            current_sim_hours = self.logger.simulation_time_hours
            current_year = current_sim_hours / (24 * 365.25)

            if self.gnn_enabled and self.gnn.should_broadcast(current_year):
                if getattr(self.logger, 'verbosity', 1) > 0:
                    self.gnn.generate_broadcast(current_year, self.agents, self.logger)
                else:
                    self.gnn.next_broadcast_year += self.gnn.interval_years

            if current_sim_hours > (24 * 365.25 * self.max_duration_years):
                self.logger.log_event("TIMEOUT", f"Raggiunto il limite temporale ({self.max_duration_years:.0f} anni).", indent=0, min_verbosity=1)
                break

            for agent in active_agents:
                if not agent.is_available(current_sim_hours):
                    continue

                curr_sys = self.stars[agent.current_system_id]
                if not curr_sys.is_sol and curr_sys.assigned_name == curr_sys.original_id:
                    curr_sys.assigned_name = self._generate_unique_star_name()
                curr_sys.ensure_planets_star_name(self.latin_numerals)

                if agent.is_terrestrial:
                    dist_to_sol = calculate_distance(sol_pos, curr_sys.position)
                    if dist_to_sol > self.max_heliocentric_distance_reached_ly:
                        self.max_heliocentric_distance_reached_ly = round(dist_to_sol, 2)

                self._check_and_log_edge_watchdog(agent, curr_sys)
                self._check_deep_space_encounter(agent)
                self._execute_system_actions(curr_sys, agent)

                next_target_id = self._get_next_target_for_agent(agent)
                if next_target_id:
                    next_sys = self.stars[next_target_id]
                    if not next_sys.is_sol and next_sys.assigned_name == next_sys.original_id:
                        next_sys.assigned_name = self._generate_unique_star_name()
                    next_sys.ensure_planets_star_name(self.latin_numerals)
                        
                    dist = calculate_distance(curr_sys.position, next_sys.position)
                    travel_duration = ACTION_DURATIONS["travel_interstellar"](dist, agent.ship_speed)
                    
                    self.logger.log_travel(f"{agent.ship_name}", next_sys.assigned_name, next_sys.original_id, dist)
                    
                    agent.busy_until_hours = current_sim_hours + travel_duration
                    agent.update_status_after_travel(dist, self.fuel_base, self.fuel_per_ly, self.health_per_ly)
                    agent.current_system_id = next_target_id
                    agent.visited_path.append(next_target_id)
                    self.visited_system_ids.add(next_target_id)
                    next_sys.visited_by_ship = True
                else:
                    if len(agent.visited_path) > 1:
                        agent.visited_path.pop()
                        prev_id = agent.visited_path[-1]
                        prev_sys = self.stars[prev_id]
                        dist_ret = calculate_distance(curr_sys.position, prev_sys.position)
                        travel_duration = ACTION_DURATIONS["travel_interstellar"](dist_ret, agent.ship_speed)
                        
                        agent.busy_until_hours = current_sim_hours + travel_duration
                        agent.update_status_after_travel(dist_ret, self.fuel_base, self.fuel_per_ly, self.health_per_ly)
                        agent.current_system_id = prev_id
                    else:
                        agent.is_active = False
                        self.logger.log_event("RIENTRO", f"{agent.ship_name} ({agent.faction_name}) ha completato le rotte ed è tornata alla base.", indent=2, min_verbosity=1)

        final_yr = self.logger.simulation_time_hours / (24 * 365.25)
        self._process_inter_colony_geopolitics()
        
        for _, col_p in self.active_colonies:
            col_p.record_lc_snapshot(final_yr)
        sol_sys = self.stars.get(self.sol_id)
        if sol_sys:
            for p in sol_sys.planets:
                if p.original_name_from_gen == self.earth_planet_name:
                    p.record_lc_snapshot(final_yr)

        if getattr(self.logger, 'verbosity', 1) > 0:
            self.generate_mission_summary()
            self.generate_geopolitical_analysis()
        self.logger.close_log()

    def _execute_system_actions(self, system: StarSystem, agent: AgentShip):
        system.ensure_planets_star_name(self.latin_numerals)
        current_year = self.logger.simulation_time_hours / (24 * 365.25)
        founder_lc = getattr(agent, 'civilization_level', 1.0)
        
        if not system.fully_scanned:
            self.logger.log_event("SCANSIONE ORBITALE", f"{agent.ship_name} mappa {system.assigned_name} ({len(system.planets)} corpi celesti).", indent=2, duration_hours=ACTION_DURATIONS["scan_system"], min_verbosity=2)
            for idx, p in enumerate(system.planets):
                self._determine_life_details(p)
                p.update_standard_name(self.latin_numerals)
            system.fully_scanned = True

        if system.has_starbase and system.starbase_status == "Leale" and system.starbase_owner == agent.faction_name:
            agent.refuel_at_colony(self.colony_refuel, self.colony_repair)

        is_chokepoint_candidate = len(self.galaxy_graph.get(system.original_id, [])) >= 2
        if system.is_sterile_system() and is_chokepoint_candidate and not system.has_starbase:
            system.build_starbase(agent.faction_name, current_year)
            agent.refuel_at_colony(self.colony_refuel, self.colony_repair)
            time_str = self.logger.get_time_str()
            self.logger.log_raw(f"    [{time_str}] [STARBASE ORBITALE] {agent.faction_name} costruisce un presidio su {system.assigned_name}!", indent=0, min_verbosity=1)

        for p in system.planets:
            is_same_faction = (p.faction_name == agent.faction_name or p.mother_faction == agent.faction_name)
            
            if not is_same_faction and p.has_life and p.life_is_intelligent:
                contact_key = (system.original_id, p.assigned_name)
                
                if contact_key not in self.logged_planet_contacts:
                    self.logged_planet_contacts.add(contact_key)
                    time_str = self.logger.get_time_str()
                    
                    if p.civilization_level and p.civilization_level >= self.prime_directive_threshold and p.civilization_level < 1.0:
                        self.logger.log_raw(f"    [{time_str}] [🛡️ DIRETTIVA PRIMARIA] {agent.ship_name} rileva '{p.civilization_name}' (LC: {p.civilization_level:.2f}). Scatta il divieto di interferenza: monitoraggio stealth.", indent=0, min_verbosity=1)
                    else:
                        self.logger.log_raw(f"    [{time_str}] [PRIMO CONTATTO] {agent.ship_name} rileva civiltà intelligente da '{p.civilization_name}' (LC: {p.civilization_level}, ESI: {p.esi:.2f}, C_col: {p.c_col:.2f}).", indent=0, min_verbosity=1)
                    
                    if agent.is_terrestrial and not self.first_contact_occurred:
                        self.first_contact_occurred = True
                        self.first_contact_year = round(current_year, 2)
                        self.first_contact_type = "Contatto Planetario / Biofirme"
                        self.first_contact_civ_name = p.civilization_name
                        self.first_contact_disposition = p.disposition or "Neutrale"
                        sol_pos = self.stars[self.sol_id].position
                        self.first_contact_distance_ly = round(calculate_distance(sol_pos, system.position), 2)
                        self.systems_explored_before_contact = len(self.visited_system_ids)

            if p.is_explored_for_surface:
                continue
            p.is_explored_for_surface = True
            time_str = self.logger.get_time_str()
            
            if p.is_archeological_site and not p.relic_extracted:
                self.logger.log_raw(f"    [{time_str}] [ARCHEOLOGIA] {agent.ship_name} scava le rovine di '{p.civilization_name}' su {p.assigned_name}.", indent=0, min_verbosity=1)
                p.relic_extracted = True
                if agent.is_terrestrial:
                    self.archeological_sites_discovered += 1
                    sol_sys = self.stars.get(self.sol_id)
                    earth_p = next((pl for pl in sol_sys.planets if pl.original_name_from_gen == self.earth_planet_name), None) if sol_sys else None
                    if earth_p and earth_p.civilization_level:
                        tech_cfg = self.ai_diplomacy_cfg.get("technology_dynamics", {})
                        bonus = tech_cfg.get("archeology_breakthrough_bonus", 0.020)
                        earth_p.civilization_level = round(min(1.60, earth_p.civilization_level + bonus), 4)
                        earth_p.record_lc_snapshot(current_year)

                agent.ship_fuel = min(1.0, agent.ship_fuel + self.relic_fuel_bonus)
                agent.ship_health = min(1.0, agent.ship_health + self.relic_health_bonus)

            elif p.is_potentially_colonizable() and not p.is_colonized:
                if p.has_life and p.life_is_intelligent and (p.civilization_level or 0.0) >= self.prime_directive_threshold:
                    continue

                founder_origin_sys = getattr(agent, 'homeworld_system_id', agent.origin_system_id)
                p.establish_colony(current_year, agent.faction_name, founder_lc=founder_lc, homeworld_system_id=founder_origin_sys)
                
                self.total_colonies_founded += 1
                self.active_colonies.append((system, p))
                agent.colonized_systems.append(p.assigned_name)
                system.controlling_faction = agent.faction_name
                system.colonized_planets_ids.append(p.assigned_name)
                
                tag = "COLONIA TERRAFORMATA (FASE 2)" if p.colony_stage == Planet.STAGE_DEVELOPING else "COLONIZZAZIONE FASE 1"
                self.logger.log_raw(f"    [{time_str}] [{tag}] {agent.faction_name} insedia {p.assigned_name} (ESI: {p.esi:.2f}, C_col: {p.c_col:.2f}, Pop Iniziale: {p.population_millions:.2f}M)!", indent=0, min_verbosity=1)
                agent.refuel_at_colony(self.colony_refuel, self.colony_repair)
                break

    def generate_geopolitical_analysis(self):
        self.logger.log_header("Rapporto Geopolitico Galattico & Rotte Commerciali")
        self.logger.log_raw(f"ROTTE COMMERCIALI INTERSTELLARI ATTIVE ({len(self.diplomacy.trade_routes)}):", indent=0, min_verbosity=1)
        for tr in self.diplomacy.trade_routes:
            s1 = self.stars[tr.source_star_id].assigned_name
            s2 = self.stars[tr.target_star_id].assigned_name
            self.logger.log_raw(f"  💰 Rotta [{s1} <---> {s2}] | {tr.faction_a} <-> {tr.faction_b} (+15% Energia)", indent=2, min_verbosity=1)

    def generate_mission_summary(self):
        self.logger.log_header("Riepilogo Generale della Galassia Multi-Agente V5.4")
        self.logger.log_raw(f"Sistemi Stellari Totali Esplorati ({len(self.visited_system_ids)}):", indent=0, min_verbosity=1)
        self.logger.log_raw(f"Flotte Esplorative Totali Attivate nel Tempo: {len(self.agents)}", indent=0, min_verbosity=1)
        
        starbases = [s for s in self.stars.values() if s.has_starbase]
        self.logger.log_raw(f"Starbase Orbitali Presidiate ({len(starbases)}):", indent=0, min_verbosity=1)
        for sb in starbases:
            tag = "🛰️ LEALE" if sb.starbase_status == "Leale" else "🔥 OCCUPATA/MUTINATA"
            self.logger.log_raw(f"  - {sb.starbase_name} [{sb.controlling_faction}] | Status: {tag}", indent=2, min_verbosity=1)

        sovereigns = [p for s in self.stars.values() for p in s.planets if p.colony_stage == Planet.STAGE_SOVEREIGN]
        self.logger.log_raw(f"\nGoverni Coloniali Sovrani Emancipati ({len(sovereigns)}):", indent=0, min_verbosity=1)
        for p in sovereigns:
            self.logger.log_raw(f"  - 👑 {p.faction_name} su {p.assigned_name} [LC: {p.civilization_level:.2f} | C_col: {p.c_col:.2f} | Attitudine: {p.colony_disposition}]", indent=2, min_verbosity=1)