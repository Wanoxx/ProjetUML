import math
from core.AbstractComponent import AbstractComponent
from core.DynamicObservable import DynamicObservable

class EngineV12(AbstractComponent):
    """
    Le bloc moteur thermique F140 GA.
    Gère la dynamique interne des fluides et de la mécanique.
    """
    def setup(self):
        self.add_observable(DynamicObservable("rpm", "Régime Moteur (RPM)", 0.0))
        self.add_observable(DynamicObservable("oil_temp", "Température Huile (°C)", 20.0))
        self.add_observable(DynamicObservable("oil_press", "Pression Huile (Bar)", 0.0))
        self.add_observable(DynamicObservable("crank_pos", "Position Vilebrequin (°)", 0.0))
        self.add_observable(DynamicObservable("inj_time", "Temps Injection (ms)", 0.0))
        self.add_observable(DynamicObservable("vibration", "Vibrations Bloc (Hz)", 0.0))

        # --- REGLE INTERNE : CINÉMATIQUE DU VILEBREQUIN ---
        # 1 RPM = 360 degrés / 60 secondes = 6 degrés par seconde.
        # J'utilise la formule de la vitesse angulaire (omega).
        def crank_rule(curr_pos, dt, rpm):
            omega_deg_s = rpm * 6.0
            new_pos = (curr_pos + (omega_deg_s * dt)) % 360.0
            return new_pos - curr_pos # Je renvoie toujours le delta pour le DynamicObservable
            
        self.crank_pos.add_evolution_rule(crank_rule, dependencies=[self.rpm])

        # --- REGLE INTERNE : HYDRODYNAMIQUE DE L'HUILE ---
        # La pompe est mécanique. La pression est une fonction du RPM, mais limitée par un clapet de décharge.
        def oil_press_rule(curr_press, dt, rpm):
            # Équation asymptotique : la pression monte vite puis plafonne à 6.0 bars (clapet)
            target_press = 6.0 * (1.0 - math.exp(-rpm / 2000.0)) if rpm > 0 else 0.0
            # Amortissement hydraulique de la montée en pression
            return (target_press - curr_press) * (1.0 - math.exp(-5.0 * dt))
            
        self.oil_press.add_evolution_rule(oil_press_rule, dependencies=[self.rpm])

        # --- REGLE INTERNE : TEMPS D'INJECTION ---
        # Le temps d'ouverture des injecteurs (en millisecondes) augmente avec le régime
        def inj_rule(curr_inj, dt, rpm):
            target_inj = 1.5 + (rpm / 2000.0) if rpm > 0 else 0.0
            return (target_inj - curr_inj) * 10.0 * dt
        self.inj_time.add_evolution_rule(inj_rule, [self.rpm])

        # --- REGLE INTERNE : VIBRATIONS ---
        # Fréquence de vibration primaire du bloc (en Hz)
        def vib_rule(curr_vib, dt, rpm):
            target_vib = rpm / 60.0 # Tours par seconde = Hz
            return (target_vib - curr_vib) * 20.0 * dt
        self.vibration.add_evolution_rule(vib_rule, [self.rpm])
