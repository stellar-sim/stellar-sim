import os
import datetime

class StrategicPlanner:
    def __init__(self, interaction_cfg):
        self.cfg = interaction_cfg.get("interaction_rules", {})
        self.earth_lc = self.cfg.get("earth_lc_start", 1.0)
        self.pd_abs = self.cfg.get("prime_directive_absolute_lc_threshold", 0.7)
        self.hostile_thresh = self.cfg.get("hostile_retreat_lc_advantage_threshold", 1.2)

    def generate_plan(self, planets_data):
        plan = []
        plan.append("================================================================================")
        plan.append("                 PIANO D'AZIONE STRATEGICO PER MISSIONI FUTURE                  ")
        plan.append(f"                 Riferimento Livello Civiltà Terrestre: {self.earth_lc}         ")
        plan.append("================================================================================")
        
        if not planets_data:
            plan.append("\nNessun dato planetario disponibile per formulare raccomandazioni strategiche.")
            return plan

        colonies = [p for p in planets_data if p.get("is_colonized")]
        if colonies:
            plan.append(f"\n[COLONIE ATTIVE ({len(colonies)})]:")
            for c in colonies:
                plan.append(f"  - Avamposto su {c['planet_name']} (Sistema: {c['star_name']})")
                plan.append(f"    Raccomandazione: Inviare convogli logistici di supporto, espandere infrastrutture estrattive e consolidare la presenza.")

        habitable = [p for p in planets_data if p.get("is_habitable_candidate") and not p.get("is_colonized")]
        if habitable:
            plan.append(f"\n[FUTURI OBIETTIVI DI COLONIZZAZIONE ({len(habitable)})]:")
            for h in habitable:
                plan.append(f"  - Candidato Ottimale: {h['planet_name']} (Sistema: {h['star_name']})")
                plan.append(f"    Raccomandazione: Pianificare missione di insediamento coloniale e terraformazione preliminare.")

        civs = [p for p in planets_data if p.get("is_intelligent")]
        if civs:
            plan.append(f"\n[VALUTAZIONE CIVILTA ALIENE ({len(civs)})]:")
            for civ in civs:
                lc = civ.get("lc", 0.0)
                disp = civ.get("disposition", "Ignota")
                plan.append(f"  - Pianeta {civ['planet_name']} (Sistema: {civ['star_name']})")
                plan.append(f"    Indice Civiltà (LC): {lc} | Profilo Comportamentale: {disp}")
                
                if lc < self.earth_lc and lc >= self.pd_abs:
                    plan.append(f"    Strategia: Direttiva Primaria attiva. Sospendere ogni contatto palese. Monitoraggio stealth a lungo termine.")
                elif disp in ["Ostile", "Predatoria"] and lc > (self.earth_lc * self.hostile_thresh):
                    plan.append(f"    STRATEGIA DI EMERGENZA: Minaccia di livello superiore. Isolare il settore e mantenere assetti difensivi.")
                elif disp in ["Pacifica", "Cauta"]:
                    plan.append(f"    Strategia: Opportunità di dialogo diplomatico graduale e scambio scientifico neutrale.")
                else:
                    plan.append(f"    Strategia: Profilo di rischio intermedio. Mantenere distanza di sicurezza e raccogliere ulteriori dati.")

        plan.append("\n================================================================================")
        plan.append("                      FINE DEL DOCUMENTO STRATEGICO                             ")
        plan.append("================================================================================")
        return plan

    def save_plan_to_file(self, plan_lines, plan_directory):
        if not os.path.exists(plan_directory):
            os.makedirs(plan_directory)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(plan_directory, f"strategic_plan_{timestamp}.txt")
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for line in plan_lines:
                    f.write(line + "\n")
            print(f"[STRATEGY] Piano strategico salvato correttamente in: {filepath}")
        except Exception as e:
            print(f"[ERRORE] Impossibile salvare il piano strategico: {e}")