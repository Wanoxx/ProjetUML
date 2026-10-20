from core.AbstractAnomaly import AbstractAnomaly
from core.AbstractComponent import AbstractComponent
from test_models.ferrari.BatteryStarter import BatteryStarter
from test_models.ferrari.AirIntake import AirIntake
from test_models.ferrari.EngineV12 import EngineV12
from test_models.ferrari.ThermalManagement import ThermalManagement
from test_models.ferrari.ExhaustLine import ExhaustLine
from test_models.ferrari.TorqueTube import TorqueTube
from test_models.ferrari.Gearbox import Gearbox
from test_models.ferrari.EDiff import EDiff
from test_models.ferrari.BrakingSystem import BrakingSystem
from test_models.ferrari.Suspension import Suspension
from test_models.ferrari.WheelsTires import WheelsTires

# --- BATTERY & STARTER ---

class BatteryDeadAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Batterie Morte", "La tension s'effondre, impossible de fournir du courant.")
        self.saved_rules = []
        self.saved_voltage = None
        self.saved_next_voltage = None

    @classmethod
    def generate_test_target(cls):
        return BatteryStarter("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        voltage = component.get_observable("voltage")
        if voltage:
            self.saved_voltage = voltage.current_value
            self.saved_next_voltage = voltage.next_value
            if hasattr(voltage, "evolution_rules"):
                # Je confisque les lois de la physique pour éviter que l'alternateur ne recharge
                self.saved_rules = voltage.evolution_rules.copy()
                voltage.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        voltage = component.get_observable("voltage")
        if voltage:
            # Je simule une batterie complètement à plat
            voltage.current_value = 9.0
            voltage.next_value = 9.0

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        voltage = component.get_observable("voltage")
        if voltage and hasattr(voltage, "evolution_rules"):
            # Je rends les règles au moteur physique
            voltage.evolution_rules = self.saved_rules.copy()
            if self.saved_voltage is not None:
                voltage.current_value = self.saved_voltage
                voltage.next_value = (
                    self.saved_next_voltage
                    if self.saved_next_voltage is not None
                    else self.saved_voltage
                )
        self.saved_rules = []
        self.saved_voltage = None
        self.saved_next_voltage = None

class StarterJamAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Démarreur Bloqué", "Le moteur électrique du démarreur est grippé.")
        self.saved_rules = []
        self.saved_starter_rpm = None
        self.saved_next_starter_rpm = None

    @classmethod
    def generate_test_target(cls):
        return BatteryStarter("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        starter_rpm = component.get_observable("starter_rpm")
        if starter_rpm:
            self.saved_starter_rpm = starter_rpm.current_value
            self.saved_next_starter_rpm = starter_rpm.next_value
            if hasattr(starter_rpm, "evolution_rules"):
                self.saved_rules = starter_rpm.evolution_rules.copy()
                starter_rpm.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        starter_rpm = component.get_observable("starter_rpm")
        if starter_rpm:
            # J'empêche le démarreur de tourner malgré le courant
            starter_rpm.current_value = 0.0
            starter_rpm.next_value = 0.0

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        starter_rpm = component.get_observable("starter_rpm")
        if starter_rpm and hasattr(starter_rpm, "evolution_rules"):
            starter_rpm.evolution_rules = self.saved_rules.copy()
            if self.saved_starter_rpm is not None:
                starter_rpm.current_value = self.saved_starter_rpm
                starter_rpm.next_value = (
                    self.saved_next_starter_rpm
                    if self.saved_next_starter_rpm is not None
                    else self.saved_starter_rpm
                )
        self.saved_rules = []
        self.saved_starter_rpm = None
        self.saved_next_starter_rpm = None


# --- AIR INTAKE ---

class IntakeCloggedAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Filtre à Air Bouché", "Réduit drastiquement le débit d'air entrant.")
        self.saved_airflow = None
        self.saved_next_airflow = None
        
    @classmethod
    def generate_test_target(cls):
        return AirIntake("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        airflow = component.get_observable("airflow")
        if airflow:
            self.saved_airflow = airflow.current_value
            self.saved_next_airflow = airflow.next_value

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        airflow = component.get_observable("airflow")
        if airflow:
            # Je bride l'air aspiré par le moteur de moitié (pas de confiscation ici, 
            # on laisse l'équilibre dynamique se faire avec la physique)
            airflow.current_value *= 0.5
            airflow.next_value = airflow.current_value

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        airflow = component.get_observable("airflow")
        if airflow and self.saved_airflow is not None:
            airflow.current_value = self.saved_airflow
            airflow.next_value = (
                self.saved_next_airflow
                if self.saved_next_airflow is not None
                else self.saved_airflow
            )
        self.saved_airflow = None
        self.saved_next_airflow = None

class ThrottleStuckAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Papillon Bloqué Ouvert", "Le papillon des gaz reste bloqué à 100%.")
        self.saved_rules = []
        self.saved_throttle_pos = None
        self.saved_next_throttle_pos = None

    @classmethod
    def generate_test_target(cls):
        return AirIntake("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        throttle_pos = component.get_observable("throttle_pos")
        if throttle_pos:
            self.saved_throttle_pos = throttle_pos.current_value
            self.saved_next_throttle_pos = throttle_pos.next_value
            if hasattr(throttle_pos, "evolution_rules"):
                self.saved_rules = throttle_pos.evolution_rules.copy()
                throttle_pos.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        throttle_pos = component.get_observable("throttle_pos")
        if throttle_pos:
            # Je force le papillon grand ouvert
            throttle_pos.current_value = 100.0
            throttle_pos.next_value = 100.0

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        throttle_pos = component.get_observable("throttle_pos")
        if throttle_pos and hasattr(throttle_pos, "evolution_rules"):
            throttle_pos.evolution_rules = self.saved_rules.copy()
            if self.saved_throttle_pos is not None:
                throttle_pos.current_value = self.saved_throttle_pos
                throttle_pos.next_value = (
                    self.saved_next_throttle_pos
                    if self.saved_next_throttle_pos is not None
                    else self.saved_throttle_pos
                )
        self.saved_rules = []
        self.saved_throttle_pos = None
        self.saved_next_throttle_pos = None

class ManifoldLeakAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Fuite Collecteur", "Perte de la dépression dans le collecteur d'admission.")
        self.saved_rules = []
        self.saved_manifold_press = None
        self.saved_next_manifold_press = None

    @classmethod
    def generate_test_target(cls):
        return AirIntake("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        manifold_press = component.get_observable("manifold_press")
        if manifold_press:
            self.saved_manifold_press = manifold_press.current_value
            self.saved_next_manifold_press = manifold_press.next_value
            if hasattr(manifold_press, "evolution_rules"):
                self.saved_rules = manifold_press.evolution_rules.copy()
                manifold_press.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        manifold_press = component.get_observable("manifold_press")
        if manifold_press:
            # Je force la pression à rester atmosphérique (pas de vide)
            manifold_press.current_value = 1.0
            manifold_press.next_value = 1.0

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        manifold_press = component.get_observable("manifold_press")
        if manifold_press and hasattr(manifold_press, "evolution_rules"):
            manifold_press.evolution_rules = self.saved_rules.copy()
            if self.saved_manifold_press is not None:
                manifold_press.current_value = self.saved_manifold_press
                manifold_press.next_value = (
                    self.saved_next_manifold_press
                    if self.saved_next_manifold_press is not None
                    else self.saved_manifold_press
                )
        self.saved_rules = []
        self.saved_manifold_press = None
        self.saved_next_manifold_press = None


# --- ENGINE V12 ---

class OilLeakAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Fuite d'Huile", "Chute violente de la pression d'huile.")
        self.saved_rules = []
        self.saved_oil_press = None
        self.saved_next_oil_press = None

    @classmethod
    def generate_test_target(cls):
        return EngineV12("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        oil_press = component.get_observable("oil_press")
        if oil_press:
            self.saved_oil_press = oil_press.current_value
            self.saved_next_oil_press = oil_press.next_value
            if hasattr(oil_press, "evolution_rules"):
                self.saved_rules = oil_press.evolution_rules.copy()
                oil_press.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        oil_press = component.get_observable("oil_press")
        if oil_press:
            # Je vide le circuit d'huile totalement pour éviter l'équilibre avec la pompe
            oil_press.current_value = 0.0
            oil_press.next_value = 0.0

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        oil_press = component.get_observable("oil_press")
        if oil_press and hasattr(oil_press, "evolution_rules"):
            oil_press.evolution_rules = self.saved_rules.copy()
            if self.saved_oil_press is not None:
                oil_press.current_value = self.saved_oil_press
                oil_press.next_value = (
                    self.saved_next_oil_press
                    if self.saved_next_oil_press is not None
                    else self.saved_oil_press
                )
        self.saved_rules = []
        self.saved_oil_press = None
        self.saved_next_oil_press = None

class EngineMisfireAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Raté d'Allumage", "Provoque des vibrations massives dans le bloc.")
        self.saved_vibration = None
        self.saved_next_vibration = None
        self.saved_rpm = None
        self.saved_next_rpm = None
        self.saved_inj_time = None
        self.saved_next_inj_time = None
        
    @classmethod
    def generate_test_target(cls):
        return EngineV12("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        vibration = component.get_observable("vibration")
        rpm = component.get_observable("rpm")
        inj_time = component.get_observable("inj_time")
        if vibration:
            self.saved_vibration = vibration.current_value
            self.saved_next_vibration = vibration.next_value
        if rpm:
            self.saved_rpm = rpm.current_value
            self.saved_next_rpm = rpm.next_value
        if inj_time:
            self.saved_inj_time = inj_time.current_value
            self.saved_next_inj_time = inj_time.next_value

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        vibration = component.get_observable("vibration")
        rpm = component.get_observable("rpm")
        inj_time = component.get_observable("inj_time")

        if vibration:
            # Je force un niveau de vibration franchement hors nominal.
            forced_vibration = max(vibration.current_value, 220.0)
            vibration.current_value = forced_vibration
            vibration.next_value = forced_vibration

        if rpm:
            # Un raté d'allumage fait décrocher le régime de façon visible.
            forced_rpm = max(rpm.current_value * 0.72, rpm.current_value - 900.0)
            rpm.current_value = forced_rpm
            rpm.next_value = forced_rpm

        if inj_time:
            # L'ECU allonge l'injection pour tenter de compenser.
            forced_inj_time = max(inj_time.current_value, 8.0)
            inj_time.current_value = forced_inj_time
            inj_time.next_value = forced_inj_time

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        vibration = component.get_observable("vibration")
        rpm = component.get_observable("rpm")
        inj_time = component.get_observable("inj_time")
        if vibration and self.saved_vibration is not None:
            vibration.current_value = self.saved_vibration
            vibration.next_value = (
                self.saved_next_vibration
                if self.saved_next_vibration is not None
                else self.saved_vibration
            )
        if rpm and self.saved_rpm is not None:
            rpm.current_value = self.saved_rpm
            rpm.next_value = (
                self.saved_next_rpm
                if self.saved_next_rpm is not None
                else self.saved_rpm
            )
        if inj_time and self.saved_inj_time is not None:
            inj_time.current_value = self.saved_inj_time
            inj_time.next_value = (
                self.saved_next_inj_time
                if self.saved_next_inj_time is not None
                else self.saved_inj_time
            )
        self.saved_vibration = None
        self.saved_next_vibration = None
        self.saved_rpm = None
        self.saved_next_rpm = None
        self.saved_inj_time = None
        self.saved_next_inj_time = None


# --- THERMAL MANAGEMENT ---

class WaterPumpFailureAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Panne Pompe à Eau", "La pompe s'arrête, l'eau ne circule plus.")
        self.saved_rules = []
        self.saved_pump_rpm = None
        self.saved_next_pump_rpm = None

    @classmethod
    def generate_test_target(cls):
        return ThermalManagement("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        pump_rpm = component.get_observable("pump_rpm")
        if pump_rpm:
            self.saved_pump_rpm = pump_rpm.current_value
            self.saved_next_pump_rpm = pump_rpm.next_value
            if hasattr(pump_rpm, "evolution_rules"):
                self.saved_rules = pump_rpm.evolution_rules.copy()
                pump_rpm.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        pump_rpm = component.get_observable("pump_rpm")
        if pump_rpm:
            # Je stoppe physiquement la pompe
            pump_rpm.current_value = 0.0
            pump_rpm.next_value = 0.0

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        pump_rpm = component.get_observable("pump_rpm")
        if pump_rpm and hasattr(pump_rpm, "evolution_rules"):
            pump_rpm.evolution_rules = self.saved_rules.copy()
            if self.saved_pump_rpm is not None:
                pump_rpm.current_value = self.saved_pump_rpm
                pump_rpm.next_value = (
                    self.saved_next_pump_rpm
                    if self.saved_next_pump_rpm is not None
                    else self.saved_pump_rpm
                )
        self.saved_rules = []
        self.saved_pump_rpm = None
        self.saved_next_pump_rpm = None

class CoolantLeakAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Fuite Liquide Refroidissement", "La pression du circuit retombe à 1 bar.")
        self.saved_rules = []
        self.saved_circuit_press = None
        self.saved_next_circuit_press = None

    @classmethod
    def generate_test_target(cls):
        return ThermalManagement("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        circuit_press = component.get_observable("circuit_press")
        if circuit_press:
            self.saved_circuit_press = circuit_press.current_value
            self.saved_next_circuit_press = circuit_press.next_value
            if hasattr(circuit_press, "evolution_rules"):
                self.saved_rules = circuit_press.evolution_rules.copy()
                circuit_press.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        circuit_press = component.get_observable("circuit_press")
        if circuit_press:
            # Je perce le circuit, la pression redescend
            circuit_press.current_value = 1.0
            circuit_press.next_value = 1.0

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        circuit_press = component.get_observable("circuit_press")
        if circuit_press and hasattr(circuit_press, "evolution_rules"):
            circuit_press.evolution_rules = self.saved_rules.copy()
            if self.saved_circuit_press is not None:
                circuit_press.current_value = self.saved_circuit_press
                circuit_press.next_value = (
                    self.saved_next_circuit_press
                    if self.saved_next_circuit_press is not None
                    else self.saved_circuit_press
                )
        self.saved_rules = []
        self.saved_circuit_press = None
        self.saved_next_circuit_press = None

class FanFailureAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Panne Ventilateurs", "Les ventilateurs refusent de s'allumer.")
        self.saved_rules = []
        self.saved_fan_rpm = None
        self.saved_next_fan_rpm = None

    @classmethod
    def generate_test_target(cls):
        return ThermalManagement("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        fan_rpm = component.get_observable("fan_rpm")
        if fan_rpm:
            self.saved_fan_rpm = fan_rpm.current_value
            self.saved_next_fan_rpm = fan_rpm.next_value
            if hasattr(fan_rpm, "evolution_rules"):
                self.saved_rules = fan_rpm.evolution_rules.copy()
                fan_rpm.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        fan_rpm = component.get_observable("fan_rpm")
        if fan_rpm:
            # J'empêche le refroidissement forcé
            fan_rpm.current_value = 0.0
            fan_rpm.next_value = 0.0

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        fan_rpm = component.get_observable("fan_rpm")
        if fan_rpm and hasattr(fan_rpm, "evolution_rules"):
            fan_rpm.evolution_rules = self.saved_rules.copy()
            if self.saved_fan_rpm is not None:
                fan_rpm.current_value = self.saved_fan_rpm
                fan_rpm.next_value = (
                    self.saved_next_fan_rpm
                    if self.saved_next_fan_rpm is not None
                    else self.saved_fan_rpm
                )
        self.saved_rules = []
        self.saved_fan_rpm = None
        self.saved_next_fan_rpm = None


# --- EXHAUST LINE ---

class ExhaustBlockedAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Échappement Bouché", "La contre-pression monte dangereusement.")
        self.saved_rules = []
        self.saved_back_press = None
        self.saved_next_back_press = None
        
    @classmethod
    def generate_test_target(cls):
        return ExhaustLine("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        back_press = component.get_observable("back_press")
        if back_press:
            self.saved_back_press = back_press.current_value
            self.saved_next_back_press = back_press.next_value
            if hasattr(back_press, "evolution_rules"):
                self.saved_rules = back_press.evolution_rules.copy()
                back_press.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        back_press = component.get_observable("back_press")
        if back_press:
            # J'étouffe le moteur en forçant une forte contre-pression.
            forced_back_press = max(back_press.current_value, 4.8)
            back_press.current_value = forced_back_press
            back_press.next_value = forced_back_press

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        back_press = component.get_observable("back_press")
        if back_press and hasattr(back_press, "evolution_rules"):
            back_press.evolution_rules = self.saved_rules.copy()
            if self.saved_back_press is not None:
                back_press.current_value = self.saved_back_press
                back_press.next_value = (
                    self.saved_next_back_press
                    if self.saved_next_back_press is not None
                    else self.saved_back_press
                )
        self.saved_rules = []
        self.saved_back_press = None
        self.saved_next_back_press = None

class LambdaSensorDeadAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Sonde Lambda Morte", "La sonde renvoie une valeur fixe (0.45V).")
        self.saved_rules = []
        self.saved_lambda_v = None
        self.saved_next_lambda_v = None

    @classmethod
    def generate_test_target(cls):
        return ExhaustLine("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        lambda_v = component.get_observable("lambda_v")
        if lambda_v:
            self.saved_lambda_v = lambda_v.current_value
            self.saved_next_lambda_v = lambda_v.next_value
            if hasattr(lambda_v, "evolution_rules"):
                self.saved_rules = lambda_v.evolution_rules.copy()
                lambda_v.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        lambda_v = component.get_observable("lambda_v")
        if lambda_v:
            # Je fige le capteur
            lambda_v.current_value = 0.45
            lambda_v.next_value = 0.45

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        lambda_v = component.get_observable("lambda_v")
        if lambda_v and hasattr(lambda_v, "evolution_rules"):
            lambda_v.evolution_rules = self.saved_rules.copy()
            if self.saved_lambda_v is not None:
                lambda_v.current_value = self.saved_lambda_v
                lambda_v.next_value = (
                    self.saved_next_lambda_v
                    if self.saved_next_lambda_v is not None
                    else self.saved_lambda_v
                )
        self.saved_rules = []
        self.saved_lambda_v = None
        self.saved_next_lambda_v = None


# --- TORQUE TUBE ---

class TorqueTubeBearingFailureAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Palier Arbre Cassé", "Surchauffe massive des paliers de l'arbre.")
        self.saved_bearing_temp = None
        self.saved_next_bearing_temp = None
        
    @classmethod
    def generate_test_target(cls):
        return TorqueTube("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        bearing_temp = component.get_observable("bearing_temp")
        if bearing_temp:
            self.saved_bearing_temp = bearing_temp.current_value
            self.saved_next_bearing_temp = bearing_temp.next_value

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        bearing_temp = component.get_observable("bearing_temp")
        if bearing_temp:
            # Je simule un frottement métal contre métal
            bearing_temp.current_value += 30.0 * dt
            bearing_temp.next_value = bearing_temp.current_value

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        bearing_temp = component.get_observable("bearing_temp")
        if bearing_temp and self.saved_bearing_temp is not None:
            bearing_temp.current_value = self.saved_bearing_temp
            bearing_temp.next_value = (
                self.saved_next_bearing_temp
                if self.saved_next_bearing_temp is not None
                else self.saved_bearing_temp
            )
        self.saved_bearing_temp = None
        self.saved_next_bearing_temp = None


# --- GEARBOX ---

class GearboxFluidOverheatAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Surchauffe Boîte", "L'huile de la boîte DCT surchauffe.")
        self.saved_rules = []
        self.saved_oil_temp = None
        self.saved_next_oil_temp = None
        self.saved_even_press = None
        self.saved_next_even_press = None
        self.saved_odd_press = None
        self.saved_next_odd_press = None
        self.saved_secondary_rpm = None
        self.saved_next_secondary_rpm = None
        
    @classmethod
    def generate_test_target(cls):
        return Gearbox("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        oil_temp = component.get_observable("oil_temp")
        clutch_even_press = component.get_observable("clutch_even_press")
        clutch_odd_press = component.get_observable("clutch_odd_press")
        secondary_rpm = component.get_observable("secondary_rpm")
        if oil_temp:
            self.saved_oil_temp = oil_temp.current_value
            self.saved_next_oil_temp = oil_temp.next_value
            if hasattr(oil_temp, "evolution_rules"):
                self.saved_rules = oil_temp.evolution_rules.copy()
                oil_temp.evolution_rules.clear()
        if clutch_even_press:
            self.saved_even_press = clutch_even_press.current_value
            self.saved_next_even_press = clutch_even_press.next_value
        if clutch_odd_press:
            self.saved_odd_press = clutch_odd_press.current_value
            self.saved_next_odd_press = clutch_odd_press.next_value
        if secondary_rpm:
            self.saved_secondary_rpm = secondary_rpm.current_value
            self.saved_next_secondary_rpm = secondary_rpm.next_value
        
    def apply(self, component: "AbstractComponent", dt: float) -> None:
        oil_temp = component.get_observable("oil_temp")
        clutch_even_press = component.get_observable("clutch_even_press")
        clutch_odd_press = component.get_observable("clutch_odd_press")
        secondary_rpm = component.get_observable("secondary_rpm")

        if oil_temp:
            # Je force une vraie surchauffe tant que l'anomalie est active.
            overheated_temp = max(oil_temp.current_value, 260.0)
            oil_temp.current_value = overheated_temp
            oil_temp.next_value = overheated_temp

        if clutch_even_press:
            degraded_even_press = min(clutch_even_press.current_value, 42.0)
            clutch_even_press.current_value = degraded_even_press
            clutch_even_press.next_value = degraded_even_press

        if clutch_odd_press:
            degraded_odd_press = min(clutch_odd_press.current_value, 42.0)
            clutch_odd_press.current_value = degraded_odd_press
            clutch_odd_press.next_value = degraded_odd_press

        if secondary_rpm:
            slipping_secondary_rpm = secondary_rpm.current_value * 0.82
            secondary_rpm.current_value = slipping_secondary_rpm
            secondary_rpm.next_value = slipping_secondary_rpm

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        oil_temp = component.get_observable("oil_temp")
        clutch_even_press = component.get_observable("clutch_even_press")
        clutch_odd_press = component.get_observable("clutch_odd_press")
        secondary_rpm = component.get_observable("secondary_rpm")
        if oil_temp and hasattr(oil_temp, "evolution_rules"):
            oil_temp.evolution_rules = self.saved_rules.copy()
            if self.saved_oil_temp is not None:
                oil_temp.current_value = self.saved_oil_temp
                oil_temp.next_value = (
                    self.saved_next_oil_temp
                    if self.saved_next_oil_temp is not None
                    else self.saved_oil_temp
                )
        if clutch_even_press and self.saved_even_press is not None:
            clutch_even_press.current_value = self.saved_even_press
            clutch_even_press.next_value = (
                self.saved_next_even_press
                if self.saved_next_even_press is not None
                else self.saved_even_press
            )
        if clutch_odd_press and self.saved_odd_press is not None:
            clutch_odd_press.current_value = self.saved_odd_press
            clutch_odd_press.next_value = (
                self.saved_next_odd_press
                if self.saved_next_odd_press is not None
                else self.saved_odd_press
            )
        if secondary_rpm and self.saved_secondary_rpm is not None:
            secondary_rpm.current_value = self.saved_secondary_rpm
            secondary_rpm.next_value = (
                self.saved_next_secondary_rpm
                if self.saved_next_secondary_rpm is not None
                else self.saved_secondary_rpm
            )
        self.saved_rules = []
        self.saved_oil_temp = None
        self.saved_next_oil_temp = None
        self.saved_even_press = None
        self.saved_next_even_press = None
        self.saved_odd_press = None
        self.saved_next_odd_press = None
        self.saved_secondary_rpm = None
        self.saved_next_secondary_rpm = None

class ClutchSlipAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Embrayage Glissant", "Perte de pression hydraulique sur les embrayages.")
        self.saved_rules_even = []
        self.saved_rules_odd = []
        self.saved_even_press = None
        self.saved_next_even_press = None
        self.saved_odd_press = None
        self.saved_next_odd_press = None
        self.saved_secondary_rpm = None
        self.saved_next_secondary_rpm = None

    @classmethod
    def generate_test_target(cls):
        return Gearbox("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        c_even = component.get_observable("clutch_even_press")
        c_odd = component.get_observable("clutch_odd_press")
        secondary_rpm = component.get_observable("secondary_rpm")
        
        if c_even:
            self.saved_even_press = c_even.current_value
            self.saved_next_even_press = c_even.next_value
            if hasattr(c_even, "evolution_rules"):
                self.saved_rules_even = c_even.evolution_rules.copy()
                c_even.evolution_rules.clear()
        if c_odd:
            self.saved_odd_press = c_odd.current_value
            self.saved_next_odd_press = c_odd.next_value
            if hasattr(c_odd, "evolution_rules"):
                self.saved_rules_odd = c_odd.evolution_rules.copy()
                c_odd.evolution_rules.clear()
        if secondary_rpm:
            self.saved_secondary_rpm = secondary_rpm.current_value
            self.saved_next_secondary_rpm = secondary_rpm.next_value

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        c_even = component.get_observable("clutch_even_press")
        c_odd = component.get_observable("clutch_odd_press")
        secondary_rpm = component.get_observable("secondary_rpm")
        
        # Je laisse la pression s'effondrer presque totalement pour rendre le glissement visible.
        if c_even:
            c_even.current_value = min(c_even.current_value, 2.0)
            c_even.next_value = c_even.current_value
        if c_odd:
            c_odd.current_value = min(c_odd.current_value, 2.0)
            c_odd.next_value = c_odd.current_value
        if secondary_rpm:
            slipping_secondary_rpm = secondary_rpm.current_value * 0.6
            secondary_rpm.current_value = slipping_secondary_rpm
            secondary_rpm.next_value = slipping_secondary_rpm

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        c_even = component.get_observable("clutch_even_press")
        c_odd = component.get_observable("clutch_odd_press")
        secondary_rpm = component.get_observable("secondary_rpm")
        
        if c_even and hasattr(c_even, "evolution_rules"):
            c_even.evolution_rules = self.saved_rules_even.copy()
            if self.saved_even_press is not None:
                c_even.current_value = self.saved_even_press
                c_even.next_value = (
                    self.saved_next_even_press
                    if self.saved_next_even_press is not None
                    else self.saved_even_press
                )
        if c_odd and hasattr(c_odd, "evolution_rules"):
            c_odd.evolution_rules = self.saved_rules_odd.copy()
            if self.saved_odd_press is not None:
                c_odd.current_value = self.saved_odd_press
                c_odd.next_value = (
                    self.saved_next_odd_press
                    if self.saved_next_odd_press is not None
                    else self.saved_odd_press
                )
        if secondary_rpm and self.saved_secondary_rpm is not None:
            secondary_rpm.current_value = self.saved_secondary_rpm
            secondary_rpm.next_value = (
                self.saved_next_secondary_rpm
                if self.saved_next_secondary_rpm is not None
                else self.saved_secondary_rpm
            )
        self.saved_rules_even = []
        self.saved_rules_odd = []
        self.saved_even_press = None
        self.saved_next_even_press = None
        self.saved_odd_press = None
        self.saved_next_odd_press = None
        self.saved_secondary_rpm = None
        self.saved_next_secondary_rpm = None


# --- E-DIFF ---

class EDiffActuatorFailureAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Panne Différentiel", "L'actionneur ne met plus de pression hydraulique.")
        self.saved_rules = []
        self.saved_hydra_press = None
        self.saved_next_hydra_press = None

    @classmethod
    def generate_test_target(cls):
        return EDiff("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        hydra_press = component.get_observable("hydra_press")
        if hydra_press:
            self.saved_hydra_press = hydra_press.current_value
            self.saved_next_hydra_press = hydra_press.next_value
            if hasattr(hydra_press, "evolution_rules"):
                self.saved_rules = hydra_press.evolution_rules.copy()
                hydra_press.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        hydra_press = component.get_observable("hydra_press")
        if hydra_press:
            # Le différentiel reste ouvert en permanence
            hydra_press.current_value = 0.0
            hydra_press.next_value = 0.0

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        hydra_press = component.get_observable("hydra_press")
        if hydra_press and hasattr(hydra_press, "evolution_rules"):
            hydra_press.evolution_rules = self.saved_rules.copy()
            if self.saved_hydra_press is not None:
                hydra_press.current_value = self.saved_hydra_press
                hydra_press.next_value = (
                    self.saved_next_hydra_press
                    if self.saved_next_hydra_press is not None
                    else self.saved_hydra_press
                )
        self.saved_rules = []
        self.saved_hydra_press = None
        self.saved_next_hydra_press = None


# --- BRAKING SYSTEM ---

class BrakeFluidBoilAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Ébullition Liquide Frein", "Perte totale de freinage (Fading).")
        self.saved_rules = []
        self.saved_hydra_press = None
        self.saved_next_hydra_press = None

    @classmethod
    def generate_test_target(cls):
        return BrakingSystem("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        hydra_press = component.get_observable("hydra_press")
        if hydra_press:
            self.saved_hydra_press = hydra_press.current_value
            self.saved_next_hydra_press = hydra_press.next_value
            if hasattr(hydra_press, "evolution_rules"):
                self.saved_rules = hydra_press.evolution_rules.copy()
                hydra_press.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        hydra_press = component.get_observable("hydra_press")
        if hydra_press:
            # Je rends le liquide spongieux (gaz), impossible de freiner
            hydra_press.current_value = 0.0
            hydra_press.next_value = 0.0

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        hydra_press = component.get_observable("hydra_press")
        if hydra_press and hasattr(hydra_press, "evolution_rules"):
            hydra_press.evolution_rules = self.saved_rules.copy()
            if self.saved_hydra_press is not None:
                hydra_press.current_value = self.saved_hydra_press
                hydra_press.next_value = (
                    self.saved_next_hydra_press
                    if self.saved_next_hydra_press is not None
                    else self.saved_hydra_press
                )
        self.saved_rules = []
        self.saved_hydra_press = None
        self.saved_next_hydra_press = None

class BrakePadWearAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Plaquettes Glacées", "Usure instantanée et perte de coefficient de friction.")
        self.saved_wear_limit = None
        self.saved_next_wear_limit = None
        
    @classmethod
    def generate_test_target(cls):
        return BrakingSystem("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        wear_limit = component.get_observable("wear_limit")
        if wear_limit:
            self.saved_wear_limit = wear_limit.current_value
            self.saved_next_wear_limit = wear_limit.next_value

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        wear_limit = component.get_observable("wear_limit")
        if wear_limit:
            # Je détruis la plaquette
            wear_limit.current_value += 10.0 * dt
            wear_limit.next_value = wear_limit.current_value

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        wear_limit = component.get_observable("wear_limit")
        if wear_limit and self.saved_wear_limit is not None:
            wear_limit.current_value = self.saved_wear_limit
            wear_limit.next_value = (
                self.saved_next_wear_limit
                if self.saved_next_wear_limit is not None
                else self.saved_wear_limit
            )
        self.saved_wear_limit = None
        self.saved_next_wear_limit = None


# --- SUSPENSION ---

class SuspensionSensorFailureAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Capteur Hauteur HS", "Le capteur SCM renvoie 0 Volts (Erreur).")
        self.saved_rules = []
        self.saved_height_v = None
        self.saved_next_height_v = None

    @classmethod
    def generate_test_target(cls):
        return Suspension("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        height_v = component.get_observable("height_v")
        if height_v:
            self.saved_height_v = height_v.current_value
            self.saved_next_height_v = height_v.next_value
            if hasattr(height_v, "evolution_rules"):
                self.saved_rules = height_v.evolution_rules.copy()
                height_v.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        height_v = component.get_observable("height_v")
        if height_v:
            # Je coupe le signal du capteur
            height_v.current_value = 0.0
            height_v.next_value = 0.0

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        height_v = component.get_observable("height_v")
        if height_v and hasattr(height_v, "evolution_rules"):
            height_v.evolution_rules = self.saved_rules.copy()
            if self.saved_height_v is not None:
                height_v.current_value = self.saved_height_v
                height_v.next_value = (
                    self.saved_next_height_v
                    if self.saved_next_height_v is not None
                    else self.saved_height_v
                )
        self.saved_rules = []
        self.saved_height_v = None
        self.saved_next_height_v = None


# --- WHEELS & TIRES ---

class TirePunctureAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Crevaison", "Dégonflage rapide du pneumatique.")
        self.saved_rules = []
        self.saved_tire_press = None
        self.saved_next_tire_press = None

    @classmethod
    def generate_test_target(cls):
        return WheelsTires("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        tire_press = component.get_observable("tire_press")
        if tire_press:
            self.saved_tire_press = tire_press.current_value
            self.saved_next_tire_press = tire_press.next_value
            if hasattr(tire_press, "evolution_rules"):
                self.saved_rules = tire_press.evolution_rules.copy()
                tire_press.evolution_rules.clear()

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        tire_press = component.get_observable("tire_press")
        if tire_press:
            # Je vide le pneu progressivement jusqu'à la pression atmo
            if tire_press.current_value > 1.0:
                tire_press.current_value -= 2.0 * dt
            else:
                tire_press.current_value = 1.0
            tire_press.next_value = tire_press.current_value

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        tire_press = component.get_observable("tire_press")
        if tire_press and hasattr(tire_press, "evolution_rules"):
            tire_press.evolution_rules = self.saved_rules.copy()
            if self.saved_tire_press is not None:
                tire_press.current_value = self.saved_tire_press
                tire_press.next_value = (
                    self.saved_next_tire_press
                    if self.saved_next_tire_press is not None
                    else self.saved_tire_press
                )
        self.saved_rules = []
        self.saved_tire_press = None
        self.saved_next_tire_press = None

class TireOverheatAnomaly(AbstractAnomaly):
    def __init__(self):
        super().__init__("Surchauffe Gomme", "La température de surface explose (Blocage de roue).")
        self.saved_rules = []
        self.saved_surface_temp = None
        self.saved_next_surface_temp = None
        self.saved_tire_press = None
        self.saved_next_tire_press = None
        self.saved_wheel_rpm = None
        self.saved_next_wheel_rpm = None

    @classmethod
    def generate_test_target(cls):
        return WheelsTires("dummy", "Test")

    def inject(self, component: "AbstractComponent") -> None:
        super().inject(component)
        surface_temp = component.get_observable("surface_temp")
        tire_press = component.get_observable("tire_press")
        wheel_rpm = component.get_observable("wheel_rpm")
        if surface_temp:
            self.saved_surface_temp = surface_temp.current_value
            self.saved_next_surface_temp = surface_temp.next_value
            if hasattr(surface_temp, "evolution_rules"):
                self.saved_rules = surface_temp.evolution_rules.copy()
                surface_temp.evolution_rules.clear()
        if tire_press:
            self.saved_tire_press = tire_press.current_value
            self.saved_next_tire_press = tire_press.next_value
        if wheel_rpm:
            self.saved_wheel_rpm = wheel_rpm.current_value
            self.saved_next_wheel_rpm = wheel_rpm.next_value

    def apply(self, component: "AbstractComponent", dt: float) -> None:
        surface_temp = component.get_observable("surface_temp")
        tire_press = component.get_observable("tire_press")
        wheel_rpm = component.get_observable("wheel_rpm")
        if surface_temp:
            # Sur les longs runs, le nominal est deja tres chaud, donc je force bien au-dessus.
            overheated_surface_temp = max(surface_temp.current_value, 900.0)
            surface_temp.current_value = overheated_surface_temp
            surface_temp.next_value = overheated_surface_temp
        if tire_press:
            overheated_tire_press = min(tire_press.current_value, 3.2)
            tire_press.current_value = overheated_tire_press
            tire_press.next_value = overheated_tire_press
        if wheel_rpm:
            dragging_wheel_rpm = wheel_rpm.current_value * 0.88
            wheel_rpm.current_value = dragging_wheel_rpm
            wheel_rpm.next_value = dragging_wheel_rpm

    def resolve(self, component: "AbstractComponent") -> None:
        super().resolve(component)
        surface_temp = component.get_observable("surface_temp")
        tire_press = component.get_observable("tire_press")
        wheel_rpm = component.get_observable("wheel_rpm")
        if surface_temp and hasattr(surface_temp, "evolution_rules"):
            surface_temp.evolution_rules = self.saved_rules.copy()
            if self.saved_surface_temp is not None:
                surface_temp.current_value = self.saved_surface_temp
                surface_temp.next_value = (
                    self.saved_next_surface_temp
                    if self.saved_next_surface_temp is not None
                    else self.saved_surface_temp
                )
        if tire_press and self.saved_tire_press is not None:
            tire_press.current_value = self.saved_tire_press
            tire_press.next_value = (
                self.saved_next_tire_press
                if self.saved_next_tire_press is not None
                else self.saved_tire_press
            )
        if wheel_rpm and self.saved_wheel_rpm is not None:
            wheel_rpm.current_value = self.saved_wheel_rpm
            wheel_rpm.next_value = (
                self.saved_next_wheel_rpm
                if self.saved_next_wheel_rpm is not None
                else self.saved_wheel_rpm
            )
        self.saved_rules = []
        self.saved_surface_temp = None
        self.saved_next_surface_temp = None
        self.saved_tire_press = None
        self.saved_next_tire_press = None
        self.saved_wheel_rpm = None
        self.saved_next_wheel_rpm = None
