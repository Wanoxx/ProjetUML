from abc import ABC, abstractmethod
from core.exceptions import *
from core.AbstractUpdatable import AbstractUpdatable

class AbstractObservable(AbstractUpdatable, ABC):
    """
    Classe abstraite définissan le minimum requis pour un observable.
    Les observables sont les valeurs numériques d'une mesure (température,
    vitesse, RPM, etc), qui seront ensuite lues par un capteur.
    """
    def __init__(self, name: str, display_name: str = None, initial_value: float = None):
        """
        name est un paramètre qui doit pouvoir être appelé comme un nom de propriété,
        par exemple "moteur.rpm" marche, mais "moteur.RPM Moteur" ne marche pas.
        display_name est un paramètre optionnel permettant de spécifier un nom
        plus lisible, par exemple avec des espaces.
        Exemple:
        AbstractObservable("rpm", "RPM Moteur") => Bien construit
        AbstractObservable("rpm") => Marche aussi, mais le display_name sera "rpm".
        AbstractObservable("RPM Moteur") => Mal construit, ne marche pas
        """
        self.warnings = [] # Les warnings seront lus par le ModelBuilder plus tard

        if not name.isidentifier():
            raise NotIdentifierError(f"Le nom {name} ne peut pas être utilisé comme nom d'observable.")
        self.name = name

        if display_name is None: # Le display_name par défaut est name
            display_name = name
        self.display_name = display_name

        if initial_value is None:
            self.warnings.append("INITIAL_VALUE_IS_NONE")
            self.initial_value = 0.0
        else:
            self.initial_value = initial_value

        self.current_value = self.initial_value
        self.next_value = self.initial_value

    @abstractmethod
    def get_value(self) -> float:
        """Renvoie la valeur actuelle de l'observable."""
        pass

    @abstractmethod
    def compute_next_state(self, dt: float) -> None:
        """Calcule le prochain état sans l'appliquer."""
        pass

    @abstractmethod
    def apply_next_state(self) -> None:
        """Applique le nouvel état en mémoire."""
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        """Effectue la mise à jour de l'observable."""
        pass