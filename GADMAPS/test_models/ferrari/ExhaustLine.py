import math
from core.AbstractComponent import AbstractComponent
from core.DynamicObservable import DynamicObservable

class ExhaustLine(AbstractComponent):
    """Évacuation et dépollution."""
    def setup(self):
        self.add_observable(DynamicObservable("cat_temp", "Temp Catalyseur", 20.0))
        self.add_observable(DynamicObservable("back_press", "Contre-Pression", 1.0))
        self.add_observable(DynamicObservable("lambda_v", "Tension Sonde Lambda", 0.45))
        self.add_observable(DynamicObservable("valve_pos", "Ouverture Clapets", 0.0))

        # regles interne
        
        # contre-pression: augmentation si les clapets sont fermés
        def back_press_rule(curr_press, dt, valve_pos):
            # si les clapets sont fermés (0%), l'échappement force un peu plus, eg 1.5 bar
            target_press = 1.0 + ((100.0 - valve_pos) * 0.005)
            return (target_press - curr_press) * (1.0 - math.exp(-8.0 * dt))
        self.back_press.add_evolution_rule(back_press_rule, [self.valve_pos])