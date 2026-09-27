################################################################################
# FILE: core/universe.py
################################################################################

import random
import math

# Parametri Astrofisici per Classe Spettrale (Massa, Luminosità media in unità solari)
STAR_STELLAR_PROPERTIES = {
    "O": {"mass_m_sun": 25.0, "luminosity_l_sun": 60000.0, "hz_inner_au": 180.0, "hz_outer_au": 350.0},
    "B": {"mass_m_sun": 6.0,  "luminosity_l_sun": 800.0,   "hz_inner_au": 22.0,  "hz_outer_au": 42.0},
    "A": {"mass_m_sun": 2.0,  "luminosity_l_sun": 20.0,    "hz_inner_au": 3.5,   "hz_outer_au": 6.8},
    "F": {"mass_m_sun": 1.3,  "luminosity_l_sun": 3.5,     "hz_inner_au": 1.5,   "hz_outer_au": 2.8},
    "G": {"mass_m_sun": 1.0,  "luminosity_l_sun": 1.0,     "hz_inner_au": 0.85,  "hz_outer_au": 1.6},
    "K": {"mass_m_sun": 0.7,  "luminosity_l_sun": 0.25,    "hz_inner_au": 0.40,  "hz_outer_au": 0.85},
    "M": {"mass_m_sun": 0.3,  "luminosity_l_sun": 0.015,   "hz_inner_au": 0.10,  "hz_outer_au": 0.28}
}

