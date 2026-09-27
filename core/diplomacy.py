################################################################################
# FILE: core/diplomacy.py
################################################################################

import random
from abc import ABC, abstractmethod

class DiplomaticRelation:
    GUERRA = "Guerra Aperta"
    EMBARGO = "Embargo & Blocco"
    DIFFIDENZA = "Diffidenza Armata"
    NEUTRALE = "Neutrale"
    COOPERAZIONE = "Trattato di Cooperazione & Commercio"
    FEDERAZIONE = "Patto Federale & Difesa Congiunta"

class TradeRoute:
    def __init__(self, source_star_id, target_star_id, faction_a, faction_b, distance_ly, established_year):
        self.source_star_id = source_star_id
        self.target_star_id = target_star_id
        self.faction_a = str(faction_a)
        self.faction_b = str(faction_b)
        self.distance_ly = distance_ly
        self.established_year = established_year
        self.energy_yield_multiplier = 0.15
        self.is_active = True

class Federation:
    def __init__(self, name, member_factions, founded_year):
        self.name = name
        self.members = set(member_factions)
        self.founded_year = founded_year
        self.defensive_pact = True
        self.shared_sensor_grid = True


# ==============================================================================
# INTERFACCIA ASTRATTA AGENTE AI DIPLOMATICO
# ==============================================================================
class BaseAIDiplomacyAgent(ABC):
    @abstractmethod
    def decide_trade_proposal(self, actor_profile: dict, target_profile: dict, distance_ly: float) -> tuple[bool, dict]:
        pass

    @abstractmethod
    def decide_border_conflict(self, actor_profile: dict, opponent_profile: dict, context: dict) -> tuple[str, dict]:
        pass

    @abstractmethod
    def decide_federation_offer(self, actor_profile: dict, other_profiles: list, context: dict) -> tuple[bool, dict]:
        pass


# ==============================================================================
# MOTORE DECISIONALE EURISTICO (In uso fino all'innesto dell'Agente AI)
# ==============================================================================
class HeuristicAIDiplomacyAgent(BaseAIDiplomacyAgent):
    def __init__(self, ai_cfg: dict):
        self.cfg = ai_cfg.get("heuristic_weights", {}) if ai_cfg else {}
        self.drift_cfg = ai_cfg.get("disposition_drift", {}) if ai_cfg else {}
        self.tech_cfg = ai_cfg.get("technology_dynamics", {}) if ai_cfg else {}

    def decide_trade_proposal(self, actor_profile: dict, target_profile: dict, distance_ly: float) -> tuple[bool, dict]:
        base_p = self.cfg.get("trade_base_acceptance_chance", 0.45)
        disp_mods = self.cfg.get("disposition_trade_modifiers", {})

        mod_a = disp_mods.get(actor_profile.get("disposition", "Neutrale"), 0.0)
        mod_b = disp_mods.get(target_profile.get("disposition", "Neutrale"), 0.0)
        dist_penalty = min(0.25, (distance_ly / 30.0) * 0.15)

        # Bonus Fratellanza Coloniale
        sister_bonus = 0.35 if (actor_profile.get("mother_faction") and actor_profile.get("mother_faction") == target_profile.get("mother_faction")) else 0.0

        total_prob = max(0.05, min(0.95, base_p + mod_a + mod_b + sister_bonus - dist_penalty))
        accepted = random.random() < total_prob

        feedback = {
            "actor_disposition_shift": "Collaborativa" if accepted and random.random() < self.drift_cfg.get("trade_cooperation_softening_chance", 0.12) else None,
            "target_disposition_shift": "Collaborativa" if accepted and random.random() < self.drift_cfg.get("trade_cooperation_softening_chance", 0.12) else None,
            "lc_bonus_actor": self.tech_cfg.get("trade_route_lc_bonus_annual", 0.0004) if accepted else 0.0,
            "lc_bonus_target": self.tech_cfg.get("trade_route_lc_bonus_annual", 0.0004) if accepted else 0.0
        }
        return accepted, feedback

    def decide_border_conflict(self, actor_profile: dict, opponent_profile: dict, context: dict) -> tuple[str, dict]:
        lc_a = actor_profile.get("lc", 1.0)
        lc_b = opponent_profile.get("lc", 1.0)
        
        # Armistizio per sfinimento bellico
        if lc_a < 0.50 or lc_b < 0.50:
            if random.random() < 0.60:
                return "CEASEFIRE", {
                    "actor_disposition_shift": "Diffidente",
                    "target_disposition_shift": "Diffidente"
                }

        base_war_p = self.cfg.get("border_friction_escalation_base", 0.30)
        war_mods = self.cfg.get("disposition_war_modifiers", {})

        mod_a = war_mods.get(actor_profile.get("disposition", "Neutrale"), 0.0)
        mod_b = war_mods.get(opponent_profile.get("disposition", "Neutrale"), 0.0)
        lc_advantage = (lc_a - lc_b) * 0.20

        escalation_prob = max(0.05, min(0.95, base_war_p + mod_a + mod_b + lc_advantage))

        if random.random() < escalation_prob:
            action = "ATTACK" if (mod_a > 0.2 or lc_a > lc_b) else "EMBARGO"
        else:
            action = "NEGOTIATE" if random.random() < 0.60 else "CONCEDE"

        feedback = {
            "actor_disposition_shift": "Diffidente" if action in ["ATTACK", "EMBARGO"] and actor_profile.get("disposition") == "Collaborativa" else None,
            "target_disposition_shift": "Ostile" if action == "ATTACK" else ("Diffidente" if action == "EMBARGO" else None),
            "actor_lc_penalty": self.tech_cfg.get("war_damage_lc_penalty", 0.015) if action == "ATTACK" else 0.0,
            "target_lc_penalty": self.tech_cfg.get("war_damage_lc_penalty", 0.015) if action == "ATTACK" else 0.0
        }
        return action, feedback

    def decide_federation_offer(self, actor_profile: dict, other_profiles: list, context: dict) -> tuple[bool, dict]:
        min_score = self.cfg.get("federation_min_compatibility_score", 0.60)
        compatible_count = sum(1 for p in other_profiles if p.get("disposition") in ["Collaborativa", "Pacifica", "Leale a Sol"])
        score = compatible_count / max(1, len(other_profiles))
        accepted = score >= min_score and actor_profile.get("disposition") in ["Collaborativa", "Pacifica", "Leale a Sol"]
        feedback = {"actor_disposition_shift": "Collaborativa" if accepted else None}
        return accepted, feedback


