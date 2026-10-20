import math
from core.AbstractComponent import AbstractComponent
from core.DynamicObservable import DynamicObservable

class BrakingSystem(AbstractComponent):
    """Freins Carbone-Céramique Brembo."""
    def setup(self):
        self.add_observable(DynamicObservable("disc_temp", "Temp Disques (°C)", 20.0))
        self.add_observable(DynamicObservable("fluid_temp", "Temp Liquide Frein (°C)", 20.0))
        self.add_observable(DynamicObservable("hydra_press", "Pression Freinage (Bar)", 0.0))
        self.add_observable(DynamicObservable("pedal_pos", "Course Pédale (%)", 0.0))
        self.add_observable(DynamicObservable("wear_limit", "Témoin Usure", 0.0))

        def brake_press_rule(curr_press, dt, pedal):
            target_press = pedal * 1.2
            return (target_press - curr_press) * (1.0 - math.exp(-15.0 * dt))
        self.hydra_press.add_evolution_rule(brake_press_rule, [self.pedal_pos])

        # --- REGLE INTERNE : CONDUCTION THERMIQUE (Loi de Fourier) ---
        def fluid_temp_rule(curr_temp, dt, disc_temp):
            k_conduction = 0.002
            k_dissipation = 0.01 
            heat_transfer = max(0, (disc_temp - curr_temp)) * k_conduction
            cooling = (curr_temp - 20.0) * k_dissipation
            return (heat_transfer - cooling) * dt
            
        self.fluid_temp.add_evolution_rule(fluid_temp_rule, [self.disc_temp])

        # regle interne sur l'usure des plaquettes
        # l'usure dépend de la force de freinage (pression hydraulique) et s'aggrave
        # de façon exponentielle si les disques sont en surchauffe (fading thermique).
        def brake_wear_rule(curr_wear, dt, disc_temp, hydra_press):
            # le facteur d'usure explose au-delà de 600°C
            wear_factor = 1.0 + max(0, (disc_temp - 600.0) / 100.0)**2
            # on calcule l'usure générée pendant ce pas de temps (dt)
            wear_increment = (hydra_press * 0.000001 * wear_factor) * dt
            return wear_increment 
            
        self.wear_limit.add_evolution_rule(brake_wear_rule, [self.disc_temp, self.hydra_press])