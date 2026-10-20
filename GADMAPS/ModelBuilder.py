from core.AbstractComponent import AbstractComponent
from core.AbstractObservable import AbstractObservable
from core.AbstractAnomaly import AbstractAnomaly
import os
import inspect
import importlib.util

class ModelBuilder:
    """
    Cette classe a pour but de récupérer un système entier à partir d'un chemin.
    Pendant la récupération du système, accumulera les erreurs rencontrés pendant l'introspection.
    """
    COMPONENT_ABSTRACT_METHODS = ["setup"]
    OBSERVABLE_ABSTRACT_METHODS = ["get_value", "compute_next_state", "apply_next_state", "update"]
    ANOMALY_ABSTRACT_METHODS = ["apply"]

    def __init__(self):
        self.correct_components = []
        self.correct_observables = []
        self.associated_observables = {} # Dictionnaire pour stocker les observables associées à chaque composant
        self.correct_anomalies = []
        self.errors = [] # Liste pour stocker toutes les erreurs
        self.verified_anomalies = [] # Liste qui est là pour être lu par le Simulator, pour qu'il puisse garder en mémoire les anomalies capables d'être injectés.
        self.cached_root = None

    @property
    def system_root(self):
        """
        Permet d'accéder au composant racine du système, en essayant de l'attraper dans le cache.
        Si self.cached_root est None, alors on sauvegarde la racine système dedans, pour faciliter l'appel.
        """
        if self.cached_root:
            return self.cached_root
        system_root = self.get_root_component()
        self.cached_root = system_root
        return system_root

    def set_cached_root(self, root_instance: "AbstractComponent"):
        """Permet de modifier la valeur de cached_root."""
        if not isinstance(root_instance, AbstractComponent):
            raise Exception("La valeur de cached_root doit obligatoirement hériter de AbstractComponent")
        self.cached_root = root_instance

    def invalidate_cached_root(self):
        """Permet d'invalider le composant racine du système stocké dans le cache"""
        self.cached_root = None
    
    def load_files(self, path: str):
        """
        Récupère tous les fichiers .py du dossier path, et les charge pour
        valider les composants et observables.
        """
        if not os.path.exists(path):
            self.add_error("FATAL", path, None, f"Le chemin {path} n'existe pas.")
            return
        if not os.path.isdir(path):
            self.add_error("FATAL", path, None, f"Le chemin {path} n'est pas un dossier.")
            return
        if not any(file.endswith(".py") for file in os.listdir(path)):
            self.add_error("FATAL", path, None, f"Le dossier {path} ne contient aucun fichier .py.")
            return
        
        for file in os.listdir(path):
            if file.endswith(".py"):
                file_path = os.path.join(path, file)
                self.load_from_file(file_path)
        
        # Une fois tous les fichiers chargés, on teste les anomalies
        self.verified_anomalies = [] # Réinitialisation des anomalies vérifiées, au cas où
        for anomaly_class in self.correct_anomalies: # Ce sont bien des instances
            if self._test_anomaly_injection(anomaly_class): # Si le test a réussi, alors on peut l'ajouter à la liste des anomalies vérifiés.
                anomaly_instance = anomaly_class()
                self.verified_anomalies.append(anomaly_instance)

    def load_from_file(self, file_path: str):
        """
        Charge un fichier .py et vérifie les composants et observables qu'il contient.
        """
        if not os.path.exists(file_path):
            self.add_error("ERROR", file_path, None, f"Le fichier {file_path} n'existe pas.")
            return
        if not file_path.endswith(".py"):
            self.add_error("ERROR", file_path, None, f"Le fichier {file_path} n'est pas un fichier .py.")
            return
        
        try:
            module_name = os.path.splitext(os.path.basename(file_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            self._check_and_validate_module(module, file_path)
        except Exception as e:
            self.add_error("ERROR", file_path, None, f"Erreur lors du chargement du module : {e}")

    def get_root_component(self):
        """Retourne la classe du composant racine, s'il y en a un seul."""
        root_components = []
        for component in self.correct_components:
            if component.is_root:
                root_components.append(component)

        if not root_components:
            self.add_error("ERROR", None, None, "Aucun composant racine (is_root = True) n'a été trouvé.")
            return None
        if len(root_components) > 1:
            self.add_error("ERROR", None, None, "Plusieurs composants racines ont été trouvés. Il ne doit y en avoir qu'un seul.")
            return None
            
        return root_components[0]

    def add_error(self, severity: str, file: str, class_name: str, message: str):
        """
        Ajoute une erreur à la liste des erreurs avec les détails fournis.
        severity: Enum de la gravité : ["FATAL", "ERROR", "WARNING"]
            FATAL : Erreur critique qui empêche la construction du système, comme un chemin invalide.
            ERROR : Erreur de validation d'un composant ou observable, par exemple une classe qui ne respecte pas les règles de construction, ou des observables dupliquées.
            WARNING : Avertissement sur des problèmes potentiels, par exemple un observable avec une valeur initiale manquante. (TODO : à implémenter plus tard)
        file: Le fichier dans lequel l'erreur a été détectée (None si pas dans un fichier).
        class_name: Nom de la classe ciblée par l'erreur (None si pas dans une classe).
        message: Un message descriptif de l'erreur.
        """
        # Simulation d'enum
        if severity not in ["FATAL", "ERROR", "WARNING"]:
            raise ValueError("La gravité de l'erreur doit être l'une des suivantes : 'FATAL', 'ERROR', 'WARNING'.")
        
        self.errors.append({
            "severity": severity,
            "file": file,
            "class_name": class_name,
            "message": message
        })

    def _check_and_validate_module(self, module, file_path: str):
        for name, cls in inspect.getmembers(module, inspect.isclass):
            # On ignore les classes qui ont été importées dans le module, 
            # on ne veut que celles qui y sont définies.
            if getattr(cls, '__module__', None) != module.__name__:
                continue

            # Obligé de vérifier que la classe n'est pas une classe abstraite, sinon 
            # on va aussi valider AbstractComponent et AbstractObservable
            if issubclass(cls, AbstractComponent) and cls is not AbstractComponent:
                if self._verify_component(cls, file_path):
                    self.correct_components.append(cls)
                    observables = self._find_observables_in_setup(cls, file_path)
                    self.associated_observables[cls] = observables
                else:
                    self.add_error("ERROR", file_path, cls.__name__, f"Composant invalide trouvé : {cls.__name__}")

            elif issubclass(cls, AbstractObservable) and cls is not AbstractObservable:
                if self._verify_observable(cls, file_path):
                    self.correct_observables.append(cls)
                else:
                    self.add_error("ERROR", file_path, cls.__name__, f"Observable invalide trouvé : {cls.__name__}")

            elif issubclass(cls, AbstractAnomaly) and cls is not AbstractAnomaly:
                if self._verify_anomaly(cls, file_path):
                    self.correct_anomalies.append(cls)
                else:
                    self.add_error("ERROR", file_path, cls.__name__, f"Anomalie invalide trouvée : {cls.__name__}")

    def _verify_component(self, component_class, file_path: str) -> bool:
        """Vérifie que la classe component_class hérite de AbstractComponent et respecte les règles de construction."""
        if inspect.isabstract(component_class):
            self.add_error("ERROR", file_path, component_class.__name__, f"Le composant {component_class.__name__} est partiellement abstrait et ne peut pas être instancié (il manque probablement des méthodes obligatoires comme 'setup').")
            return False
        
        try:
            sig = inspect.signature(component_class.__init__)
            if 'name' not in sig.parameters:
                self.add_error("ERROR", file_path, component_class.__name__, f"Le composant {component_class.__name__} doit avoir un paramètre 'name' dans son constructeur.")
                return False
            for method in self.COMPONENT_ABSTRACT_METHODS:
                if method not in dir(component_class):
                    self.add_error("ERROR", file_path, component_class.__name__, f"Le composant {component_class.__name__} doit implémenter la méthode '{method}'.")
                    return False
        except Exception as e:
            self.add_error("ERROR", file_path, component_class.__name__, f"Erreur lors de l'inspection du composant : {e}")
            return False

        return True

    def _verify_observable(self, observable_class, file_path: str) -> bool:
        """Vérifie que la classe observable_class hérite de AbstractObservable et respecte les règles de construction."""
        if inspect.isabstract(observable_class):
            self.add_error("ERROR", file_path, observable_class.__name__, f"L'observable {observable_class.__name__} est partiellement abstrait et ne peut pas être instancié (il manque probablement des méthodes obligatoires).")
            return False
        
        try:
            sig = inspect.signature(observable_class.__init__)
            if 'name' not in sig.parameters:
                self.add_error("ERROR", file_path, observable_class.__name__, f"L'observable {observable_class.__name__} doit avoir un paramètre 'name' dans son constructeur.")
                return False
            for method in self.OBSERVABLE_ABSTRACT_METHODS:
                if method not in dir(observable_class):
                    self.add_error("ERROR", file_path, observable_class.__name__, f"L'observable {observable_class.__name__} doit implémenter la méthode '{method}'.")
                    return False
        except Exception as e:
            self.add_error("ERROR", file_path, observable_class.__name__, f"Erreur lors de l'inspection de l'observable : {e}")
            return False

        return True
    
    def _verify_anomaly(self, anomaly_class, file_path: str) -> bool:
        """Vérifie que la classe anomaly_class hérite de AbstractAnomaly et respecte les règles de construction."""
        if inspect.isabstract(anomaly_class):
            self.add_error("ERROR", file_path, anomaly_class.__name__, f"L'anomalie {anomaly_class.__name__} est partiellement abstraite et ne peut pas être instanciée (il manque probablement des méthodes obligatoires).")
            return False
        
        try:
            sig = inspect.signature(anomaly_class.__init__)
            for method in self.ANOMALY_ABSTRACT_METHODS:
                if method not in dir(anomaly_class):
                    self.add_error("ERROR", file_path, anomaly_class.__name__, f"L'anomalie {anomaly_class.__name__} doit implémenter la méthode '{method}'.")
                    return False
        except Exception as e:
            self.add_error("ERROR", file_path, anomaly_class.__name__, f"Erreur lors de l'inspection de l'anomalie : {e}")
            return False

        return True

    def _find_observables_in_setup(self, component_class, file_path: str) -> list:
        """
        Analyse dynamiquement les observables configurées dans le setup en
        instanciant la classe temporairement.
        """
        observables_found = []

        # Si jamais la classe n'est pas un composant valide, on ne fait pas l'analyse et on retourne une liste vide.
        if not (isinstance(component_class, type) and issubclass(component_class, AbstractComponent)):
            return []
            
        try:
            if hasattr(component_class, 'setup'):
                temp_instance = component_class(name="temp_component")

                observables = temp_instance.get_observables()
                
                for obs in observables:
                    obs_name = obs.name
                    obs_type = obs.__class__.__name__
                    
                    if obs_name in [o.name for o in observables_found]:
                        self.add_error("ERROR", file_path, component_class.__name__, f"L'observable '{obs_name}' est instanciée plusieurs fois dans le setup de {component_class.__name__}.")
                    
                    if obs.warnings:
                        for warning in obs.warnings:
                            if warning == "INITIAL_VALUE_IS_NONE":
                                self.add_error("WARNING", file_path, component_class.__name__, f"Attention, l'observable '{obs_name}' n'a pas de valeur initiale.")
                    
                    observables_found.append(obs)
        except Exception as e:
            self.add_error("ERROR", file_path, component_class.__name__, f"Erreur lors de l'analyse de la méthode setup de {component_class.__name__} : {e}")
            
        return observables_found
    
    def _test_anomaly_injection(self, anomaly_class: AbstractAnomaly) -> bool:
        """
        Méthode de test pour vérifier que l'anomalie donné peut être injectée et appliquée à un composant.
        On injecte l'anomalie dans le composant de test, on appelle apply une fois, puis on résout l'anomalie.
        Si des erreurs sont rencontrées lors de ce processus, elles sont ajoutées à la liste des erreurs.
        Renvoie True si l'anomalie est valide ou qu'elle n'a pas pu être testé, False sinon.
        """
        try:
            anomaly_instance = anomaly_class()
            component_instance = anomaly_class.generate_test_target()
            
            anomaly_instance.inject(component_instance)
            anomaly_instance.apply(component_instance, dt=0.1) # On utilise un dt arbitraire pour le test
            anomaly_instance.resolve(component_instance)
        except NotImplementedError:
            self.add_error("WARNING", None, anomaly_class.__name__, f"L'anomalie {anomaly_class.__name__} n'a pas implémenté la méthode generate_test_target(). Le test d'injection de cette anomalie a été ignoré.")
            # Pas de False, car techniquement l'anomalie pourrait potentiellement marcher. Dans tous les cas, il y a un warning.
        except Exception as e:
            self.add_error("ERROR", None, anomaly_class.__name__, f"Erreur lors du test d'injection de l'anomalie {anomaly_class.__name__} : {e}")
            return False
        return True