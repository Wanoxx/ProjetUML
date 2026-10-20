import math
from core.AbstractComponent import AbstractComponent
from core.DynamicObservable import DynamicObservable

class EDiff(AbstractComponent):
    """Différentiel électronique actif."""
    def setup(self):
        self.add_observable(DynamicObservable("actuator_curr", "Courant Actionneur", 0.0))
        self.add_observable(DynamicObservable("hydra_press", "Pression Hydra Diff", 0.0))
        self.add_observable(DynamicObservable("internal_temp", "Temp Interne Diff", 20.0))
        self.add_observable(DynamicObservable("rpm_left", "Vitesse Sortie Gauche", 0.0))
        self.add_observable(DynamicObservable("rpm_right", "Vitesse Sortie Droite", 0.0))

        # regle interne sur la pression hydraulique
        # on réponds à la commande de courant avec un système du premier ordre pour l'actionneur
        def press_rule(curr_press, dt, current):
            target_press = current * 5.0
            return (target_press - curr_press) * (1.0 - math.exp(-8.0 * dt))
            
        self.hydra_press.add_evolution_rule(press_rule, [self.actuator_curr])