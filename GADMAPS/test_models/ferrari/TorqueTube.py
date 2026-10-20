import math
from core.AbstractComponent import AbstractComponent
from core.DynamicObservable import DynamicObservable

class TorqueTube(AbstractComponent):
    """Arbre de transmission rigide."""
    def setup(self):
        self.add_observable(DynamicObservable("shaft_rpm", "Vitesse Arbre", 0.0))
        self.add_observable(DynamicObservable("bearing_temp", "Temp Paliers", 20.0))
        self.add_observable(DynamicObservable("resonance", "Fréquence Résonance", 0.0))

        # regle interne temperature des paliers
        # on fait chauffer les paliers avec la friction de rotation
        def bearing_temp_rule(curr_temp, dt, rpm):
            heat_gen = (rpm / 1000.0) * 0.2
            heat_loss = (curr_temp - 20.0) * (1.0 - math.exp(-0.1 * dt))
            return (heat_gen - heat_loss) * dt
            
        self.bearing_temp.add_evolution_rule(bearing_temp_rule, [self.shaft_rpm])
        
        # regle interne sur resonance
        # vibration de l'arbre
        def resonance_rule(curr_res, dt, rpm):
            target_res = rpm / 60.0
            return (target_res - curr_res) * (1.0 - math.exp(-10.0 * dt))
            
        self.resonance.add_evolution_rule(resonance_rule, [self.shaft_rpm])