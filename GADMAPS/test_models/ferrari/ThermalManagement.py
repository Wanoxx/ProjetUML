import math
from core.AbstractComponent import AbstractComponent
from core.DynamicObservable import DynamicObservable

class ThermalManagement(AbstractComponent):
    """Gestion thermique et radiateurs."""
    def setup(self):
        self.add_observable(DynamicObservable("temp_in", "Temp Entrée Liquide", 20.0))
        self.add_observable(DynamicObservable("temp_out", "Temp Sortie Liquide", 20.0))
        self.add_observable(DynamicObservable("pump_rpm", "Vitesse Pompe", 0.0))
        self.add_observable(DynamicObservable("circuit_press", "Pression Circuit", 1.0))
        self.add_observable(DynamicObservable("fan_rpm", "Vitesse Ventilos", 0.0))

        # regle interne sur la pression du circuit

        # on dilate le liquide avec la chaleur, ce qui augmente la pression dans le vase d'expansion.
        def press_rule(curr_press, dt, temp_in):
            target_press = 1.0 + max(0, (temp_in - 20.0)) * 0.015
            # l'equilibrage des pressions dans le circuit se fait avec un leger amortissement
            return (target_press - curr_press) * (1.0 - math.exp(-2.0 * dt))
            
        self.circuit_press.add_evolution_rule(press_rule, [self.temp_in])

        # regle interne sur le ventilateurs de refroidissement

        # les ventilateurs s'allument par paliers pour forcer le refroidissement
        # du liquide quand il devient trop chaud, eg à l'arret ou après un circuit
        def fan_rpm_rule(curr_rpm, dt, temp_out):
            if temp_out > 105.0:
                # vitesse maximale (surchauffe)
                target_rpm = 3000.0
            elif temp_out > 95.0:
                # vitesse moyenne
                target_rpm = 1500.0
            else:
                # eteints en usage normal
                target_rpm = 0.0 
                
            return (target_rpm - curr_rpm) * (1.0 - math.exp(-2.0 * dt))
            
        self.fan_rpm.add_evolution_rule(fan_rpm_rule, [self.temp_out])