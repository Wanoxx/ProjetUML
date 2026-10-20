import math
import random
from core.AbstractComponent import AbstractComponent
from test_models.ferrari.BatteryStarter import BatteryStarter
from test_models.ferrari.EngineV12 import EngineV12
from test_models.ferrari.AirIntake import AirIntake
from test_models.ferrari.ThermalManagement import ThermalManagement
from test_models.ferrari.ExhaustLine import ExhaustLine
from test_models.ferrari.TorqueTube import TorqueTube
from test_models.ferrari.Gearbox import Gearbox
from test_models.ferrari.EDiff import EDiff
from test_models.ferrari.BrakingSystem import BrakingSystem
from test_models.ferrari.Suspension import Suspension
from test_models.ferrari.WheelsTires import WheelsTires

class Ferrari812(AbstractComponent):
    """Classe racine qui orchestre la physique et les interactions de tous les sous-composants de la Ferrari 812."""
    is_root = True

    def __init__(self, name: str, display_name: str = "Ferrari 812 Superfast"):
        super().__init__(name, display_name)
        
        # on initialise les etats de base du pilote automatique
        self.drive_mode = "CITY" 
        self.mode_timer = 10.0 
        self.target_speed_kmh = 0.0
        self.base_speed = 45.0 
        
        # on setup les constantes physiques et aerodynamiques du vehicule
        self.AIR_DENSITY = 1.225
        self.FRONTAL_AREA = 2.1
        self.DRAG_COEFF = 0.33
        self.AMBIENT_TEMP = 20.0

    def setup(self):
        """Instancie les modules physiques et definit toutes les regles d'evolution croisees basees sur la mecanique classique."""
        
        # on rattache tous les sous-systemes au composant principal
        self.add_child(BatteryStarter("battery", "Electrical System"))
        self.add_child(AirIntake("intake", "Air Intake"))
        self.add_child(EngineV12("engine", "V12 Engine"))
        self.add_child(ThermalManagement("cooling", "Cooling System"))
        self.add_child(ExhaustLine("exhaust", "Exhaust Line"))
        self.add_child(TorqueTube("transmission", "Torque Tube"))
        self.add_child(Gearbox("gearbox", "DCT Gearbox"))
        self.add_child(EDiff("differential", "Electronic Diff"))
        self.add_child(BrakingSystem("brakes", "Carbon Brakes"))
        self.add_child(Suspension("suspension", "SCM Suspension"))
        self.add_child(WheelsTires("wheels", "Wheels & Tires"))

        # sous-systeme: EngineV12
        
        # on definit la logique de calcul du rpm moteur basee sur l'inertie rotatoire
        def engine_logic(curr_rpm, dt, starter_rpm, throttle_pos):
            if curr_rpm > 500.0:
                wheel_rpm = self.wheels.wheel_rpm.get_value()
                gear = self.gearbox.gear.get_value()
                gear_ratio = max(0.7, 3.5 - (gear * 0.4))
                
                # cinematique des solides: on lie le regime moteur a la vitesse des roues via les ratios de transmission
                mech_rpm = wheel_rpm * 3.53 * gear_ratio
                
                target_rpm = mech_rpm + (throttle_pos * 30.0)
                target_rpm = max(800.0, min(target_rpm, 8900.0)) 
            elif starter_rpm > 50.0:
                target_rpm = starter_rpm
            else:
                target_rpm = 0.0
                
            # reponse de systeme du premier ordre pour simuler l'inertie mecanique
            return (target_rpm - curr_rpm) * (1.0 - math.exp(-4.0 * dt))
            
        self.engine.rpm.add_evolution_rule(engine_logic, [self.battery.starter_rpm, self.intake.throttle_pos])

        #sous-systeme: BrakingSystem ---

        # dynamique de la pedale de frein
        def brake_pedal_logic(curr_pos, dt):
            actual_speed = (self.wheels.wheel_rpm.get_value() * 60.0 * 2.2) / 1000.0
            error = self.target_speed_kmh - actual_speed
            
            if error < -3.0:
                target_pos = min(100.0, abs(error) * 1.0)
            else:
                target_pos = 0.0
                
            return (target_pos - curr_pos) * (1.0 - math.exp(-5.0 * dt))
            
        self.brakes.pedal_pos.add_evolution_rule(brake_pedal_logic, [])

        # sous-systeme: ThermalManagement
        
        def pump_logic(curr_rpm, dt, engine_rpm):
            # cinematique simple ou la pompe est entrainee par la courroie
            return (engine_rpm - curr_rpm) * (1.0 - math.exp(-5.0 * dt))
            
        self.cooling.pump_rpm.add_evolution_rule(pump_logic, [self.engine.rpm])

        def coolant_logic(curr_temp, dt, oil_temp, pump_rpm, wheel_rpm, fan_rpm):
            # loi de fourier pour la conduction thermique entre l'huile et le liquide
            exchange = (oil_temp - curr_temp) * (pump_rpm / 9000.0) * 1.5 * dt
            
            thermostat = max(0.0, min(1.0, (curr_temp - 85.0) / 10.0))
            
            speed_kmh = (wheel_rpm * 60.0 * 2.2) / 1000.0
            ram_air_effect = speed_kmh * 0.05 
            fan_effect = (fan_rpm / 3000.0) * 3.0
            
            total_cooling_power = (ram_air_effect + fan_effect) * thermostat
            
            # loi de refroidissement de newton pour la dissipation de la chaleur du radiateur vers l'air
            radiator_dissipation = (curr_temp - self.AMBIENT_TEMP) * (1.0 - math.exp(-total_cooling_power * dt))
            
            # principe de conservation de l'energie (premier principe de la thermodynamique)
            return exchange - radiator_dissipation
            
        self.cooling.temp_out.add_evolution_rule(coolant_logic, [
            self.engine.oil_temp, 
            self.cooling.pump_rpm, 
            self.wheels.wheel_rpm, 
            self.cooling.fan_rpm
        ])

        # sous-systeme: EngineV12

        def thermal_logic(curr_temp, dt, rpm, coolant_temp):
            # thermodynamique classique: accumulation de chaleur liée a la friction mecanique
            heat_gain = (10.0 + (rpm / 8000.0) * 40.0) * dt
            cooling_effect = (coolant_temp - curr_temp) * 1.5 * dt
            return heat_gain + cooling_effect
            
        self.engine.oil_temp.add_evolution_rule(thermal_logic, [self.engine.rpm, self.cooling.temp_out])

        # sous-systeme: BrakingSystem
        
        def brake_heat_logic(curr_temp, dt, pedal, wheel_rpm):
            speed_ms = (wheel_rpm * 2.2) / 60.0
            
            # theoreme de l'energie cinetique ou le travail de la force de frottement se transforme en chaleur
            friction_work = (pedal / 100.0) * (speed_ms**2) * 0.05 * dt
            
            # loi de newton pour la dissipation thermique dans l'air ambiant
            cooling = (curr_temp - self.AMBIENT_TEMP) * (1.0 - math.exp(-0.05 * dt))
            return friction_work - cooling
            
        self.brakes.disc_temp.add_evolution_rule(brake_heat_logic, [self.brakes.pedal_pos, self.wheels.wheel_rpm])

        # ous-systeme: TorqueTube
        
        def shaft_resonance_logic(curr_res, dt, rpm):
            # mecanique vibratoire pour simuler la frequence de resonance de l'arbre
            critical_freq = 7000.0
            dist = abs(rpm - critical_freq)
            target_res = 100.0 / (dist + 1.0) 
            return (target_res - curr_res) * 0.2 * dt
            
        self.transmission.resonance.add_evolution_rule(shaft_resonance_logic, [self.engine.rpm])

        # sous-systeme: WheelsTires

        def tire_pressure_logic(curr_press, dt, surface_temp):
            # loi de gay-lussac sur les gaz parfaits ou la pression est proportionnelle a la temperature
            temp_kelvin = surface_temp + 273.15
            target_press = 2.4 * (temp_kelvin / 293.15)
            return (target_press - curr_press) * dt
            
        self.wheels.tire_press.add_evolution_rule(tire_pressure_logic, [self.wheels.surface_temp])

        # sous-systeme: BatteryStarter

        def relay_rule(curr_state, dt):
            target = 1.0 if self.target_speed_kmh > 0 else 0.0
            return (target - curr_state) * 10.0 * dt
            
        self.battery.relay_state.add_evolution_rule(relay_rule, [])

        def current_rule(curr_amps, dt, relay, engine_rpm):
            # on simule le pic d'amperage necessaire pour vaincre l'inertie du vilebrequin
            if relay > 0.5 and engine_rpm < 500:
                target_amps = 300.0 
            elif relay > 0.5:
                target_amps = 25.0 
            else:
                target_amps = 0.0
            return (target_amps - curr_amps) * 5.0 * dt
            
        self.battery.current.add_evolution_rule(current_rule, [self.battery.relay_state, self.engine.rpm])

        def voltage_rule(curr_v, dt, engine_rpm, amps):
            if engine_rpm < 500:
                # loi d'ohm appliquee a la resistance interne de la batterie provoquant une chute de tension
                target_v = 12.6 - (amps * 0.005) 
            else:
                target_v = 14.4 
            return (target_v - curr_v) * (1.0 - math.exp(-2.0 * dt))
            
        self.battery.voltage.add_evolution_rule(voltage_rule, [self.engine.rpm, self.battery.current])

        def starter_rule(curr_rpm, dt, amps, engine_rpm):
            if engine_rpm < 500:
                target_rpm = amps * 2.5 
            else:
                target_rpm = 0.0
            return (target_rpm - curr_rpm) * 8.0 * dt
            
        self.battery.starter_rpm.add_evolution_rule(starter_rule, [self.battery.current, self.engine.rpm])

        # sous-systeme: AirIntake

        def throttle_logic(curr_pos, dt, brake_pedal):
            actual_speed = (self.wheels.wheel_rpm.get_value() * 60.0 * 2.2) / 1000.0
            error = self.target_speed_kmh - actual_speed
            
            # theorie du controle: on utilise un correcteur integral pour annuler l'erreur statique
            if brake_pedal > 2.0 or self.target_speed_kmh < 1.0:
                target_pos = 0.0
            else:
                target_pos = curr_pos + (error * 1.5 * dt)
                
            target_pos = max(0.0, min(100.0, target_pos))
            return target_pos - curr_pos
            
        self.intake.throttle_pos.add_evolution_rule(throttle_logic, [self.brakes.pedal_pos])
            
        def airflow_logic(curr_flow, dt, rpm, throttle):
            # mecanique des fluides et rendement volumetrique du cylindre
            target_flow = (rpm / 8500.0) * (throttle / 100.0) * 600.0
            return (target_flow - curr_flow) * (1.0 - math.exp(-10.0 * dt))
            
        self.intake.airflow.add_evolution_rule(airflow_logic, [self.engine.rpm, self.intake.throttle_pos])

        # sous-systeme: ExhaustLine

        def cat_temp_logic(curr_temp, dt, airflow):
            target_temp = 20.0 + (airflow * 1.5) 
            return (target_temp - curr_temp) * (1.0 - math.exp(-0.05 * dt))
            
        self.exhaust.cat_temp.add_evolution_rule(cat_temp_logic, [self.intake.airflow])

        def exhaust_valve_logic(curr_pos, dt, rpm):
            target_pos = 100.0 if rpm > 4000.0 else 0.0
            return (target_pos - curr_pos) * (1.0 - math.exp(-5.0 * dt))
            
        self.exhaust.valve_pos.add_evolution_rule(exhaust_valve_logic, [self.engine.rpm])

        # sous-systeme: TorqueTube

        def shaft_logic(curr_rpm, dt, engine_rpm):
            # theorie des mecanismes: liaison encastrement parfaite sans glissement
            return engine_rpm - curr_rpm
            
        self.transmission.shaft_rpm.add_evolution_rule(shaft_logic, [self.engine.rpm])

        # sous-systeme: Gearbox

        def gear_logic(curr_gear, dt, wheel_rpm):
            speed_kmh = (wheel_rpm * 60.0 * 2.2) / 1000.0
            
            if speed_kmh < 15.0: target_gear = 1.0
            elif speed_kmh < 30.0: target_gear = 2.0
            elif speed_kmh < 45.0: target_gear = 3.0
            elif speed_kmh < 65.0: target_gear = 4.0
            elif speed_kmh < 90.0: target_gear = 5.0
            elif speed_kmh < 115.0: target_gear = 6.0
            else: target_gear = 7.0
            
            return (target_gear - curr_gear) * (1.0 - math.exp(-8.0 * dt))
            
        self.gearbox.gear.add_evolution_rule(gear_logic, [self.wheels.wheel_rpm])

        def primary_rpm_logic(curr_rpm, dt, shaft_rpm):
            return shaft_rpm - curr_rpm
            
        self.gearbox.primary_rpm.add_evolution_rule(primary_rpm_logic, [self.transmission.shaft_rpm])

        def secondary_rpm_logic(curr_rpm, dt, primary_rpm, gear):
            # cinematique des engrenages via la raison de train d'engrenage
            ratio = max(0.7, 3.5 - (gear * 0.4)) 
            target_rpm = primary_rpm / ratio
            return target_rpm - curr_rpm
            
        self.gearbox.secondary_rpm.add_evolution_rule(secondary_rpm_logic, [self.gearbox.primary_rpm, self.gearbox.gear])

        # sous-systeme: EDiff

        def diff_rpm_logic(curr_rpm, dt, secondary_rpm):
            # reduction finale via le rapport de pont
            final_drive = 3.53
            target_rpm = secondary_rpm / final_drive
            return target_rpm - curr_rpm
            
        self.differential.rpm_left.add_evolution_rule(diff_rpm_logic, [self.gearbox.secondary_rpm])
        self.differential.rpm_right.add_evolution_rule(diff_rpm_logic, [self.gearbox.secondary_rpm])

        # sous-systeme: WheelsTires

        def wheel_rpm_logic(curr_rpm, dt, diff_rpm, hydra_press):
            speed_kmh = (curr_rpm * 60.0 * 2.2) / 1000.0
            
            # dynamique des fluides: theoreme de bernoulli pour calculer la trainee aerodynamique (force quadratique)
            aero_drag_factor = (speed_kmh / 340.0)**2
            target_driven_rpm = diff_rpm * (1.0 - min(1.0, aero_drag_factor * 0.2))
            
            delta_rpm = (target_driven_rpm - curr_rpm) * (1.0 - math.exp(-2.0 * dt))
            
            max_accel = 300.0 * dt
            delta_rpm = max(-max_accel, min(max_accel, delta_rpm))
            
            brake_decel = (hydra_press * 15.0) * dt
            return (curr_rpm + delta_rpm - brake_decel) - curr_rpm
            
        self.wheels.wheel_rpm.add_evolution_rule(wheel_rpm_logic, [self.differential.rpm_left, self.brakes.hydra_press])

        def tire_temp_logic(curr_temp, dt, wheel_rpm):
            speed_kmh = (wheel_rpm * 60.0 * 2.2) / 1000.0 
            
            # thermodynamique des frottements solides
            heat_gen = speed_kmh * 0.05 * dt
            cooling = (curr_temp - self.AMBIENT_TEMP) * (1.0 - math.exp(-0.01 * dt))
            return heat_gen - cooling
            
        self.wheels.surface_temp.add_evolution_rule(tire_temp_logic, [self.wheels.wheel_rpm])

        # sous-systeme: Suspension

        def suspension_logic(curr_curr, dt, wheel_rpm):
            # theorie de l'electromagnetisme: controle de la viscosite via le fluide magnetorheologique
            speed_kmh = (wheel_rpm * 60.0 * 2.2) / 1000.0
            
            if self.drive_mode == "TRACK":
                target_curr = 2.5 
            elif speed_kmh > 100.0:
                target_curr = 1.5 
            else:
                target_curr = 0.5 
                
            return (target_curr - curr_curr) * (1.0 - math.exp(-2.0 * dt))
            
        self.suspension.coil_curr.add_evolution_rule(suspension_logic, [self.wheels.wheel_rpm])

        # sous-systeme: EDiff

        def ediff_actuator_logic(curr_curr, dt, throttle):
            target_curr = (throttle / 100.0) * 5.0 
            return (target_curr - curr_curr) * (1.0 - math.exp(-10.0 * dt))
            
        self.differential.actuator_curr.add_evolution_rule(ediff_actuator_logic, [self.intake.throttle_pos])

        def diff_temp_logic(curr_temp, dt, wheel_rpm):
            heat_gen = (wheel_rpm / 1000.0) * 0.5 * dt
            cooling = (curr_temp - self.AMBIENT_TEMP) * (1.0 - math.exp(-0.05 * dt))
            return heat_gen - cooling
            
        self.differential.internal_temp.add_evolution_rule(diff_temp_logic, [self.wheels.wheel_rpm])

        # sous-systeme : WheelsTires

        def long_accel_logic(curr_g, dt, wheel_rpm):
            speed_ms = (wheel_rpm * 2.2) / 60.0 
            
            if not hasattr(long_accel_logic, "last_speed"):
                long_accel_logic.last_speed = speed_ms
                
            # deuxieme loi de newton (principe fondamental de la dynamique) ou a = dv/dt
            accel_ms2 = (speed_ms - long_accel_logic.last_speed) / dt
            long_accel_logic.last_speed = speed_ms
            
            target_g = accel_ms2 / 9.81
            
            return (target_g - curr_g) * (1.0 - math.exp(-10.0 * dt))
            
        self.wheels.long_accel.add_evolution_rule(long_accel_logic, [self.wheels.wheel_rpm])
        
        def lat_accel_logic(curr_g, dt, wheel_rpm):
            speed_kmh = (wheel_rpm * 60.0 * 2.2) / 1000.0
            target_g = 0.0
            
            if self.drive_mode == "TRACK" and speed_kmh > 80.0:
                target_g = random.uniform(-1.5, 1.5)
            elif speed_kmh > 40.0 and random.random() < 0.05:
                target_g = random.uniform(-0.3, 0.3)
                
            return (target_g - curr_g) * (1.0 - math.exp(-5.0 * dt))
            
        self.wheels.lat_accel.add_evolution_rule(lat_accel_logic, [self.wheels.wheel_rpm])

        # sous- systeme: Gearbox

        def clutch_odd_logic(curr_press, dt, gear):
            target = 100.0 if round(gear) % 2 != 0 else 0.0
            return (target - curr_press) * (1.0 - math.exp(-15.0 * dt))
            
        self.gearbox.clutch_odd_press.add_evolution_rule(clutch_odd_logic, [self.gearbox.gear])

        def clutch_even_logic(curr_press, dt, gear):
            target = 100.0 if round(gear) % 2 == 0 else 0.0
            return (target - curr_press) * (1.0 - math.exp(-15.0 * dt))
            
        self.gearbox.clutch_even_press.add_evolution_rule(clutch_even_logic, [self.gearbox.gear])

        # sous-systeme: ExhaustLine

        def lambda_logic(curr_lambda, dt, throttle):
            # chimie de combustion: on module la richesse (ratio air carburant stoechiometrique)
            if throttle > 80.0: target_lambda = 0.85
            elif throttle > 5.0: target_lambda = 1.0
            else: target_lambda = 1.2
            return (target_lambda - curr_lambda) * (1.0 - math.exp(-5.0 * dt))
            
        self.exhaust.lambda_v.add_evolution_rule(lambda_logic, [self.intake.throttle_pos])

        # sous-systeme: ThermalManagement

        def circuit_press_logic(curr_press, dt, temp_out):
            # thermodynamique: dilatation isobare du fluide avec la chaleur
            target_press = 1.0 + max(0.0, (temp_out - 20.0) * 0.015)
            return (target_press - curr_press) * (1.0 - math.exp(-0.5 * dt))
            
        self.cooling.circuit_press.add_evolution_rule(circuit_press_logic, [self.cooling.temp_out])

        def temp_in_logic(curr_temp, dt, temp_out, wheel_rpm, fan_rpm):
            speed_kmh = (wheel_rpm * 60.0 * 2.2) / 1000.0
            cooling_drop = (speed_kmh * 0.05) + (fan_rpm / 3000.0 * 10.0)
            target_temp = max(self.AMBIENT_TEMP, temp_out - cooling_drop)
            return (target_temp - curr_temp) * (1.0 - math.exp(-1.0 * dt))
            
        self.cooling.temp_in.add_evolution_rule(temp_in_logic, [self.cooling.temp_out, self.wheels.wheel_rpm, self.cooling.fan_rpm])

        # sous-systeme: AirIntake

        def air_temp_logic(curr_temp, dt, oil_temp, wheel_rpm):
            speed_kmh = (wheel_rpm * 60.0 * 2.2) / 1000.0
            
            # transfert thermique par rayonnement du bloc moteur vers l'admission
            heat_soak = max(0.0, (oil_temp - 50.0) * 0.15)
            air_flow_cooling = min(1.0, speed_kmh / 50.0) 
            target_temp = self.AMBIENT_TEMP + (heat_soak * (1.0 - air_flow_cooling))
            return (target_temp - curr_temp) * (1.0 - math.exp(-0.5 * dt))
            
        self.intake.air_temp.add_evolution_rule(air_temp_logic, [self.engine.oil_temp, self.wheels.wheel_rpm])

    def before_update(self, dt: float) -> None:
        """Surcharge du hook d'update pour inclure la logique de variation de vitesse du pilote."""
        super().before_update(dt)
        
        self.mode_timer -= dt 

        if self.mode_timer <= 0:
            self._transition_logic()

        if self.drive_mode == "CITY":
            if random.random() < 0.005: 
                self.base_speed = 0.0
            elif self.base_speed < 10.0 and random.random() < 0.02: 
                self.base_speed = 45.0
                
        elif self.drive_mode == "NATIONAL":
            if random.random() < 0.01:
                self.base_speed = random.choice([70.0, 80.0, 90.0])
                
        elif self.drive_mode == "TRACK":
            if random.random() < 0.02:
                self.base_speed = random.uniform(150.0, 240.0)
            else:
                self.base_speed = 340.0

        # reponse de systeme du premier ordre (filtre passe-bas) pour lisser l'acceleration cible
        alpha = 1.0 - math.exp(-0.2 * dt)
        self.target_speed_kmh += (self.base_speed - self.target_speed_kmh) * alpha

    def _transition_logic(self):
        """Methode probabiliste qui gere les changements de contexte environnemental du pilote."""
        
        if self.drive_mode == "STOP": 
            self.drive_mode = "CITY"
            self.mode_timer = random.uniform(20.0, 40.0)
            self.base_speed = 45.0
            
        elif self.drive_mode == "CITY":
            self.drive_mode = random.choices(["CITY", "NATIONAL"], weights=[0.3, 0.7])[0]
            self.mode_timer = random.uniform(60.0, 120.0) 
            self.base_speed = 80.0 if self.drive_mode == "NATIONAL" else 45.0
            
        elif self.drive_mode == "NATIONAL":
            self.drive_mode = random.choices(["CITY", "HIGHWAY"], weights=[0.2, 0.8])[0]
            self.mode_timer = random.uniform(90.0, 180.0) 
            self.base_speed = 130.0 if self.drive_mode == "HIGHWAY" else 45.0
            
        elif self.drive_mode == "HIGHWAY":
            self.drive_mode = "NATIONAL"
            self.mode_timer = random.uniform(60.0, 120.0)
            self.base_speed = 80.0
            
        else: 
            self.drive_mode = "CITY"
            self.mode_timer = random.uniform(30.0, 60.0)
            self.base_speed = 45.0