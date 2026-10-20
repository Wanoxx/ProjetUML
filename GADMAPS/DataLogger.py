import csv
import os
from datetime import datetime

class DataLogger:
    """Service indépendant chargé d'enregistrer les données de simulation au format Excel (Wide)."""
    def __init__(self):
        self.csv_path = None
        self.headers = ["Timestamp"]
        self.current_values = {}
        self.active_keys = []
        
        # tampon en mémoire vive pour optimiser les I/O disque
        self.buffer = [] 
        # nombre de lignes avant écriture sur le disque
        self.flush_limit = 200

    def initialize_file(self, system_name, active_sensor_keys):
        """Prépare le fichier avec le séparateur point-virgule pour Excel."""
        
        # on force l'écriture des données en attente de l'ancienne simulation
        self.flush() 
        
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_dir = "data_output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        self.csv_path = os.path.join(output_dir, f"{system_name}_{now}.csv")
        
        self.active_keys = sorted(active_sensor_keys)
        self.headers = ["Timestamp"] + self.active_keys
        
        self.current_values = {key: 0.0 for key in self.active_keys}
        self.buffer = [] 
        
        with open(self.csv_path, 'w', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(self.headers)

    def log_event(self, key, value):
        """Met à jour la dernière valeur connue (reçue via le bus)."""
        if key in self.current_values:
            self.current_values[key] = value

    def write_snapshot(self, time_t):
        """Écrit une ligne complète. Les valeurs non mises à jour sont répétées."""
        if not self.csv_path:
            return
            
        # construction de la ligne avec les données actuelles en mémoire
        row = [round(time_t, 2)]
        for key in self.active_keys:
            # on répète la dernière valeur connue présente dans self.current_values
            # arrondi à 4 décimales pour alléger le CSV
            row.append(round(self.current_values[key], 4)) 
            
        # on ajoute en mémoire RAM
        self.buffer.append(row)
        
        # on decharge sur le disque dur uniquement si le buffer est plein
        if len(self.buffer) >= self.flush_limit:
            self.flush()

    def flush(self):
        """Méthode à appeler aussi manuellement à la fin ou en pause pour vider le reste."""
        if not self.csv_path or not self.buffer:
            return
        # l'utilisation de writerows au lieu de writerow divise le coût temporel I/O
        with open(self.csv_path, 'a', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerows(self.buffer)
        self.buffer.clear()