from core.AbstractComponent import AbstractComponent
from core.Sensor import Sensor
from core.AbstractObservable import AbstractObservable
from core.AbstractAnomaly import AbstractAnomaly
from core.MessageBus import MessageBus
from typing import Callable

class Simulator:
    def __init__(self, system_root: AbstractComponent = None, bus: MessageBus = None) -> None:
        # Ces vérifications ne seront (je pense) jamais utiles en pratique car le SimulationController
        # utilise le constructeur de Simulator seulement pour avoir une instance de Simulator vide.
        # Au cas où, je garde le fait qu'on puisse définir ces champs pendant la construction,
        # mais je ne pense pas que ça servira à quelque chose, à part pour des tests unitaires par exemple.
        if system_root and not isinstance(system_root, AbstractComponent):
            raise TypeError("La racine du système passé vers le constructeur de Simulator doit hériter de AbstractComponent.")
        if bus and not isinstance(bus, MessageBus):
            raise TypeError("Le bus passé vers le constructeur de Simulator doit être un MessageBus instancié.")
        
        self.system_root = system_root
        self.bus = bus
        self.active_sensors = []
        self.global_time = 0
        self.anomaly_dict = {} # Clé = anomaly.__class__.__name__, valeur = instance héritée de AbstractAnomaly

    def set_system_root(self, root: AbstractComponent) -> None:
        """
        Setter de system_root. 
        Lève une TypeError si la racine passée n'hérite pas de AbstractComponent.
        """
        if not isinstance(root, AbstractComponent):
            raise TypeError("La racine donnée au setter n'hérite pas d'AbstractComponent.")
        
        self.system_root = root

    def set_bus(self, bus: MessageBus) -> None:
        """
        Setter de bus. 
        Lève une TypeError si le bus passé n'est pas un MessageBus.
        """
        if not isinstance(bus, MessageBus):
            raise TypeError("Le bus passé au setter n'est pas un MessageBus.")
        
        self.bus = bus

    def add_anomaly_to_dict(self, anomaly_instance: AbstractAnomaly):
        """Ajoute de façon autonome une anomalie au dictionnaire, en gérant la clé et la valeur lui-même."""
        if not isinstance(anomaly_instance, AbstractAnomaly):
            raise TypeError("anomaly_instance doit hériter de AbstractAnomaly.")
        if anomaly_instance.__class__.__name__ in self.anomaly_dict.keys():
            raise Exception(f"L'anomalie {anomaly_instance.__class__.__name__} est déjà présente dans le dictionnaire.")
        
        self.anomaly_dict[anomaly_instance.__class__.__name__] = anomaly_instance
    
    def update_simulation(self, dt: float) -> float:
        """
        Met à jour le système en appelant update sur la racine, mets à jour les
        capteurs puis incrémente la variable global_time.
        Retourne la valeur du temps global dans la simulation.
        """
        if not self.system_root or not isinstance(self.system_root, AbstractComponent):
            raise Exception("Le système ne peut pas être mis à jour, car la racine du système n'est pas disponible ou n'est pas un AbstractComponent.")
        # Je ne pense pas que la vérification du bus soit nécessaire, parce que si l'utilisateur rajoute un capteur, 
        # alors il y aura cette vérification faite lors de l'appel de add_sensor, et en soi on pourrait lancer une 
        # simulation sans capteur, et également sans bus pour simplement vérifier que tout marche bien.
        #if not self.bus or not isinstance(self.bus, MessageBus):
        #    raise Exception("Le système ne peut pas être mis à jour, car le bus n'est pas disponible ou n'est pas un MessageBus.")

        # on incrémente le temps global avant de faire les updates
        self.global_time += dt

        self.system_root.update(dt) # Va mettre à jour récursivement le système
        # Les capteurs ne sont mis à jour que après (ils ne font pas partie du système en tant que tel)
        for sensor in self.active_sensors:
            sensor.update(dt)

        return self.global_time

    def add_sensor(self, target_observable: AbstractObservable, interval: float, channel_name: str) -> Sensor:
        """
        Ajoute un capteur à la simulation pour lire régulièrement une valeur et
        la publier sur le MessageBus via ce nom de channel.
        Le bus utilisé sera celui passé lors de la construction du Simulator courant.
        Lève une Exception si le bus n'est pas défini.
        Retourne le capteur qui vient d'être ajouté.
        """
        if not self.bus:
            raise Exception("Le bus qui sera utilisé par le capteur n'est pas défini.")
        # Les autres erreurs de type sont prises en compte autre part (setter de bus et constructeur de Sensor)
             
        sensor = Sensor(target_observable, self.bus, interval, channel_name)
        self.active_sensors.append(sensor)
        return sensor

    def get_component_in_system(self, component_name: str):
        """Recherche récursivement un composant par son nom, à partir de la racine."""
        if not self.system_root:
            raise Exception(f"Impossible de trouver le composant {component_name} car la racine du système n'est pas disponible.")
            
        components_to_check = [self.system_root]
        while components_to_check:
            current_component = components_to_check.pop(0) # On traite le premier composant de la liste
            if current_component.name == component_name:
                return current_component
            components_to_check.extend(current_component.get_children())

        raise ValueError(f"Composant '{component_name}' introuvable.")

    def get_observable_in_system(self, component_name: str, observable_name: str) -> AbstractObservable:
        """Recherche récursivement un observable par son nom dans un composant ciblé par son nom, à partir de la racine."""
        if not self.system_root:
            raise Exception(f"Impossible de trouver l'observable {observable_name} dans {component_name} car la racine du système n'est pas disponible.")
            
        components_to_check = [self.system_root]
        while components_to_check:
            current_component = components_to_check.pop(0) # On traite le premier composant de la liste
            if current_component.name == component_name:
                observable = current_component.get_observable(observable_name)
                if observable is not None:
                    return observable
                else:
                    raise ValueError(f"Observable '{observable_name}' introuvable dans le composant '{component_name}'.")
            components_to_check.extend(current_component.get_children())

        raise ValueError(f"Composant '{component_name}' introuvable.")

    def find_anomaly(self, anomaly_name: str) -> AbstractAnomaly:
        """
        Retrouve l'anomalie via soit son nom de classe, soit son attribut "name".
        On suppose que l'anomaly_dict est bien formé, et que toutes les valeurs sont des 
        instances qui héritent de AbstractAnomaly.
        """
        # Chercher avec le nom de classe d'abord
        if anomaly_name in self.anomaly_dict.keys():
            return self.anomaly_dict[anomaly_name]
        # Chercher avec l'attribut name
        for anomaly in self.anomaly_dict.values():
            if anomaly.name == anomaly_name:
                return anomaly
        raise 

    def inject_anomaly(self, anomaly: AbstractAnomaly, component: AbstractComponent):
        """Injecte une anomalie dans la simulation, avec des vrais instances."""
        if not isinstance(anomaly, AbstractAnomaly):
            raise TypeError("L'anomalie doit hériter de AbstractAnomaly pour être injecté.")
        if not isinstance(component, AbstractComponent):
            raise TypeError("Le composant doit hériter de AbstractComponent pour qu'une anomalie soit injecté dedans.")
        
        component.inject_anomaly(anomaly) # Cette méthode se charge de tout

    def resolve_anomaly(self, anomaly: AbstractAnomaly, component: AbstractComponent):
        """Résout une anomalie dans la simulation, avec des vrais instances."""
        if not isinstance(anomaly, AbstractAnomaly):
            raise TypeError("L'anomalie doit hériter de AbstractAnomaly pour être résolue.")
        if not isinstance(component, AbstractComponent):
            raise TypeError("Le composant doit hériter de AbstractComponent pour qu'une anomalie soit résolue.")
        
        component.resolve_anomaly(anomaly) # Cette méthode se charge de tout

    def subscribe_callback_to_channel(self, channel_name: str, callback: Callable):
        """Permet de s'abonner à un channel du bus de message pour recevoir les données publiées dessus."""
        if not self.bus:
            raise Exception("Le bus n'est pas défini, impossible de s'abonner à un channel.")
        if not isinstance(self.bus, MessageBus):
            raise TypeError("Le bus n'est pas une instance de MessageBus, impossible de s'abonner à un channel.")
        if not isinstance(channel_name, str):
            raise TypeError("Le nom du channel doit être une chaine de caractères.")
        if not callable(callback):
            raise TypeError("Le callback doit être une fonction ou une méthode callable.")
        
        self.bus.subscribe(channel_name, callback)