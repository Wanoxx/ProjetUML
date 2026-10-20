from __future__ import annotations
from abc import ABC, abstractmethod
from typing import final, TYPE_CHECKING
from core.AbstractObservable import AbstractObservable
from core.AbstractUpdatable import AbstractUpdatable
from core.exceptions import *

if TYPE_CHECKING:
    from core.AbstractAnomaly import AbstractAnomaly

class AbstractComponent(AbstractUpdatable, ABC):
    """
    Classe abstraite définissant le minimum requis pour un composant quelconque.
    Permet d'ajouter des observables et d'avoir des enfants, pour former une hiérarchie.
    """
    # Si cet attribut est à True, alors le composant est considéré comme la racine de la hiérarchie, et c'est donc lui qui va déclencher la mise à jour de tout l'arbre.
    # Le ModelBuilder va vérifier que la hiérarchie contient exactement un composant avec is_root à True, et que c'est un composant valide.
    is_root = False

    def __init__(self, name: str, display_name: str = None):
        """
        name est un paramètre qui doit pouvoir être appelé comme un nom de propriété,
        par exemple "fusee.moteur_droit" marche, mais "fusee.Moteur droit" ne marche pas.
        display_name est un paramètre optionnel permettant de spécifier un nom
        plus lisible, par exemple avec des espaces.
        Exemple:
        AbstractComponent("moteur_droit", "Moteur droit") => Bien construit
        AbstractComponent("moteur_droit") => Marche aussi, mais le display_name sera "moteur_droit".
        AbstractComponent("Moteur droit") => Mal construit, ne marche pas
        """
        if not name.isidentifier():
            raise NotIdentifierError(f"Le nom {name} ne peut pas être utilisé comme nom de composant.")
        self.name = name
        if display_name is None: # Le display_name par défaut est name
            display_name = name
        self.display_name = display_name
        self.observables = {}
        self.parent = None
        self.children = {}
        self.active_anomalies = []

        self.setup() # Appel d'une méthode setup pour que les composants puissent 
        # définir leurs observables et enfants à la construction directement

    @abstractmethod
    def setup(self):
        """Méthode à implémenter pour définir les observables et enfants du composant, ou autre."""
        pass

    def add_observable(self, observable: AbstractObservable) -> None:
        """
        Ajoute un observable dans le composant en utilisant son nom unique.
        """
        if not isinstance(observable, AbstractObservable):
            raise TypeError(
                "L'observable n'est pas une instance de AbstractObservable, et ne peut pas être rajouté."
            )
        observable_name = observable.name
        if self.get_observable(observable_name):
            raise DuplicateNameError(
                f"Le nom de l'observable '{observable_name}' du composant '{self.__class__.__name__}' est déjà attribué."
            )
        observable.parent = self
        self.observables[observable_name] = observable

    def get_observable(self, observable_name: str) -> AbstractObservable:
        return self.observables.get(observable_name)
    
    @final
    def get_observables(self) -> list[AbstractObservable]:
        """
        Renvoie la liste de tous les observables du composant.
        Cette méthode ne DOIT PAS être surchargée, car elle est utilisée par le ModelBuilder pour trouver les observables d'un composant, et doit donc être fiable.
        """
        return list(self.observables.values())
    
    @final
    def get_children(self) -> list["AbstractComponent"]:
        """
        Renvoie la liste de tous les enfants du composant.
        Cette méthode ne DOIT PAS être surchargée, car elle est utilisée par le SimulationController pour trouver les enfants d'un composant, et doit donc être fiable.
        """
        return list(self.children.values())
    
    @final
    def get_parent(self) -> AbstractComponent:
        """
        Renvoie le parent du composant, ou None s'il n'en a pas.
        Cette méthode ne DOIT PAS être surchargée, car elle est utilisée par le SimulationController pour trouver le parent d'un composant, et doit donc être fiable.
        """
        return self.parent
    
    def add_child(self, child: "AbstractComponent") -> None:
        """
        Ajoute un enfant dans le composant en utilisant son nom unique.
        Protège contre les mauvais types et les redondances de noms.
        """
        if not isinstance(child, AbstractComponent):
            raise TypeError("L'enfant n'est pas une instance de AbstractComponent et ne peut pas être rattaché.")
        if child is self or child is self.parent:
            raise InvalidHierarchyError("Un composant ne peut pas être son propre enfant ou le parent de son enfant.")
        
        child_name = child.name
        
        if child_name in self.children or child_name in self.observables:
            raise DuplicateNameError(f"Le nom '{child_name}' est déjà utilisé dans le composant '{self.__class__.__name__}'.")
        if child.parent:
            raise InvalidHierarchyError(f"L'enfant '{child_name}' appartient déjà au composant '{child.parent.name}'.")
        
        child.parent = self
        self.children[child_name] = child

    def compute_next_state(self, dt: float) -> None:
        """
        Calcule le prochain état de tous les enfants et observables du composant,
        sans l'appliquer.
        """
        for child in self.children.values():
            child.compute_next_state(dt)
        for observable in self.observables.values():
            observable.compute_next_state(dt)

    def apply_next_state(self) -> None:
        """
        Applique le nouvel état en mémoire pour tous les enfants et observables.
        """
        for child in self.children.values():
            child.apply_next_state()
        for observable in self.observables.values():
            observable.apply_next_state()

    def inject_anomaly(self, anomaly: "AbstractAnomaly") -> None:
        """Injecte une anomalie dans le composant."""
        from core.AbstractAnomaly import AbstractAnomaly
        if not isinstance(anomaly, AbstractAnomaly):
            raise TypeError("L'anomalie doit hériter de AbstractAnomaly pour être injecté.")
        self.active_anomalies.append(anomaly)
        anomaly.inject(self) # On déclenche son initialisation (is_active = True pour comportement normal)

    def resolve_anomaly(self, anomaly: "AbstractAnomaly") -> None:
        """Résout et retire une anomalie du composant."""
        from core.AbstractAnomaly import AbstractAnomaly
        if not isinstance(anomaly, AbstractAnomaly):
            raise TypeError("L'anomalie doit hériter de AbstractAnomaly pour être résolu.")
        if anomaly in self.active_anomalies:
            anomaly.resolve(self) # On déclenche sa résolution (is_active = False pour comportement normal)
            self.active_anomalies.remove(anomaly)

    def before_update(self, dt: float) -> None:
        """
        Méthode à implémenter pour faire quelque chose AVANT de calculer le prochain état de tous les enfants et observables du composant.
        Par défaut, ne fait rien, et doit être surchargée.
        Cette méthode sert à déclencher les anomalies actives, ou bien pour faire quoi que ce soit d'autre.
        """
        for anomaly in self.active_anomalies:
            anomaly.apply(self, dt)

    def after_update(self) -> None:
        """
        Méthode à implémenter pour faire quelque chose APRÈS que la physique ait été mise à jour.
        Par défaut, ne fait rien, et doit être surchargée.
        Pour l'instant, je ne suis pas sûr de l'utilité de cette méthode, car il me semble que ce n'est pas là 
        que les composants vont faire des actions, mais plutôt à la lecture d'une valeur d'un capteur. Dans tous les cas, je la laisse au cas où.
        """
        pass

    def _recursive_before_update(self, dt: float) -> None:
        """Parcourt récursivement l'arbre pour appeler before_update sur chaque composant."""
        self.before_update(dt)
        for child in self.children.values():
            child._recursive_before_update(dt)

    def _recursive_after_update(self) -> None:
        """Parcourt récursivement l'arbre pour appeler after_update sur chaque composant."""
        self.after_update()
        for child in self.children.values():
            child._recursive_after_update()

    def update(self, dt: float) -> None:
        """
        Mise à jour en deux passes pour éviter les problèmes d'ordre de dépendance.
        Calcule d'abord le prochain état de tout l'arbre, puis applique le prochain état à tout l'arbre.
        """
        self._recursive_before_update(dt)
        self.compute_next_state(dt)
        self.apply_next_state()
        self._recursive_after_update()

    def __getattr__(self, item):
        """Permet de facilement trouver des enfants/observables, par exemple fusee.moteur.temperature"""
        if item in self.children:
            return self.children[item]
        if item in self.observables:
            return self.observables[item]
        raise AttributeError(f"L'attribut '{item}' n'a pas été trouvé.")