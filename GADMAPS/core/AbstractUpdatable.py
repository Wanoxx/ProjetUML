from abc import ABC, abstractmethod

class AbstractUpdatable(ABC):
    """
    Interface abstraite pour tout composant ou entité de la simulation 
    (Composants physiques, Capteurs, etc.) qui a besoin d'être mis à jour 
    à chaque pas de temps (dt).
    """
    
    @abstractmethod
    def update(self, dt: float) -> None:
        """Met à jour l'état de l'objet en fonction du temps écoulé."""
        pass