class UniverseGenerator:
    def __init__(self, sim_config, naming_config):
        self.sim_cfg = sim_config
        self.naming_cfg = naming_config
        
        star_naming = naming_config.get("star_naming", {})
        self.prefixes = star_naming.get("prefixes", ["Alpha", "Proxima", "Sigma", "Apex"])
        self.suffixes = star_naming.get("generic_suffixes", ["System", "Prime", "Major"])
        self.syl1 = star_naming.get("syllables1", ["Sol", "Astra", "Vesper", "Kael"])
        self.syl2 = star_naming.get("syllables2", ["Prime", "is", "gard", "antis"])

    def _determine_albedo(self, planet_type, hydrosphere_pct, has_atmosphere):
        """Assegna l'Albedo di Bond A in base al profilo geofisico e atmosferico."""
        if not has_atmosphere:
            return round(random.uniform(0.08, 0.14), 3)  # Roccia nuda scura (tipo Luna/Mercurio)
        if planet_type == "Mondo Oceanico":
            return round(random.uniform(0.22, 0.32), 3)
        elif planet_type in ["Terrestre", "Super-Terra"]:
            return round(random.uniform(0.28, 0.36), 3)  # Terra = 0.306
        elif planet_type == "Gigante Ghiacciato" or hydrosphere_pct > 85.0:
            return round(random.uniform(0.55, 0.82), 3)  # Ghiacci perenni
        elif planet_type in ["Gigante Gassoso", "CO2 Densa"]:
            return round(random.uniform(0.65, 0.78), 3)  # Riflessione nubi dense
        else:
            return round(random.uniform(0.18, 0.30), 3)

    def generate_planetary_system(self, star_id, star_type):
        pg_params = self.sim_cfg['planetary_system_generation']
        num_planets = random.randint(pg_params['min_planets_per_system'], pg_params['max_planets_per_system'])
        planets = []
        
        st_props = STAR_STELLAR_PROPERTIES.get(star_type, STAR_STELLAR_PROPERTIES["G"])
        l_star = st_props["luminosity_l_sun"]
        hz_in = st_props["hz_inner_au"]
        hz_out = st_props["hz_outer_au"]

        p_types = list(pg_params['planet_type_distribution'].keys())
        p_weights = list(pg_params['planet_type_distribution'].values())

        # Distanze orbitali crescenti (Legge stile Titius-Bode)
        current_orbit_au = random.uniform(hz_in * 0.3, hz_in * 0.7)

        for i in range(num_planets):
            planet_name = f"{star_id}-Planet-{i+1}"
            planet_type = random.choices(p_types, weights=p_weights, k=1)[0]
            
            # Avanzamento orbitale
            orbital_dist_au = round(current_orbit_au, 3)
            current_orbit_au *= random.uniform(1.4, 2.0)

            is_in_hz = (hz_in <= orbital_dist_au <= hz_out)

            # 1. Raggio e Densità in base alla tipologia
            if planet_type == "Terrestre":
                radius_r = round(random.uniform(0.80, 1.25), 3)
                density_rho = round(random.uniform(0.90, 1.08) * (radius_r ** 0.15), 3)
                hydrosphere_pct = round(random.uniform(40.0, 85.0), 1) if is_in_hz else round(random.uniform(0.0, 15.0), 1)
                atmo = "Ossigeno-Azoto" if (is_in_hz and 0.85 <= radius_r <= 1.20) else "Inerte (Azoto-Argon)"
            elif planet_type == "Super-Terra":
                radius_r = round(random.uniform(1.26, 1.85), 3)
                density_rho = round(random.uniform(0.95, 1.18) * (radius_r ** 0.20), 3)
                hydrosphere_pct = round(random.uniform(20.0, 95.0), 1)
                atmo = "CO2 Densa" if random.random() < 0.40 else "Inerte (Azoto-Argon)"
            elif planet_type == "Mondo Oceanico":
                radius_r = round(random.uniform(0.90, 1.60), 3)
                density_rho = round(random.uniform(0.70, 0.88), 3) # Ricco di volatili/acqua
                hydrosphere_pct = round(random.uniform(85.0, 100.0), 1)
                atmo = "Ossigeno-Azoto" if is_in_hz else "Inerte (Azoto-Argon)"
            elif "Gigante" in planet_type:
                radius_r = round(random.uniform(3.5, 12.0), 3)
                density_rho = round(random.uniform(0.12, 0.35), 3) # Densità gassosa molto bassa
                hydrosphere_pct = 0.0
                atmo = "Tossica (Metano-Ammoniaca)"
            else: # Roccioso standard / Nano
                radius_r = round(random.uniform(0.35, 0.80), 3)
                density_rho = round(random.uniform(0.70, 0.98), 3)
                hydrosphere_pct = round(random.uniform(0.0, 5.0), 1)
                atmo = random.choice(["CO2 Densa", "Corrosiva (Acida/SO2)", "Assente (Vuoto)"])

            # 2. DIPENDENZA GRAVITAZIONALE RIGIDA: v_e = R * sqrt(rho)
            escape_vel_v = round(radius_r * math.sqrt(density_rho), 3)
            gravity_g = round(radius_r * density_rho, 3)

            # 3. ALBEDO E TERMODINAMICA RADIATIVA
            has_atmo = (atmo != "Assente (Vuoto)")
            albedo = self._determine_albedo(planet_type, hydrosphere_pct, has_atmo)
            
            # Temperatura di equilibrio di corpo nero: T_eq = 278.5 * ((L / d^2) * (1 - A))^0.25
            flux_ratio = l_star / (max(0.02, orbital_dist_au) ** 2)
            t_eq = 278.5 * (flux_ratio ** 0.25) * ((1.0 - albedo) ** 0.25)

            # Effetto serra delta_T in base alla composizione atmosferica
            if atmo == "Assente (Vuoto)" or escape_vel_v < 0.25:
                delta_t_greenhouse = 0.0
                atmo = "Assente (Vuoto)"
            elif atmo == "Ossigeno-Azoto":
                delta_t_greenhouse = random.uniform(28.0, 38.0) # Terra = +33K
            elif atmo == "CO2 Densa":
                delta_t_greenhouse = random.uniform(80.0, 250.0)
            elif atmo == "Corrosiva (Acida/SO2)":
                delta_t_greenhouse = random.uniform(300.0, 500.0) # Tipo Venere (+500K)
            else:
                delta_t_greenhouse = random.uniform(5.0, 25.0)

            temp_surface_k = round(max(20.0, t_eq + delta_t_greenhouse), 1)

            # Condizione oggettiva di abitabilità
            habitable = (is_in_hz and atmo == "Ossigeno-Azoto" and 260.0 <= temp_surface_k <= 315.0 and 0.70 <= gravity_g <= 1.40)

            # --- HOOK FATTORE D (DOE): Penalità Flare / Sterilizzazione Nane Rosse M (Guarded PRNG) ---
            m_flare_penalty = self.sim_cfg.get("m_dwarf_flare_penalty", 0.0)
            if m_flare_penalty > 0.0 and habitable and star_type == "M":
                if random.random() < m_flare_penalty:
                    habitable = False
                    atmo = "Sterilizzata da Radiazione/Flare UV"

            planets.append({
                "name": planet_name,
                "type": planet_type,
                "habitable": habitable,
                "orbital_dist_au": orbital_dist_au,
                "radius_r": radius_r,
                "density_rho": density_rho,
                "escape_vel_v": escape_vel_v,
                "gravity_g": gravity_g,
                "temp_surface_k": temp_surface_k,
                "albedo": albedo,
                "hydrosphere_pct": hydrosphere_pct,
                "atmosphere_type": atmo
            })
        return planets

    def generate_star_field(self):
        volume_side = self.sim_cfg['simulation_volume_side_ly']
        avg_dist = self.sim_cfg['average_star_distance_ly']
        num_stars_estimate = int((volume_side / avg_dist)**3)
        num_stars = max(1, min(num_stars_estimate, 15000))
        
        stars = []
        star_types = list(self.sim_cfg['star_type_distribution'].keys())
        star_weights = list(self.sim_cfg['star_type_distribution'].values())
        
        sol_id = self.sim_cfg['earth_star_name']
        
        # Benchmark Reale del Sistema Solare (Dati Astrofisici Standard)
        sol_planets = [
            {"name": "Mercurio", "type": "Roccioso", "habitable": False, "orbital_dist_au": 0.387, "radius_r": 0.383, "density_rho": 0.984, "escape_vel_v": 0.384, "gravity_g": 0.38, "temp_surface_k": 440.0, "albedo": 0.088, "hydrosphere_pct": 0.0, "atmosphere_type": "Assente (Vuoto)"},
            {"name": "Venere", "type": "Roccioso", "habitable": False, "orbital_dist_au": 0.723, "radius_r": 0.949, "density_rho": 0.951, "escape_vel_v": 0.926, "gravity_g": 0.90, "temp_surface_k": 737.0, "albedo": 0.770, "hydrosphere_pct": 0.0, "atmosphere_type": "Corrosiva (Acida/SO2)"},
            {"name": self.sim_cfg['earth_planet_name'], "type": "Terrestre", "habitable": True, "orbital_dist_au": 1.000, "radius_r": 1.000, "density_rho": 1.000, "escape_vel_v": 1.000, "gravity_g": 1.00, "temp_surface_k": 288.0, "albedo": 0.306, "hydrosphere_pct": 71.0, "atmosphere_type": "Ossigeno-Azoto"},
            {"name": "Marte", "type": "Roccioso", "habitable": False, "orbital_dist_au": 1.524, "radius_r": 0.532, "density_rho": 0.713, "escape_vel_v": 0.450, "gravity_g": 0.38, "temp_surface_k": 210.0, "albedo": 0.250, "hydrosphere_pct": 2.0, "atmosphere_type": "CO2 Densa"},
            {"name": "Giove", "type": "Gigante Gassoso", "habitable": False, "orbital_dist_au": 5.204, "radius_r": 11.21, "density_rho": 0.241, "escape_vel_v": 5.32, "gravity_g": 2.53, "temp_surface_k": 165.0, "albedo": 0.343, "hydrosphere_pct": 0.0, "atmosphere_type": "Tossica (Metano-Ammoniaca)"},
            {"name": "Saturno", "type": "Gigante Gassoso", "habitable": False, "orbital_dist_au": 9.582, "radius_r": 9.45, "density_rho": 0.125, "escape_vel_v": 3.17, "gravity_g": 1.06, "temp_surface_k": 134.0, "albedo": 0.342, "hydrosphere_pct": 0.0, "atmosphere_type": "Tossica (Metano-Ammoniaca)"},
            {"name": "Urano", "type": "Gigante Ghiacciato", "habitable": False, "orbital_dist_au": 19.20, "radius_r": 4.01, "density_rho": 0.230, "escape_vel_v": 1.90, "gravity_g": 0.89, "temp_surface_k": 76.0, "albedo": 0.300, "hydrosphere_pct": 0.0, "atmosphere_type": "Tossica (Metano-Ammoniaca)"},
            {"name": "Nettuno", "type": "Gigante Ghiacciato", "habitable": False, "orbital_dist_au": 30.05, "radius_r": 3.88, "density_rho": 0.297, "escape_vel_v": 2.10, "gravity_g": 1.14, "temp_surface_k": 72.0, "albedo": 0.290, "hydrosphere_pct": 0.0, "atmosphere_type": "Tossica (Metano-Ammoniaca)"}
        ]
        
        stars.append({"id": sol_id, "position": (0.0, 0.0, 0.0), "type": "G", "planets": sol_planets, "is_sol": True})
        
        half_side = volume_side / 2.0
        for i in range(num_stars - 1):
            star_id = f"Star-{i+1}"
            pos = (random.uniform(-half_side, half_side), random.uniform(-half_side, half_side), random.uniform(-half_side, half_side))
            s_type = random.choices(star_types, weights=star_weights, k=1)[0]
            planets = self.generate_planetary_system(star_id, s_type)
            stars.append({"id": star_id, "position": pos, "type": s_type, "planets": planets, "is_sol": False})
            
        return stars