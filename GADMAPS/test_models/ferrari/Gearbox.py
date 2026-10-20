import math
from core.AbstractComponent import AbstractComponent
from core.DynamicObservable import DynamicObservable

class Gearbox(AbstractComponent):
    """Boîte double embrayage arrière."""
    def setup(self):
        self.add_observable(DynamicObservable("gear", "Rapport Engagé", 0.0))
        self.add_observable(DynamicObservable("oil_temp", "Temp Huile Boîte", 20.0))
        self.add_observable(DynamicObservable("clutch_even_press", "Pression Embrayage Pair", 0.0))
        self.add_observable(DynamicObservable("clutch_odd_press", "Pression Embrayage Impair", 0.0))
        self.add_observable(DynamicObservable("primary_rpm", "Vitesse Arbre Primaire", 0.0))
        self.add_observable(DynamicObservable("secondary_rpm", "Vitesse Arbre Secondaire", 0.0))

        # regles internes
        
        # on fait chauffer l'huile de boîte via la friction visqueuse
        def box_temp_rule(curr_temp, dt, rpm):
            heat_gen = (rpm / 1000.0) * 0.3
            heat_loss = (curr_temp - 20.0) * (1.0 - math.exp(-0.02 * dt))
            return (heat_gen - heat_loss) * dt
            
        self.oil_temp.add_evolution_rule(box_temp_rule, [self.primary_rpm])
