from ModelBuilder import ModelBuilder
from core.MessageBus import MessageBus
from core.Sensor import Sensor
from core.AbstractObservable import AbstractObservable
from core.exceptions import NotIdentifierError
from core.AbstractComponent import AbstractComponent
from core.AbstractAnomaly import AbstractAnomaly
from Simulator import Simulator
from typing import Callable
from AnomalyScheduler import AnomalyScheduler

class SimulationController:
    def __init__(self, bus: MessageBus = None):
        if bus is None:
            bus = MessageBus()
        self.simulator = Simulator(bus=bus)
        self.anomaly_scheduler = AnomalyScheduler(self.simulator)
        
    def set_bus(self, bus: MessageBus):
        """
        Méthode servant à définir le bus dans le simulator chargé en mémoire.
        Lève une TypeError si le bus passé n'est pas un MessageBus.
        """
        if not isinstance(bus, MessageBus):
            raise TypeError("Le bus passé au setter de bus de SimulationController n'est pas une instance de MessageBus.")
        self.simulator.bus = bus

    def validate_system_directory(self, path: str) -> dict:
        """
        Utilise un ModelBuilder temporaire pour vérifier et valider un dossier de système.
        Ne sert pas à charger le système, juste à le valider et à renvoyer un rapport de validation.
        Renvoie un dictionnaire représentant le système, de cette forme:
        {
            "components": [
                {
                    "class_name": str,
                    "display_name": str,
                    "linked_observables": [
                        {
                            "name": str,
                            "display_name": str,
                            "class_type": str,
                            "initial_value": float / int (si non défini, 0.0 car le constructeur de AbstractObservable met un warning et une valeur par défaut de 0.0)
                        }
                    ]
                }
            ],
            "anomalies": [
                {
                    "class_name": str,
                    "name": str,
                    "description": str
                }
            ]
            "errors": [
                {
                    "severity": str,      # "FATAL", "ERROR", ou "WARNING"
                    "file": str,          # Chemin du fichier concerné ( ! ou None)
                    "class_name": str,    # Nom de la classe concernée (! ou None)
                    "message": str        # Description détaillée de l'erreur
                }
            ]
        }
        """
        validator = ModelBuilder()
        validator.load_files(path)
        output_dict = {'components': [], 'anomalies': [], 'errors': []}
        
        for component in validator.correct_components:
            linked_observables = []
            for obs in validator.associated_observables.get(component, []):
                linked_observables.append({
                    "name": obs.name,
                    "display_name": getattr(obs, 'display_name', obs.name), # Si display_name n'est pas défini, on utilise le name de l'observable (ne devrait pas arriver)
                    "class_type": obs.__class__.__name__,
                    "initial_value": getattr(obs, 'initial_value', None) # Si jamais initial_value n'est pas défini, on met None (ne devrait pas arriver car AbstractObservable met un warning et une valeur par défaut de 0.0)
                })

            output_dict["components"].append({
                "class_name": component.__name__,
                "display_name": getattr(component, 'display_name', component.__name__), # Si display_name n'est pas défini, on utilise le name de l'observable (ne devrait pas arriver)
                "linked_observables": linked_observables
            })

        for anomaly in validator.correct_anomalies:
            temp_instance = anomaly() # HACK : Sert à charger la description et nom, devra être changé
            output_dict["anomalies"].append({
                "class_name": anomaly.__name__,
                "name": getattr(temp_instance, 'name', anomaly.__name__), # Si name n'est pas défini (normalement n'arrive pas)
                "description": getattr(temp_instance, 'description', "No description")
            })

        for error in validator.errors:
            output_dict["errors"].append({
                "severity": error["severity"],
                "file": error["file"],
                "class_name": error["class_name"],
                "message": error["message"]
            })

        return output_dict 

    def initialize_system(self, path: str, name: str = "systeme_global", display_name: str = "Système Global") -> None:
        """
        Charge un système dans le simulateur courant, et alimente aussi son dictionnaire d'anomalies.
        Doit être fait en amont pour utiliser les autres méthodes.
        Utilise un ModelBuilder temporaire pour instancier le système.
        Lève une exception si le chargement ou l'instanciation échoue.
        """
        # on nettoie car maintenant j'ai un bouton reset simulation
        self.simulator.bus = MessageBus()
        self.simulator.anomaly_dict.clear()
        self.simulator.active_sensors.clear()
        self.simulator.global_time = 0.0
        
        # on vide le scheduler pour éviter que la simulation a les anomalies d'une ancienne
        self.anomaly_scheduler.scheduled_events.clear()

        temp_builder = ModelBuilder()
        temp_builder.load_files(path)
        
        RootClass = temp_builder.system_root
        if RootClass is None:
            raise Exception("Aucun composant racine trouvé, impossible d'initialiser le système.")
        if not name.isidentifier():
            raise NotIdentifierError(f"Le nom {name} ne peut pas être utilisé comme nom de composant.")
        root_instance = RootClass(name=name, display_name=display_name) # Par défaut : name="systeme_global", display_name="Système Global"
        
        # Grâce à load_files(), on est sûr que le temp_builder a une liste d'anomalies en mémoire.
        for anomaly in temp_builder.verified_anomalies:
            if not isinstance(anomaly, AbstractAnomaly): # Devrait vraiment jamais arriver mais bon
                raise TypeError(f"L'anomalie {anomaly} trouvé dans la liste verified_anomalies du ModelBuilder n'hérite pas de AbstractAnomaly")
            self.simulator.add_anomaly_to_dict(anomaly)
        self.simulator.set_system_root(root_instance)

    def update_simulation(self, dt: float) -> float:
        """
        Fais avancer la simulation de dt.
        Dédie la tâche au simulator chargé en mémoire.
        Retourne la valeur de retour de update_simulation() dans le Simulator, qui est donc le temps global de la simulation.
        """
        if not self._system_is_loaded():
            raise Exception("Le système doit être chargé avant d'appeler cette méthode. Utiliser initialize_system() dans le SimulationController au préalable.")
        
        self.anomaly_scheduler.update() # Gère les anomalies AVANT de faire avancer la simulation, sinon l'anomalie aurait un pas de retard
        current_time = self.simulator.update_simulation(dt)
        return current_time

    def add_sensor_and_subscribe(self, component_name: str, observable_name: str, interval: float, callback: Callable) -> Sensor:
        """
        Ajoute un capteur sur un observable et abonne un callback directement à son channel dans le bus.
        """
        if not self._system_is_loaded():
            raise Exception("Le système doit être chargé avant d'appeler cette méthode. Utiliser initialize_system() dans le SimulationController au préalable.")
        
        observable = self._get_observable_in_system(component_name, observable_name)
        channel_name = self._return_channel_name_for_observable(component_name, observable_name)
        
        sensor = self._add_sensor(observable, interval, channel_name)
        self._subscribe_callback_to_given_channel(channel_name, callback)
        
        return sensor
    
    def load_anomaly_file(self, file_path: str) -> bool:
        """
        Charge un fichier de planification d'anomalies dans l'AnomalyScheduler.
        Retourne True si le chargement a réussi, False sinon (fichier invalide).
        Délègue la tâche à l'AnomalyScheduler, qui gère lui-même la validation et 
        le chargement du fichier.
        """
        return self.anomaly_scheduler.load_schedule(file_path)
    
    def inject_anomaly(self, anomaly_name: str, component_name: str):
        """
        Injecte une anomalie dans la simulation.
        Pour trouver les instances liées aux noms, appelle des méthodes dédiés.
        """
        if not self._system_is_loaded():
            raise Exception("Le système doit être chargé avant d'appeler cette méthode. Utiliser initialize_system() dans le SimulationController au préalable.")

        # Ces deux méthodes provoquent des erreurs si elles ne trouvent pas
        anomaly_instance = self._find_anomaly(anomaly_name) 
        component_instance = self._get_component_in_system(component_name)

        self.simulator.inject_anomaly(anomaly=anomaly_instance, component=component_instance)
        
    def resolve_anomaly(self, anomaly_name: str, component_name: str):
        """
        Résout une anomalie dans la simulation.
        Pour trouver les instances liées aux noms, appelle des méthodes dédiés.
        """
        if not self._system_is_loaded():
            raise Exception("Le système doit être chargé avant d'appeler cette méthode. Utiliser initialize_system() dans le SimulationController au préalable.")

        # Ces deux méthodes provoquent des erreurs si elles ne trouvent pas
        anomaly_instance = self._find_anomaly(anomaly_name) 
        component_instance = self._get_component_in_system(component_name)

        self.simulator.resolve_anomaly(anomaly=anomaly_instance, component=component_instance)

    def subscribe_callback_to_observable_channel(self, component_name: str, observable_name: str, callback: Callable):
        """
        Permet de s'abonner à un channel du bus de message lié à un observable spécifique, pour recevoir les données publiées dessus.
        La méthode se charge de trouver un nom de channel fiable et sans collision pour l'observable ciblé.
        Le callback doit être une fonction qui prend un argument (la donnée publiée).
        Délègue la tâche à une méthode protégée.
        """
        channel_name = self._return_channel_name_for_observable(component_name, observable_name)
        self._subscribe_callback_to_given_channel(channel_name, callback)

    def _get_simulator(self) -> Simulator:
        """Getter de simulator."""
        return self.simulator

    def _system_is_loaded(self) -> bool:
        """Renvoie True si un système est chargé, False sinon."""
        if self.simulator.system_root:
            return True
        return False

    def _add_sensor(self, target_observable: AbstractObservable, interval: float, channel_name: str) -> Sensor:
        """
        Ajoute un capteur au simulateur.
        Utilise la méthode add_sensor() du simulateur pour gérer la logique.
        """
        if not self._system_is_loaded():
            raise Exception("Le système doit être chargé avant d'appeler cette méthode. Utiliser initialize_system() dans le SimulationController au préalable.")
        return self.simulator.add_sensor(target_observable, interval, channel_name)
    
    def _return_channel_name_for_observable(self, component_name: str, observable_name: str) -> str:
        """
        Retourne le nom de channel à utiliser pour un observable donné, en fonction de son arborescence complète.

        Le format de channel_name utilisé dans les capteurs est "root_component_name/.../parent_component_name/component_name/observable_name".
        Cette méthode est un simple utilitaire pour construire ce nom de channel de manière fiable, en évitant les 
        collisions de noms.

        Il est nécessaire d'utiliser les noms en string, car un observable ne peut pas connaitre le composant auquel il appartient, 
        il faut donc chercher ça à la volée.
        
        Lève une Exception si le système n'est pas chargé, et une ValueError si l'observable ou le composant n'est pas trouvé dans le système.
        """
        if not self._system_is_loaded():
            raise Exception("Le système doit être chargé avant d'appeler cette méthode. Utiliser initialize_system() dans le SimulationController au préalable.")
        
        observable_instance = self._get_observable_in_system(component_name, observable_name)
        component_instance = self._get_component_in_system(component_name)
        if not observable_instance:
            raise ValueError(f"Observable '{observable_name}' dans le composant '{component_name}' n'a pas été trouvé dans le système.")
        if not component_instance:
            raise ValueError(f"Composant '{component_name}' n'a pas été trouvé dans le système.")

        # On construit le channel name en remontant l'arborescence des composants à partir de l'observable
        channel_parts = [observable_instance.name]
        current = component_instance
        while current:
            channel_parts.insert(0, current.name) # On ajoute le nom du composant parent au début de la liste
            current = current.parent
        return "/".join(channel_parts)

    def _get_component_in_system(self, component_name: str) -> AbstractComponent:
        """
        Retourne le composant de nom component_name, si il existe.
        Lève une Exception si le système n'est pas chargé, et une ValueError si le composant n'est pas trouvé dans le système.
        Utilise la méthode get_component_in_system() du simulateur pour gérer la logique.
        """
        if not self._system_is_loaded():
            raise Exception("Le système doit être chargé avant d'appeler cette méthode. Utiliser initialize_system() dans le SimulationController au préalable.")
        return self.simulator.get_component_in_system(component_name)

    def _get_observable_in_system(self, component_name: str, observable_name: str) -> AbstractObservable:
        """
        Retourne l'observable observable_name dans component_name, si il existe.
        Lève une Exception si le système n'est pas chargé, et une ValueError si l'observable ou le composant n'est pas trouvé dans le système.
        Utilise la méthode get_observable_in_system() du simulateur pour gérer la logique.
        """
        if not self._system_is_loaded():
            raise Exception("Le système doit être chargé avant d'appeler cette méthode. Utiliser initialize_system() dans le SimulationController au préalable.")
        return self.simulator.get_observable_in_system(component_name, observable_name)

    def _find_anomaly(self, anomaly_name: str) -> AbstractAnomaly:
        """Retourne l'anomalie à partir de son nom, en déléguant la tâche au simulateur."""
        if not self._system_is_loaded():
            raise Exception("Le système doit être chargé avant d'appeler cette méthode. Utiliser initialize_system() dans le SimulationController au préalable.")
        return self.simulator.find_anomaly(anomaly_name)

    def _subscribe_callback_to_given_channel(self, channel_name: str, callback: Callable):
        """
        Permet de s'abonner à un channel du bus de message pour recevoir les données publiées dessus.
        Cette méthode est protégée car elle suppose que le channel_name donné est déjà vérifié et fiable (ex: via return_channel_name_for_observable).
        Il est préférable d'utiliser la méthode publique subscribe_callback_to_channel_of_observable.
        Le callback doit être une fonction qui prend un argument (la donnée publiée).
        Délègue la tâche au simulateur.
        """
        if not self._system_is_loaded():
            raise Exception("Le système doit être chargé avant d'appeler cette méthode. Utiliser initialize_system() dans le SimulationController au préalable.")
        if not isinstance(channel_name, str):
            raise TypeError("Le nom du channel doit être une chaîne de caractères.")
        if not callable(callback):
            raise TypeError("Le callback doit être une fonction ou une méthode callable.")
        self.simulator.subscribe_callback_to_channel(channel_name, callback)