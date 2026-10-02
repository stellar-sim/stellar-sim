################################################################################
# FILE: core/civilization.py
# VERSIONE V5.4.1 - TRUE DETERMINISTIC ONE-SEED REPLAY (PRNG STREAM ISOLATION)
################################################################################

import random
import math
import hashlib

def determine_civilization_mobility(sim_config):
    """
    Determina la mobilità della civiltà lungo l'intero spettro cosmico del libro:
    v_max in [0.15 c, 0.60 c] e endurance in [15, 24] anni.
    """
    # Range cosmico del Master DOE (Capitoli 7 e 8)
    ship_speed_c = round(random.uniform(0.15, 0.60), 3)
    ship_speed_ly_per_year = ship_speed_c

    hop_endurance = random.uniform(15.0, 24.0)
    max_reach_ly = round(ship_speed_ly_per_year * hop_endurance, 2)
    abs_max_trip = 150.0

    return {
        "ship_speed_c": ship_speed_c,
        "ship_speed_ly_per_year": ship_speed_ly_per_year,
        "hop_endurance_years": hop_endurance,
        "max_reach_ly": max_reach_ly,
        "abs_max_trip_years": abs_max_trip
    }

def calculate_esi(radius_r, density_rho, escape_vel_v, temp_surface_k):
    """
    Calcola l'Earth Similarity Index (ESI) canonico normalizzato (Schulze-Makuch et al. 2011).
    Pesi corretti normalizzati sulla somma totale (0.57 + 1.07 + 0.70 + 5.58 = 7.92).
    """
    params = [
        (radius_r, 1.0, 0.57),
        (density_rho, 1.0, 1.07),
        (escape_vel_v, 1.0, 0.70),
        (temp_surface_k, 288.0, 5.58)
    ]
    
    w_sum = sum(w for _, _, w in params)  # 7.92
    esi = 1.0
    
    for val, val_0, weight in params:
        if val <= 0.0 or val_0 <= 0.0:
            return 0.0
        term = 1.0 - abs((val - val_0) / (val + val_0))
        if term <= 0.0:
            return 0.0
        esi *= (term ** (weight / w_sum))
        
    return round(float(min(1.0, max(0.0, esi))), 3)

def _deterministic_c_col(planet_name, system_id):
    """
    Genera C_col in [0, 1] in modo deterministico e isolato tramite hash.
    NON consuma chiamate dal generatore random globale, preservando la sincronizzazione del PRNG.
    """
    key = f"{system_id}_{planet_name}".encode('utf-8')
    h = int(hashlib.md5(key).hexdigest(), 16)
    return round((h % 1000) / 1000.0, 3)

