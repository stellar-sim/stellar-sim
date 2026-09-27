################################################################################
# FILE: core/agents.py
################################################################################

import random

class AgentShip:
    def __init__(
        self, 
        ship_name, 
        faction_name, 
        origin_system_id, 
        ship_speed, 
        max_reach, 
        is_terrestrial=False, 
        disposition="Neutrale", 
        civilization_level=1.0, 
        homeworld_system_id=None
    ):
        self.ship_name = ship_name
        self.faction_name = faction_name
        self.origin_system_id = origin_system_id
        self.current_system_id = origin_system_id
        self.homeworld_system_id = homeworld_system_id or origin_system_id
        
        self.ship_speed = ship_speed
        self.max_reach = max_reach
        self.is_terrestrial = is_terrestrial
        self.disposition = disposition
        self.civilization_level = civilization_level
        
        self.ship_fuel = 1.0
        self.ship_health = 1.0
        self.is_active = True
        
        self.visited_path = [self.current_system_id]
        self.explored_branches = {}
        self.colonized_systems = []
        
        self.busy_until_hours = 0.0

    def is_available(self, current_sim_hours):
        return self.is_active and (current_sim_hours >= self.busy_until_hours)

    def update_status_after_travel(self, dist, fuel_base, fuel_per_ly, health_per_ly):
        self.ship_fuel = max(0.0, self.ship_fuel - (fuel_base + (dist * fuel_per_ly)))
        self.ship_health = max(0.0, self.ship_health - (0.01 + (dist * health_per_ly)))
        if self.ship_fuel <= 0.05:
            self.is_active = False

    def refuel_at_colony(self, fuel_amount, repair_amount):
        self.ship_fuel = min(1.0, self.ship_fuel + fuel_amount)
        self.ship_health = min(1.0, self.ship_health + repair_amount)