# ==============================================================================
# GESTORE DIPLOMATICO CENTRALE
# ==============================================================================
class DiplomaticManager:
    def __init__(self, ai_agent: BaseAIDiplomacyAgent = None):
        self.relations = {}
        self.trade_routes = []
        self.federations = []
        self.war_casualties = {}
        self.conquered_worlds = []
        self.starbase_incidents = []
        self.ai_engine = ai_agent

    def _get_pair_key(self, f1, f2):
        return tuple(sorted([str(f1), str(f2)]))

    def get_relation(self, f1, f2):
        if str(f1) == str(f2):
            return DiplomaticRelation.FEDERAZIONE
        key = self._get_pair_key(f1, f2)
        return self.relations.get(key, DiplomaticRelation.NEUTRALE)

    def set_relation(self, f1, f2, relation_status):
        key = self._get_pair_key(f1, f2)
        self.relations[key] = relation_status

    def is_faction_at_war(self, faction_name: str) -> bool:
        f_name = str(faction_name)
        for pair_key, status in self.relations.items():
            if f_name in pair_key and status == DiplomaticRelation.GUERRA:
                return True
        return False

    def evaluate_initial_relation_profiles(self, prof1: dict, prof2: dict):
        f1, f2 = prof1["faction_name"], prof2["faction_name"]
        key = self._get_pair_key(f1, f2)
        if key in self.relations:
            return self.relations[key]

        m1, m2 = prof1.get("mother_faction"), prof2.get("mother_faction")
        disp1 = prof1.get("disposition", "Neutrale")
        disp2 = prof2.get("disposition", "Neutrale")

        # 1. Caso: Colonia <---> Propria Madrepatria
        if m1 == f2 or m2 == f1:
            colony_disp = disp1 if m1 == f2 else disp2
            if colony_disp in ["Ostile", "Predatoria"]:
                status = DiplomaticRelation.GUERRA  # Guerra di Indipendenza
            elif colony_disp == "Diffidente":
                status = DiplomaticRelation.DIFFIDENZA
            elif colony_disp in ["Collaborativa", "Leale a Sol", "Leale alla Madrepatria"]:
                status = DiplomaticRelation.COOPERAZIONE
            else:
                status = DiplomaticRelation.NEUTRALE

        # 2. Caso: Due Colonie Sorelle (stessa Madrepatria) -> Solidarietà Fraterna
        elif m1 and m2 and (m1 == m2):
            if disp1 in ["Predatoria", "Ostile"] and disp2 in ["Predatoria", "Ostile"]:
                status = DiplomaticRelation.NEUTRALE
            else:
                status = DiplomaticRelation.COOPERAZIONE

        # 3. Caso: Imperi alieni o fazioni non imparentate
        else:
            hostile_disps = ["Ostile", "Predatoria"]
            friendly_disps = ["Pacifica", "Collaborativa", "Leale a Sol", "Esplorativa"]
            if disp1 in hostile_disps or disp2 in hostile_disps:
                status = DiplomaticRelation.DIFFIDENZA
            elif disp1 in friendly_disps and disp2 in friendly_disps:
                status = DiplomaticRelation.COOPERAZIONE
            else:
                status = DiplomaticRelation.NEUTRALE

        self.relations[key] = status
        return status

    def evaluate_initial_relation(self, f1, disp1, f2, disp2):
        prof1 = {"faction_name": f1, "disposition": disp1}
        prof2 = {"faction_name": f2, "disposition": disp2}
        return self.evaluate_initial_relation_profiles(prof1, prof2)

    def declare_total_retaliation_war(self, motherland_faction, usurper_faction, starbase_name, current_year):
        """Casus Belli Immediato: Dichiarazione di guerra totale per la caduta/ammutinamento di una Starbase."""
        self.set_relation(motherland_faction, usurper_faction, DiplomaticRelation.GUERRA)
        
        # Cancella immediatamente tutte le rotte commerciali
        self.trade_routes = [
            r for r in self.trade_routes 
            if self._get_pair_key(r.faction_a, r.faction_b) != self._get_pair_key(motherland_faction, usurper_faction)
        ]
        
        incident_report = {
            "starbase_name": starbase_name,
            "motherland": motherland_faction,
            "usurper": usurper_faction,
            "year": current_year
        }
        self.starbase_incidents.append(incident_report)
        return incident_report

    def negotiate_trade_route(self, s1_id, s2_id, p1_obj, p2_obj, dist_ly, current_year):
        f1, f2 = p1_obj.faction_name, p2_obj.faction_name
        rel = self.get_relation(f1, f2)
        
        if rel in [DiplomaticRelation.GUERRA, DiplomaticRelation.EMBARGO]:
            return None, {}

        for r in self.trade_routes:
            if {r.source_star_id, r.target_star_id} == {s1_id, s2_id}:
                return None, {}

        prof1 = p1_obj.get_state_profile()
        prof2 = p2_obj.get_state_profile()

        if self.ai_engine:
            accepted, feedback = self.ai_engine.decide_trade_proposal(prof1, prof2, dist_ly)
        else:
            accepted, feedback = True, {}

        if accepted:
            route = TradeRoute(s1_id, s2_id, f1, f2, dist_ly, current_year)
            self.trade_routes.append(route)
            self.set_relation(f1, f2, DiplomaticRelation.COOPERAZIONE)
            return route, feedback

        return None, feedback

    def resolve_border_friction(self, s1_id, s2_id, p1_obj, p2_obj, system_name, current_year):
        f1, f2 = p1_obj.faction_name, p2_obj.faction_name
        prof1 = p1_obj.get_state_profile()
        prof2 = p2_obj.get_state_profile()

        if self.ai_engine:
            action, feedback = self.ai_engine.decide_border_conflict(prof1, prof2, {"system": system_name, "year": current_year})
        else:
            action, feedback = "EMBARGO", {}

        if action == "ATTACK":
            self.set_relation(f1, f2, DiplomaticRelation.GUERRA)
            self.trade_routes = [r for r in self.trade_routes if self._get_pair_key(r.faction_a, r.faction_b) != self._get_pair_key(f1, f2)]
            return DiplomaticRelation.GUERRA, feedback
        elif action == "EMBARGO":
            self.set_relation(f1, f2, DiplomaticRelation.EMBARGO)
            self.trade_routes = [r for r in self.trade_routes if self._get_pair_key(r.faction_a, r.faction_b) != self._get_pair_key(f1, f2)]
            return DiplomaticRelation.EMBARGO, feedback
        elif action == "CEASEFIRE":
            self.set_relation(f1, f2, DiplomaticRelation.DIFFIDENZA)
            return DiplomaticRelation.DIFFIDENZA, feedback
        else:
            return DiplomaticRelation.DIFFIDENZA, feedback