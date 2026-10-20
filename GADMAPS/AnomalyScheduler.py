import csv
from Simulator import Simulator
from AnomalyFileValidator import AnomalyFileValidator

class AnomalyScheduler:
    def __init__(self, simulator: Simulator):
        if not isinstance(simulator, Simulator):
            raise TypeError("Le paramètre simulator doit être une instance de Simulator")
        self.simulator = simulator
        self.validator = AnomalyFileValidator(simulator)
        self.scheduled_events = []

    def load_schedule(self, file_path: str) -> bool:
        """
        Valide le fichier CSV de planification d'anomalies, puis charge et trie les événements.
        Retourne True si le chargement a réussi, False sinon (fichier invalide).
        """
        # utilisation du validateur existant pour garantir l'intégrité du fichier
        if not self.validator.validate(file_path):
            return False

        self.scheduled_events = []
        with open(file_path, newline='', encoding='utf-8') as csvfile:
            # auto détection du séparateur
            first_line = csvfile.readline()
            delim = ';' if ';' in first_line else ','
            csvfile.seek(0)
            
            reader = csv.DictReader(csvfile, delimiter=delim)
            for row in reader:
                self.scheduled_events.append({
                    'global_time': float(row['global_time']),
                    'component_name': row['component_name'].strip(),
                    'anomaly_name': row['anomaly_name'].strip(),
                    'action': row['action'].strip().lower()
                })
        return True

    def update(self) -> None:
        """
        Vérifie si le temps global du simulateur a atteint le temps prévu pour 
        les prochains événements dans la liste, et les déclenche si c'est le cas.
        Doit être appelé à chaque itération de la boucle de simulation.
        """
        current_time = self.simulator.global_time

        while self.scheduled_events and current_time >= self.scheduled_events[0]['global_time']:
            event = self.scheduled_events.pop(0) # Retire l'événement de la liste

            component = self.simulator.get_component_in_system(event['component_name'])
            anomaly = self.simulator.find_anomaly(event['anomaly_name'])
            
            # Application de l'action demandée, on vérifiée en amont dans le validateur que c'est soit inject soit resolve
            if event['action'] == 'inject':
                self.simulator.inject_anomaly(anomaly, component)
            elif event['action'] == 'resolve':
                self.simulator.resolve_anomaly(anomaly, component)