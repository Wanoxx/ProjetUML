"""fichier de tests de robustesse pour eprouver la resistance du parseur d'anomalies face a des donnees corrompues.
note d'apprentissage: les tests de robustesse (ou tests aux limites) servent a s'assurer que notre programme 
ne crash pas violemment quand on lui donne n'importe quoi. on veut qu'il gere l'erreur proprement, eg return False.
ici, on utilise 'tempfile' pour creer de vrais fichiers physiques le temps du test et les detruire juste apres."""

import unittest
import sys
import os
import tempfile

# on ajoute la racine au path pour que les modules locaux soient trouvables
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from AnomalyFileValidator import AnomalyFileValidator
from Simulator import Simulator
from core.MessageBus import MessageBus

class TestRobustesse(unittest.TestCase):

    # note: la methode 'setUp' est très puissante dans unittest
    # elle est executee automatiquement AVANT chaque test de la classe
    # ca permet de recreer un environnement (bus, sim, validateur) propre et neuf pour chaque test
    def setUp(self):
        """Initialise l'environnement de test avant chaque methode."""
        self.bus = MessageBus()
        self.sim = Simulator(bus=self.bus)
        self.validator = AnomalyFileValidator(self.sim)

    def test_invalid_csv_format(self):
        """Teste la reaction du systeme face a un CSV avec des entetes invalides ou manquantes."""
        
        # on genere un fichier txt temporaire simulant un csv ecorche
        # delete=False force a le garder le temps qu'on finisse le bloc 'with'
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("global_time;bad_column\n1.0;error")
            temp_path = f.name

        # on utilise try/finally pour garantir la destruction du fichier meme si l'assertion echoue et leve une exception
        try:
            result = self.validator.validate(temp_path)
            
            # on check si la methode a bien vu l'erreur et a decide de refuser le fichier (False)
            self.assertFalse(result, "Le validateur devrait renvoyer False pour un CSV malformé.")
        finally:
            os.remove(temp_path)

    def test_non_chronological_time(self):
        """Vérifie que le validateur bloque un fichier ou le temps fait des sauts en arriere (non croissant)."""
        
        # on ecrit un csv ou la deuxieme action se passe avant la premiere (t=5s apres t=10s)
        content = "global_time;anomaly_name;action;component_name\n10.0;A;inject;C\n5.0;A;inject;C"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = self.validator.validate(temp_path)
            
            # on s'attend a ce que le validateur capte l'incoherence temporelle et retourne False
            self.assertFalse(result, "Le validateur devrait refuser des temps non chronologiques.")
        finally:
            os.remove(temp_path)

# bloc d'execution standard pour un script de test
if __name__ == '__main__':
    unittest.main()