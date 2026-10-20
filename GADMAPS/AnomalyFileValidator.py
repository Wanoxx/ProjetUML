import csv
from Simulator import Simulator

class AnomalyFileValidator:
    def __init__(self, simulator: Simulator):
        if not isinstance(simulator, Simulator):
            raise TypeError("Le simulator doit être de type Simulator")
        self.simulator = simulator

    def validate(self, path: str) -> bool:
        """
        Valide un fichier csv d'anomalie.
        Renvoie True si le fichier est bien structuré, False sinon.
        """
        try:
            # on initialise à -1 pour accepter un temps de 0.0 au début
            previous_time = -1.0
            
            with open(path, newline='', encoding='utf-8') as csvfile:
                # auto détection du séparateur , ou ;
                first_line = csvfile.readline()
                delim = ';' if ';' in first_line else ','
                csvfile.seek(0)
                
                reader = csv.DictReader(csvfile, delimiter=delim)
                
                # verification des colonnes requises
                required_columns = {'global_time', 'anomaly_name', 'action', 'component_name'}
                if reader.fieldnames is None or not required_columns.issubset(set(reader.fieldnames)):
                    return False
                
                for row in reader:
                    # Vérification du temps
                    try:
                        time = float(row['global_time'])
                        # il faut absolument que les temps soient dans l'ordre croissant, sinon le scheduler va fail
                        if time < 0 or time < previous_time:
                            return False
                        previous_time = time
                    except ValueError:
                        return False

                    # verification de l'anomalie
                    anomaly_instance = self.simulator.find_anomaly(row['anomaly_name'].strip())
                    if anomaly_instance is None:
                        return False
                    
                    # verification du composant
                    component_instance = self.simulator.get_component_in_system(row['component_name'].strip())
                    if component_instance is None:
                        return False
                    
                    # verification de l'action
                    action = row['action'].strip().lower()
                    if action not in ['inject', 'resolve']:
                        return False
            
            return True
        except Exception:
            return False