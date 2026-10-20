import math
from core.AbstractComponent import AbstractComponent
from core.DynamicObservable import DynamicObservable

class WheelsTires(AbstractComponent):
    """Dynamique des trains roulants."""
    def setup(self):
        self.add_observable(DynamicObservable("wheel_rpm", "Vitesse Roue", 0.0))
        self.add_observable(DynamicObservable("tire_press", "Pression Pneus", 2.4))
        self.add_observable(DynamicObservable("surface_temp", "Temp Gomme", 20.0))
        self.add_observable(DynamicObservable("lat_accel", "G Latéral", 0.0))
        self.add_observable(DynamicObservable("long_accel", "G Longitudinal", 0.0))

        # regle interne: theromdynamique
        # on applique la loi de Charles (P/T = constante à volume constant)
        def tire_press_rule(curr_press, dt, temp):
            temp_kelvin = temp + 273.15
            # base de 2.4 bar à 20°C
            target_press = 2.4 * (temp_kelvin / 293.15)
            # l'air met un peu de temps à s'equilibrer thermiquement avec la surface
            return (target_press - curr_press) * (1.0 - math.exp(-0.5 * dt))
            
        self.tire_press.add_evolution_rule(tire_press_rule, [self.surface_temp])