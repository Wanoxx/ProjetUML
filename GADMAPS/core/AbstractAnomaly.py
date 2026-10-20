from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.AbstractComponent import AbstractComponent

class AbstractAnomaly(ABC):
    """
    Classe abstraite définissant une anomalie applicable à un composant.
    L'anomalie peut affecter la hiérarchie du composant ciblé, ou juste un de ses observables, ou même juste un de ses enfants.
    Il est possible pour l'anomalie de connaitre l'état du composant ciblé, et de faire des calculs basés dessus pour appliquer son effet.
    """
    
    def __init__(self, name: str = "Unnamed anomaly", description: str = ""):
        """
        Le constructeur des classes qui héritent de AbstractAnomaly doivent ne pas avoir de paramètre.
        Par exemple : 
        class ExampleAnomaly(AbstractAnomaly):
            def __init__(self):
                super().__init__("Name of Example Anomaly", "Description of Example Anomaly")
        """
        self.name = name
        self.description = description
        self.is_active = False

    def inject(self, component: AbstractComponent) -> None:
        """
        Appelé une seule fois au moment où l'anomalie est affectée au composant cible.
        Cette méthode peut être surchargé pour pouvoir faire quelque chose avant l'application
        de l'anomalie (ex: sauvegarder une valeur d'origine pour la restaurer plus tard).
        ATTENTION : Ne pas oublier de d'abord faire super().inject() avant la surcharge.
        """
        self.is_active = True

    @abstractmethod
    def apply(self, component: AbstractComponent, dt: float) -> None:
        """
        Méthode principale appelée à chaque cycle par le composant (généralement dans before_update).
        C'est ici que l'anomalie "attaque" le composant (modifie un observable, bloque un état, etc.).
        """
        pass

    def resolve(self, component: AbstractComponent) -> None:
        """
        Appelé quand l'anomalie est terminée ou réparée.
        Cette méthode peut être surchargé pour remettre le composant dans un état normal 
        (nettoyer les effets de l'anomalie).
        ATTENTION : Ne pas oublier de d'abord faire super().resolve() avant la surcharge.
        """
        self.is_active = False

    @classmethod
    def generate_test_target(cls) -> AbstractComponent:
        """
        Génère et renvoie un composant factice spécialement configuré 
        pour tester cette anomalie isolément (via ModelBuilder ou scripts de test).
        Doit être surchargé par l'anomalie enfant.
        """
        raise NotImplementedError("La méthode generate_test_target() n'est pas implémentée.")