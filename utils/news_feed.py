################################################################################
# FILE: utils/news_feed.py
################################################################################

from collections import Counter

class GalacticNewsNetwork:
    def __init__(self, broadcast_interval_years=50.0):
        self.interval_years = broadcast_interval_years
        self.next_broadcast_year = broadcast_interval_years
        
        self.epoch_emancipations = []
        self.epoch_combats_count = 0
        self.epoch_combat_sectors = Counter()
        self.epoch_diplomacy = []
        self.epoch_archeology = []

    def record_emancipation(self, planet_name, system_name, faction_name, disposition):
        self.epoch_emancipations.append(f"{planet_name} ({system_name}) ha dichiarato la sovranità [{disposition.upper()}].")

    def record_combat(self, ship1, faction1, ship2, faction2, system_name):
        # Aggrega statisticamente invece di salvare ogni singola riga testuale
        self.epoch_combats_count += 1
        self.epoch_combat_sectors[system_name] += 1

    def record_diplomacy(self, faction1, faction2, system_name, is_refuel=False):
        self.epoch_diplomacy.append(f"Accordo tra {faction1} e {faction2} nel sistema {system_name}.")

    def record_archeology(self, planet_name, civ_name, cause):
        self.epoch_archeology.append(f"Rovine di '{civ_name}' su {planet_name} (Causa: {cause}).")

    def should_broadcast(self, current_year):
        return current_year >= self.next_broadcast_year

    def generate_broadcast(self, current_year, agents_list, logger):
        """Genera un bollettino GNN compatto ed essenziale."""
        logger.log_raw("\n" + "=" * 80)
        logger.log_raw(f"|                  GALACTIC NEWS NETWORK (GNN) - ANNO {current_year:6.1f}                   |")
        logger.log_raw("=" * 80)

        # 1. Nuove Sovranità (mostra solo conteggio o max 3-4 nomi)
        if self.epoch_emancipations:
            logger.log_raw(f"\n  [SOVRANITA & SECESSIONI ({len(self.epoch_emancipations)})]")
            for item in self.epoch_emancipations[:5]: # Max 5 per non intasare
                logger.log_raw(f"    * {item}")
            if len(self.epoch_emancipations) > 5:
                logger.log_raw(f"    * ... e altri {len(self.epoch_emancipations) - 5} governi coloniali.")
        else:
            logger.log_raw("\n  [SOVRANITA] Nessun nuovo movimento di secessione in quest'epoca.")

        # 2. Sintesi Conflitti (SOLO 2 RIGHE STATISTICHE)
        if self.epoch_combats_count > 0:
            top_sectors = [sec for sec, _ in self.epoch_combat_sectors.most_common(3)]
            logger.log_raw(f"\n  [CRONACA DI GUERRA & FRONTIERE]")
            logger.log_raw(f"    * Registrate {self.epoch_combats_count} schermaglie armate lungo le frontiere.")
            logger.log_raw(f"    * Teatri principali di scontro: {', '.join(top_sectors)}")
        else:
            logger.log_raw("\n  [SICUREZZA] Nessun ingaggio armato registrato lungo le rotte.")

        # 3. Scoperte Archeologiche (Grande Filtro)
        if self.epoch_archeology:
            logger.log_raw("\n  [ARCHEOLOGIA & GRANDE FILTRO]")
            for item in self.epoch_archeology:
                logger.log_raw(f"    * {item}")

        # 4. Potenza Leader
        active_factions = sorted(agents_list, key=lambda ag: len(set(ag.visited_path)) + len(ag.colonized_systems) * 2, reverse=True)
        if active_factions:
            leader = active_factions[0]
            logger.log_raw(f"\n  [INDICE DI DOMINIO GALATTICO]")
            logger.log_raw(f"    * Fazione Leader: {leader.faction_name} (Sistemi: {len(set(leader.visited_path))}, Flotte: {len([a for a in agents_list if a.faction_name == leader.faction_name])})")

        logger.log_raw("=" * 80 + "\n")

        # Reset buffer
        self.epoch_emancipations.clear()
        self.epoch_combats_count = 0
        self.epoch_combat_sectors.clear()
        self.epoch_diplomacy.clear()
        self.epoch_archeology.clear()
        self.next_broadcast_year += self.interval_years