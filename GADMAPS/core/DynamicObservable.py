from core.AbstractObservable import AbstractObservable
from typing import Callable

class DynamicObservable(AbstractObservable):
    """
    Implémentation de AbstractObservable qui permet de définir une règle d'évolution
    dépendant d'autres valeurs d'Observables.
    """
    def __init__(self, name: str, display_name: str = None, initial_value: float = None):
        super().__init__(name, display_name, initial_value)

        self.evolution_rules = [] # Liste de lambdas qui définissent la règle
        # d'évolution pour calculer le prochain état

    def add_evolution_rule(self, rule: Callable, dependencies: list):
        """
        Ajoute une règle d'évolution et les dépendances pour cet observable.
        Le lambda (rule) doit accepter current_value, dt, et les valeurs des 
        observables dans dependencies comme arguments.
        Les paramètres du lambda doivent toujours suivre cette ordre :
        current_value, dt, valeur_1, valeur_2, ... avec en dependencies dans
        ce cas-là, [obs_1, obs_2], donc dans le même ordre que les paramètres.
        """
        if dependencies is None:
            dependencies = []
            
        if not callable(rule):
            raise TypeError("La règle passée doit être un Callable, par exemple un lambda.")
            
        for dep in dependencies:
            if not isinstance(dep, AbstractObservable):
                raise TypeError(f"La dépendance {dep} n'est pas une instance de AbstractObservable.")
                
        self.evolution_rules.append({"rule": rule, "dependencies": dependencies})


    def get_value(self) -> float:
        return self.current_value

    def compute_next_state(self, dt):
        if not self.evolution_rules:
            self.next_value = self.current_value
            return
        
        total_change = 0.0

        for rule_info in self.evolution_rules:
            rule = rule_info["rule"]
            dependencies = rule_info["dependencies"]
            dependency_values = [dep.get_value() for dep in dependencies]
            change = rule(self.current_value, dt, *dependency_values)
            total_change += change

        self.next_value = self.current_value + total_change

    def apply_next_state(self):
        self.current_value = self.next_value

    def update(self, dt):
        """
        Raccourci pour mettre à jour un observable unitairement (hors hiérarchie).
        """
        self.compute_next_state(dt)
        self.apply_next_state()