class Planet:
    STAGE_ABANDONED = -1
    STAGE_UNINHABITED = 0
    STAGE_OUTPOST = 1
    STAGE_DEVELOPING = 2
    STAGE_SELF_SUFFICIENT = 3
    STAGE_SOVEREIGN = 4

    STAGE_NAMES = {
        -1: "Mondo Abbandonato",
        0: "Disabitato",
        1: "Avamposto Scientifico",
        2: "Colonia in Sviluppo",
        3: "Colonia Autosufficiente",
        4: "Governo Sovrano Maturo"
    }

    def __init__(self, planet_data, star_assigned_name, orbital_index, system_id=None):
        self.original_name_from_gen = planet_data['name'] 
        self.type = planet_data['type']
        self.star_name = star_assigned_name 
        self.star_system_id = system_id
        self.orbital_index = orbital_index
        self.assigned_name = self.original_name_from_gen 
        self.has_custom_proper_name = False
        
        self.orbital_dist_au = planet_data.get('orbital_dist_au', 1.0)
        self.radius_r = planet_data.get('radius_r', 1.0)
        self.density_rho = planet_data.get('density_rho', 1.0)
        self.escape_vel_v = planet_data.get('escape_vel_v', round(self.radius_r * math.sqrt(self.density_rho), 3))
        self.gravity_g = planet_data.get('gravity_g', round(self.radius_r * self.density_rho, 3))
        self.temp_surface_k = planet_data.get('temp_surface_k', 288.0)
        self.albedo = planet_data.get('albedo', 0.30)
        self.hydrosphere_pct = planet_data.get('hydrosphere_pct', 70.0)
        self.atmosphere_type = planet_data.get('atmosphere_type', "Inerte (Azoto-Argon)")
        
        # 1. ESI Geofisico Puro
        self.esi = calculate_esi(self.radius_r, self.density_rho, self.escape_vel_v, self.temp_surface_k)
        
        # 2. Indice di Colonizzabilità Superficiale deterministico (Zero consumo PRNG globale)
        self.c_col = _deterministic_c_col(self.original_name_from_gen, system_id or "Sys")

        self.is_explored_for_life = False
        self.is_explored_for_surface = False
        self.has_life = None
        self.life_is_intelligent = None
        self.civilization_level = None
        self.disposition = None        
        self.social_structure = None
        self.dominant_ethic = None     
        self.unity_level = None
        self.base_life_form = None     
        self.civilization_name = None 
        
        self.is_archeological_site = False
        self.cataclysm_cause = None
        self.relic_extracted = False
        
        # Parametri Colonia V5.4.1
        self.is_colonized = False
        self.colony_stage = self.STAGE_UNINHABITED
        self.colony_founded_year = None
        self.last_stage_transition_year = None
        self.years_unsupplied = 0.0
        self.population_millions = 0.0
        self.is_independent = False
        self.colony_disposition = "Leale a Sol"
        self.faction_name = "Colonia Terrestre"
        self.mother_faction = None
        self.homeworld_system_id = None
        self.mother_lc_at_foundation = 1.0
        self.has_spawned_autonomous_fleet = False

        self.colonial_resentment = 0.0
        self.is_exploited = True
        self.has_declared_independence_war = False

        self.lc_history = []
        self.emancipation_year = None
        self.emancipation_lc = None

    @property
    def colony_stage_name(self):
        return self.STAGE_NAMES.get(self.colony_stage, "Sconosciuto")

    def is_potentially_habitable(self): 
        return (self.esi >= 0.70 and self.atmosphere_type == "Ossigeno-Azoto" and 260.0 <= self.temp_surface_k <= 320.0)

    def is_potentially_colonizable(self):
        if not self.is_potentially_habitable():
            return False
        if self.has_life and self.life_is_intelligent and not self.is_archeological_site:
            return False
        return self.colony_stage in [self.STAGE_UNINHABITED, self.STAGE_ABANDONED]

    def record_lc_snapshot(self, current_year):
        if self.civilization_level is not None:
            t = round(float(current_year), 2)
            lc = round(float(self.civilization_level), 4)
            if not self.lc_history or self.lc_history[-1][0] != t or self.lc_history[-1][1] != lc:
                self.lc_history.append((t, lc))

    def establish_colony(self, current_year, founder_faction, founder_lc=1.0, homeworld_system_id=None):
        self.is_colonized = True
        self.colony_founded_year = current_year
        self.last_stage_transition_year = current_year
        self.years_unsupplied = 0.0
        self.is_independent = False
        self.mother_faction = founder_faction
        self.homeworld_system_id = homeworld_system_id
        self.mother_lc_at_foundation = founder_lc
        
        self.civilization_level = round(max(0.20, founder_lc * random.uniform(0.70, 0.85)), 3)
        self.colony_disposition = "Leale alla Madrepatria"
        
        if founder_lc >= 1.40:
            self.colony_stage = self.STAGE_DEVELOPING
            self.population_millions = round(random.uniform(0.15, 0.35), 3)
            self.faction_name = f"Colonia Avanzata di {founder_faction}"
        else:
            self.colony_stage = self.STAGE_OUTPOST
            self.population_millions = round(random.uniform(0.01, 0.05), 3)
            self.faction_name = f"Avamposto di {founder_faction}"

        self.record_lc_snapshot(current_year)

    def update_colony_lifecycle(self, current_year, delta_years, is_connected_to_homeworld, disp_weights_dict, distance_from_capital=0.0, temporal_mode="TACTICAL_ACCELERATED", ai_diplomacy_cfg=None):
        if not self.is_colonized or self.colony_stage == self.STAGE_ABANDONED:
            return None

        is_deep_time = (temporal_mode == "DEEP_TIME_ASTROPHYSICAL")
        time_mult = 3.0 if is_deep_time else 1.0
        unsupplied_limit = 200.0 if is_deep_time else 50.0

        years_in_stage = current_year - self.last_stage_transition_year

        # 1. Mercantilismo e risentimento
        merc_cfg = (ai_diplomacy_cfg or {}).get("colonial_mercantilism", {})
        if merc_cfg.get("enabled", True) and not self.is_independent and self.colony_stage in [self.STAGE_OUTPOST, self.STAGE_DEVELOPING, self.STAGE_SELF_SUFFICIENT]:
            expl_rate = merc_cfg.get("exploitation_rate", 0.10)
            res_rate = merc_cfg.get("resentment_accumulation_rate", 0.85)
            self.colonial_resentment += delta_years * res_rate * (1.5 - self.esi)
            drain_penalty = expl_rate * 0.001 * delta_years
            self.civilization_level = max(0.15, (self.civilization_level or 0.5) - drain_penalty)

        # 2. Rifornimenti e collasso
        if self.colony_stage in [self.STAGE_OUTPOST, self.STAGE_DEVELOPING]:
            if not is_connected_to_homeworld:
                self.years_unsupplied += delta_years
                if self.years_unsupplied >= unsupplied_limit:
                    self.colony_stage = self.STAGE_ABANDONED
                    self.is_colonized = False
                    self.population_millions = 0.0
                    self.faction_name = f"Rovine di {self.assigned_name}"
                    return ("COLLASSO", f"La colonia su {self.assigned_name} è collassata per isolamento logistico ({self.years_unsupplied:.1f} anni senza convogli)!")
            else:
                self.years_unsupplied = max(0.0, self.years_unsupplied - delta_years * 0.5)

        # 3. Stadio 1 -> Stadio 2
        t1_thresh = (45.0 * (1.6 - self.esi)) * time_mult
        if self.colony_stage == self.STAGE_OUTPOST and years_in_stage >= t1_thresh:
            self.colony_stage = self.STAGE_DEVELOPING
            self.last_stage_transition_year = current_year
            self.population_millions = round(self.population_millions * random.uniform(5.0, 10.0), 2)
            self.civilization_level = round(min(1.40, (self.civilization_level or 0.8) + 0.05), 3)
            self.record_lc_snapshot(current_year)
            return ("CRESCITA_STADIO_2", f"L'avamposto su {self.assigned_name} completa le biocupole urbane (Pop: {self.population_millions:.2f}M).")

        # 4. Stadio 2 -> Stadio 3
        t2_thresh = (85.0 * (1.6 - self.esi)) * time_mult
        if self.colony_stage == self.STAGE_DEVELOPING and years_in_stage >= t2_thresh:
            self.colony_stage = self.STAGE_SELF_SUFFICIENT
            self.last_stage_transition_year = current_year
            self.population_millions = round(self.population_millions * random.uniform(5.0, 12.0) * self.esi, 2)
            self.civilization_level = round(min(1.50, (self.civilization_level or 0.9) + 0.10), 3)
            self.record_lc_snapshot(current_year)
            return ("AUTOSUFFICIENZA_STADIO_3", f"La colonia su {self.assigned_name} raggiunge l'autosufficienza industriale ed energetica: SBLOCCO CANTIERISTICA INTERSTELLARE (Pop: {self.population_millions:.2f}M)!")

        # 5. Stadio 3 -> Stadio 4 (Emancipazione con Leapfrogging)
        t3_thresh = (110.0 * (1.5 - (self.esi * 0.5))) * time_mult
        if self.colony_stage == self.STAGE_SELF_SUFFICIENT and years_in_stage >= t3_thresh:
            has_enough_mass = (self.population_millions >= 1.2 and self.esi >= 0.70)
            if not has_enough_mass:
                self.last_stage_transition_year += (20.0 * time_mult)
                return None

            self.colony_stage = self.STAGE_SOVEREIGN
            self.is_independent = True
            self.last_stage_transition_year = current_year
            self.population_millions = round(self.population_millions * random.uniform(2.0, 4.0), 2)
            
            beta_val = (ai_diplomacy_cfg or {}).get("civilization_parameters", {}).get("beta_esi_leapfrogging", 0.50)
            divergence_factor = (self.esi - 0.70) * beta_val * self.c_col + random.uniform(-0.05, 0.20)
            self.civilization_level = round(max(0.60, min(1.60, self.mother_lc_at_foundation * (1.0 + divergence_factor))), 3)

            self.emancipation_year = round(float(current_year), 2)
            self.emancipation_lc = self.civilization_level
            self.record_lc_snapshot(current_year)

            overstretch_mod = min(3.0, (distance_from_capital / 10.0) ** 1.35) if distance_from_capital > 0 else 1.0
            res_thresh = merc_cfg.get("independence_war_resentment_threshold", 35.0)
            
            if self.colonial_resentment >= res_thresh:
                self.colony_disposition = "Ostile"
                self.has_declared_independence_war = True
                self.faction_name = f"Governo Sovrano Ribelle di {self.assigned_name}"
                return ("GUERRA_INDIPENDENZA_STADIO_4", f"⚡ RIVOLTA DI FRONTIERA: {self.assigned_name} dichiara la GUERRA D'INDIPENDENZA contro {self.mother_faction} (Risentimento: {self.colonial_resentment:.1f}, LC: {self.civilization_level:.2f})!")

            weights_copy = dict(disp_weights_dict)
            if "Ostile" in weights_copy:
                weights_copy["Ostile"] = int(weights_copy["Ostile"] * overstretch_mod)
            if "Diffidente" in weights_copy:
                weights_copy["Diffidente"] = int(weights_copy["Diffidente"] * (1.0 + (overstretch_mod - 1.0) * 0.5))

            dispositions = list(weights_copy.keys())
            weights = list(weights_copy.values())
            self.colony_disposition = random.choices(dispositions, weights=weights, k=1)[0]
            self.faction_name = f"Governo Sovrano di {self.assigned_name}"
            
            return ("EMANCIPAZIONE_STADIO_4", f"{self.assigned_name} proclama la sovranità pacifica: nasce il '{self.faction_name}' [LC: {self.civilization_level:.2f} | C_col: {self.c_col:.2f} | Assetto: {self.colony_disposition.upper()}].")

        return None

    def update_dynamic_technology(self, delta_years, active_trade_routes_count, has_war, controlled_starbases_count=0, tech_cfg=None, temporal_mode="TACTICAL_ACCELERATED"):
        if not self.civilization_level:
            return
        
        cfg = tech_cfg or {}
        time_scaling = 0.15 if temporal_mode == "DEEP_TIME_ASTROPHYSICAL" else 1.0
        
        p_growth = cfg.get("base_passive_annual_growth", 0.00003) * time_scaling
        sb_bonus = cfg.get("starbase_bonus_annual", 0.00008) * time_scaling
        tr_bonus = cfg.get("trade_route_lc_bonus_annual", 0.00035) * time_scaling
        war_pen = cfg.get("war_damage_lc_penalty", 0.015)

        diminishing_factor = max(0.08, 1.80 - self.civilization_level)
        growth = (p_growth + (controlled_starbases_count * sb_bonus) + (active_trade_routes_count * tr_bonus)) * delta_years * diminishing_factor
        
        if has_war:
            growth -= (war_pen * 0.10 * delta_years * time_scaling)
            
        new_lc = min(1.60, max(0.10, self.civilization_level + growth))
        self.civilization_level = round(new_lc, 4)

    def check_poisson_great_filter(self, delta_years, filter_cfg=None):
        if not self.has_life or not self.life_is_intelligent or self.is_archeological_site:
            return False
            
        cfg = filter_cfg or {}
        if not cfg.get("enabled", True):
            return False

        base_hazard = cfg.get("base_annual_hazard_rate", 0.00018)
        crit_range = cfg.get("critical_transition_lc_range", [0.75, 1.05])
        mult = cfg.get("transition_risk_multiplier", 3.2)
        
        lc = self.civilization_level or 0.5
        effective_hazard = base_hazard * mult if (crit_range[0] <= lc <= crit_range[1]) else base_hazard
        
        prob_extinction = 1.0 - math.exp(-effective_hazard * delta_years)
        return random.random() < prob_extinction

    def get_state_profile(self):
        return {
            "planet_name": self.assigned_name,
            "faction_name": self.faction_name,
            "mother_faction": self.mother_faction,
            "lc": self.civilization_level or 1.0,
            "disposition": self.colony_disposition if self.is_independent else (self.disposition or "Neutrale"),
            "population_millions": self.population_millions,
            "esi": self.esi,
            "c_col": self.c_col,
            "colony_stage": self.colony_stage
        }

    def assign_proper_name(self, existing_names_set, naming_cfg):
        p_cfg = naming_cfg.get("planet_naming", {})
        prefixes = p_cfg.get("prefixes", ["New ", "Neo-", "Astra-", "Port "])
        roots = p_cfg.get("phonetic_roots", ["Aethel", "Vesper", "Kryon", "Valoria", "Caelum", "Elysium", "Chronos", "Drakon", "Sylvan", "Genesis"])
        infixes = p_cfg.get("infixes", ["an", "or", "el", "is", "ar", "en", "on"])
        suffixes = p_cfg.get("suffixes", ["gard", "ia", "on", "is", "dor", "vallis", "ium", "antis", " Prime", " Major"])
        legendary = p_cfg.get("historic_legendary_worlds", ["Coruscant", "Corellia", "Naboo", "Alderaan"])

        attempts = 0
        while attempts < 100:
            roll = random.random()
            if legendary and roll < 0.15: candidate = random.choice(legendary)
            elif roll < 0.45: candidate = f"{random.choice(roots)}{random.choice(suffixes)}"
            elif roll < 0.80: candidate = f"{random.choice(roots)}{random.choice(infixes)}{random.choice(suffixes).strip()}"
            else: candidate = f"{random.choice(prefixes)}{random.choice(roots)}{random.choice(suffixes)}"
                
            if candidate not in existing_names_set:
                self.assigned_name = candidate
                self.has_custom_proper_name = True
                existing_names_set.add(candidate)
                return candidate
            attempts += 1

        candidate = f"{random.choice(roots)}-{random.choice(suffixes).strip()}-{random.randint(10, 99)}"
        self.assigned_name = candidate
        self.has_custom_proper_name = True
        existing_names_set.add(candidate)
        return candidate

    def update_standard_name(self, latin_numerals):
        if not self.has_custom_proper_name:
            numeral_index = self.orbital_index - 1
            roman = latin_numerals[numeral_index] if numeral_index < len(latin_numerals) else str(self.orbital_index)
            self.assigned_name = f"{self.star_name} {roman}"

