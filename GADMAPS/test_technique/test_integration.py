"""fichier de tests d'integration pour valider le flux de donnees entre les capteurs et le bus.
note: on utilise la bibliotheque standard 'unittest'. c'est un framework de test qui 
fonctionne comme un labo. il permet de creer des cas de tests isoles pour verifier automatiquement 
que chaque fonction renvoie bien le resultat attendu. ça evite de tout tester a la main a chaque modif."""

import unittest
import sys
import os

# on modifie le chemin d'importation du systeme pour forcer python a reconnaitre le dossier parent
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.MessageBus import MessageBus
from core.AbstractObservable import AbstractObservable
from core.Sensor import Sensor

# note: un mock est un objet factice de simulation. on s'en sert en testing pour imiter une vraie classe complexe
# ça permet de tester une mecanique precise (ici le bus) sans dependre de la physique d'un vrai objet lourd
class MockObservable(AbstractObservable):
    def get_value(self): return 42.0
    def compute_next_state(self, dt): pass
    def apply_next_state(self): pass
    def update(self, dt): pass

# classe qui herite de unittest.TestCase pour que le module comprenne que c'est une suite de tests a run
class TestIntegration(unittest.TestCase):

    def test_sensor_to_bus_flow(self):
        """Vérifie que le capteur publie sur le bus après le bon intervalle.
        Note : unittest detecte et lance automatiquement toutes les methodes qui commencent par 'test_'."""
        
        # on instancie notre systeme de message et notre faux capteur
        bus = MessageBus()
        obs = MockObservable("temp")
        
        # on setup le composant principal qu'on veut reellement tester
        sensor = Sensor(obs, bus, interval=1.0, channel_name="temp_chan")
        
        self.received_val = None
        
        # on definit une fonction de rappel pour intercepter la donnee quand elle sera postee sur le bus
        def callback(val): self.received_val = val
        bus.subscribe("temp_chan", callback)

        # on simule un premier update avec un dt de 0.5s, ce qui est inferieur a l'intervalle de 1.0s
        sensor.update(0.5)
        
        # assertIsNone est une methode de verification stricte de unittest
        # si la valeur n'est pas None, le test crash et signale une erreur mathematique dans la logique
        self.assertIsNone(self.received_val)

        # on rajoute 0.6s au temps precedent, on depasse l'intervalle global donc le capteur doit trigger
        sensor.update(0.6)
        
        # assertEqual compare la valeur reellement recue avec notre valeur mockee de 42.0
        self.assertEqual(self.received_val, 42.0)

# bloc standard pour lancer les tests si le script est execute directement au lieu d'etre importe
if __name__ == '__main__':
    unittest.main()