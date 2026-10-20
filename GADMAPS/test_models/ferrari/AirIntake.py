import math
from core.AbstractComponent import AbstractComponent
from core.DynamicObservable import DynamicObservable

class AirIntake(AbstractComponent):
    """Admission d'air frais atmosphérique."""
    def setup(self):
        self.add_observable(DynamicObservable("airflow", "Débit d'Air", 0.0))
        self.add_observable(DynamicObservable("air_temp", "Température Admission", 20.0))
        self.add_observable(DynamicObservable("manifold_press", "Pression Collecteur", 1.0))
        self.add_observable(DynamicObservable("throttle_pos", "Position Papillon", 0.0))

        # regle interne
        # la pression du collecteur (manifold pressure) chute quand l'air est aspiré violemment
        def manifold_rule(curr_press, dt, airflow):
            # à l'arrêt on est à 1.0 bar (pression atmo), en pleine charge ça crée un vide partiel.
            target_press = 1.0 - (airflow / 1500.0)

            target_press = max(0.2, target_press)
            return (target_press - curr_press) * (1.0 - math.exp(-10.0 * dt))
            
        self.manifold_press.add_evolution_rule(manifold_rule, [self.airflow])