class StarSystem:
    def __init__(self, star_data):
        self.original_id = star_data['id']
        self.type = star_data['type']
        self.position = tuple(star_data['position'])
        self.planets_data = star_data['planets'] 
        self.is_sol = star_data.get('is_sol', False)
        self.assigned_name = self.original_id 
        self.visited_by_ship = False
        self.fully_scanned = False
        self.colonized_planets_ids = []
        self.resources_extracted = False
        self.controlling_faction = None
        
        self.has_starbase = False
        self.starbase_owner = None
        self.starbase_founded_year = None
        self.starbase_status = "Leale"
        self.starbase_name = None
        
        self.planets = [
            Planet(p, self.assigned_name, idx + 1, system_id=self.original_id) 
            for idx, p in enumerate(self.planets_data)
        ]

    def ensure_planets_star_name(self, latin_numerals=None):
        for p in self.planets:
            p.star_name = self.assigned_name
            p.star_system_id = self.original_id
            if latin_numerals:
                p.update_standard_name(latin_numerals)

    def has_habitable_candidate(self):
        return any(p.is_potentially_habitable() for p in self.planets)

    def is_sterile_system(self):
        return not self.has_habitable_candidate()

    def build_starbase(self, owner_faction, current_year, starbase_name=None):
        self.has_starbase = True
        self.starbase_owner = owner_faction
        self.starbase_founded_year = current_year
        self.starbase_status = "Leale"
        self.controlling_faction = owner_faction
        self.starbase_name = starbase_name or f"Starbase {self.assigned_name}"

    def flip_starbase_control(self, new_owner, new_status="Occupata"):
        old_owner = self.starbase_owner
        self.starbase_owner = new_owner
        self.starbase_status = new_status
        self.controlling_faction = new_owner
        return old_owner, new_owner