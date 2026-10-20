import math
import random
from core.AbstractComponent import AbstractComponent
from core.DynamicObservable import DynamicObservable

class Suspension(AbstractComponent):
    """Amortisseurs magnétorhéologiques SCM."""
    def setup(self):
        self.add_observable(DynamicObservable("coil_curr", "Courant Bobines (A)", 0.0))
        self.add_observable(DynamicObservable("stroke_mm", "Débattement (mm)", 0.0))
        self.add_observable(DynamicObservable("velocity_ms", "Vitesse Tige (m/s)", 0.0))
        self.add_observable(DynamicObservable("height_v", "Tension Capteur (V)", 2.5))

        # regle interne sur la dynamique masse-ressort-amortisseur
        # m*x'' + c*x' + k*x = F_route
        def suspension_kinematics(curr_stroke, dt, velocity):
            # on calcule le nouveau débattement
            new_stroke = curr_stroke + (velocity * 1000.0 * dt)
            
            # force de bridage: la roue ne peut pas sortir de l'aile (max 80mm)
            # si elle s'enfonce plus que la butée (min -80mm)
            if new_stroke > 80.0: return 80.0 - curr_stroke
            if new_stroke < -80.0: return -80.0 - curr_stroke
            
            return velocity * 1000.0 * dt
        self.stroke_mm.add_evolution_rule(suspension_kinematics, [self.velocity_ms])

        def suspension_dynamics(curr_vel, dt, stroke, coil_curr):
            k_spring = 50000.0 
            c_damping = 2000.0 + (coil_curr * 1500.0)
            mass = 400.0 

            # on reduit un peu le bruit de la route pour aider la stabilité
            f_road = random.gauss(0, 200.0) 
            
            stroke_m = stroke / 1000.0
            accel = (f_road - (k_spring * stroke_m) - (c_damping * curr_vel)) / mass
            
            # calcul de la vitesse future
            new_vel = curr_vel + (accel * dt)
            
            # si on touche une butée, on stoppe net la vitesse
            if (stroke >= 80.0 and new_vel > 0) or (stroke <= -80.0 and new_vel < 0):
                return -curr_vel # la vitesse devient 0
                
            return accel * dt
        self.velocity_ms.add_evolution_rule(suspension_dynamics, [self.stroke_mm, self.coil_curr])

        # on convertit le débattement mécanique de la suspension (en mm) 
        # en un signal électrique (en Volts) lu par le calculateur
        # 0mm = 2.5V (neutre), +80mm = 5.0V (detente max), -80mm = 0.0V (compression max).
        def height_sensor_rule(curr_v, dt, stroke_mm):
            target_v = 2.5 + (stroke_mm / 80.0) * 2.5
            return (target_v - curr_v) * (1.0 - math.exp(-20.0 * dt))
            
        self.height_v.add_evolution_rule(height_sensor_rule, [self.stroke_mm])