import math
from core.AbstractComponent import AbstractComponent
from core.DynamicObservable import DynamicObservable

class BatteryStarter(AbstractComponent):
    """Système de démarrage et batterie 12V."""
    def setup(self):
        self.add_observable(DynamicObservable("voltage", "Tension Batterie", 12.6))
        self.add_observable(DynamicObservable("current", "Courant d'Appel", 0.0))
        self.add_observable(DynamicObservable("temp", "Température Batterie", 20.0))
        self.add_observable(DynamicObservable("starter_rpm", "Vitesse Démarreur", 0.0))
        self.add_observable(DynamicObservable("relay_state", "État Relais", 0.0))

        # regles internes
        
        # temperature batterie via effet joules
        def temp_rule(curr_temp, dt, current):
            heat_gen = (current / 100.0) ** 2 * 0.15
            heat_loss = (curr_temp - 20.0) * (1.0 - math.exp(-0.02 * dt))
            return (heat_gen - heat_loss) * dt
        self.temp.add_evolution_rule(temp_rule, [self.current])
        
