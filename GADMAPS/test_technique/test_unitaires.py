"""fichier de tests unitaires pour valider individuellement les briques de base du systeme.
note: contrairement aux tests d'integration qui valident un flux entier, 
les tests unitaires se concentrent sur une seule fonction ou classe a la fois pour 
s'assurer que sa logique interne est solide."""

import unittest
import sys
import os

# on force le chemin parent dans les variables systemes pour eviter les problemes d'import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.MessageBus import MessageBus
from core.AbstractComponent import AbstractComponent
from core.exceptions import DuplicateNameError, InvalidHierarchyError

# note d'apprentissage: une classe abstraite ne peut pas etre instanciee directement
# on build un mock, donc une sous-classe factice pour pouvoir manipuler et tester les methodes de la classe mere
class MockComponent(AbstractComponent):
    def setup(self):
        pass

class TestUnitaires(unittest.TestCase):
    
    # sous-systeme: MessageBus
    
    def test_message_bus_subscribe_publish(self):
        """Verifie que l'envoi d'une donnee sur un canal declenche bien les ecouteurs."""
        bus = MessageBus()
        self.received_data = None
        
        # on definit un callback factif pour intercepter la donnee
        def callback(data):
            self.received_data = data
            
        bus.subscribe("test_channel", callback)
        bus.publish("test_channel", 123.45)
        
        # on check si l'information a bien transite a travers le bus sans alteration
        self.assertEqual(self.received_data, 123.45)

    def test_message_bus_unsubscribe(self):
        """Verifie que se desabonner d'un canal coupe bien la reception des messages."""
        bus = MessageBus()
        self.count = 0
        
        def callback(data): self.count += 1
            
        bus.subscribe("chan", callback)
        bus.unsubscribe("chan", callback)
        bus.publish("chan", 1)
        
        # si l'unsubscribe marche la methode callback ne doit pas etre run et on doit rester a 0
        self.assertEqual(self.count, 0)

    # sous-systeme: AbstractComponent
    
    def test_component_duplicate_name(self):
        """Test la robustesse de l'arbre pour empecher deux enfants de porter le meme nom."""
        parent = MockComponent("parent")
        child1 = MockComponent("robot")
        child2 = MockComponent("robot") 
        
        parent.add_child(child1)
        
        # note d'apprentissage: assertRaises permet de verifier qu'un bout de code crash intentionnellement
        # on s'assure ici que le systeme leve bien notre erreur custom DuplicateNameError et pas un autre bug generique
        with self.assertRaises(DuplicateNameError):
            parent.add_child(child2)

    def test_component_self_parenting(self):
        """Test de securite pour empecher une boucle de hierarchie ou un composant se rajoute a lui-meme."""
        comp = MockComponent("self_test")
        
        with self.assertRaises(InvalidHierarchyError):
            comp.add_child(comp)

# on check si le script est run en mode standalone pour lancer l'execution de la suite de tests
if __name__ == '__main__':
    unittest.main()