from PyQt6.QtWidgets import QDialog, QMessageBox, QFileDialog
from PyQt6.QtCore import QTimer
import os

from view import MainWindow, ImportDialog
from SimulationController import SimulationController
from GuiIntrospector import find_gui
from DataLogger import DataLogger

class SystemListController:
    """Controleur qui gere l'importation locale et la selection des modeles physiques dans la liste."""
    def __init__(self, main_controller):
        self.main = main_controller
        self.view = main_controller.view.system_list_panel
        
        # on bind les signaux ui aux methodes de ce controleur
        self.view.import_requested.connect(self.handle_import_request)
        self.view.system_selected.connect(self.handle_system_selection)

    def handle_import_request(self):
        # on ouvre une boite de dialogue native pour cibler le dossier
        folder_path = self.view.ask_for_directory()
        if folder_path:
            # on valide la conformite du dossier via le backend
            res = self.main.sim_backend.validate_system_directory(folder_path)
            res["folder_name"] = os.path.basename(folder_path)
            res["folder_path"] = folder_path
            res["gui_class"] = find_gui(folder_path)
            
            dialog = ImportDialog(res, self.main.view)
            
            # on lance la fenetre d'importation et on check si l'utilisateur valide
            if dialog.exec() == QDialog.DialogCode.Accepted:
                name = res["folder_name"]
                
                # on stocke les chemins et references de classe dans les dictionnaires du main
                self.main.imported_systems[name] = folder_path
                self.main.imported_guis[name] = res.get("gui_class")
                self.view.add_system(name)

    def handle_system_selection(self, system_name):
        """Charge la structure physique en memoire des la selection pour permettre le parametrage."""
        
        # on coupe l'horloge interne de pyqt si elle tournait
        if self.main.timer.isActive():
            self.main.timer.stop()

        # on vide le buffer des données simulée pour éviter de perdre les 200 dernières lignes de la simulation précédente
        if hasattr(self.main, 'data_logger'):
            self.main.data_logger.flush()

        self.main.selected_system_name = system_name
        self.main.current_simulated_system = system_name

        self.main.last_gui_update_time = 0.0
        
        # on clean l'historique du terminal et des graphiques
        self.main.view.simulation_panel.shell_output.clear()
        self.main.view.detailed_view_panel.curve_plotter.clear_plots()
        
        # on force l'initialisation du moteur physique pour creer l'arbre des composants
        folder_path = self.main.imported_systems[system_name]
        self.main.sim_backend.initialize_system(folder_path, "root", system_name)
        
        self.main.display_ctrl.show_system_gui(system_name)
        self.main.view.simulation_panel.append_log(f">>> Système {system_name} initialisé à t=0.")

class DisplayController:
    """Controleur dedie a la zone d'affichage centrale pour integrer le panneau de commande du systeme."""
    def __init__(self, main_controller):
        self.main = main_controller
        self.view = main_controller.view.main_display_panel
        self.current_gui_instance = None

    def show_system_gui(self, system_name):
        gui_class = self.main.imported_guis.get(system_name)
        
        # on verifie si une interface a ete trouvee lors de l'introspection
        if gui_class:
            gui_instance = gui_class()
            # on passe le pointeur du backend a l'interface et un callback pour connaitre l'etat du timer
            gui_instance.set_backend(self.main.sim_backend, lambda: self.main.timer.isActive())
            self.view.set_system_gui(gui_instance)
            self.current_gui_instance = gui_instance
        else:
            # sinon on reaffiche le texte de base
            self.view.update_display(system_name)
            self.current_gui_instance = None

class SimPlaybackController:
    """Gere les commandes de lecture multimedia et la modification du tickrate de simulation."""
    def __init__(self, main_controller):
        self.main = main_controller
        self.view = main_controller.view.simulation_panel
        self.view.pause_btn.clicked.connect(self.toggle_pause)
        
        # on passe les multiplicateurs de vitesse via des fonctions anonymes lambda
        # le lambda permet d'injecter un parametre dans le connect sans declencher la fonction
        self.view.slow_btn.clicked.connect(lambda: self.change_speed(1.25))
        self.view.speed_btn.clicked.connect(lambda: self.change_speed(0.80))

    def toggle_pause(self):
        if not self.main.check_system_ready(): 
            return 
        
        if self.main.timer.isActive():
            self.main.timer.stop()
            self.view.update_pause_button(False)
            self.view.append_log(">>> Simulation en pause.")
            
            # hasattr verifie la presence d'un attribut dans un objet pour eviter une erreur
            # ici on s'assure que l'objet data_logger existe bien avant de vider son buffer
            if hasattr(self.main, 'data_logger'):
                self.main.data_logger.flush()
                
        else:
            self.main.timer.start()
            self.view.update_pause_button(True)
            self.view.append_log(">>> Simulation reprise.")

    def change_speed(self, factor):
        # on applique le multiplicateur sur l'intervalle du timer courant
        current_interval = self.main.timer.interval()
        new_val = int(current_interval * factor)
        
        # on bride la frequence pour pas faire crasher le thread principal de l'interface
        new_val = max(10, min(2000, new_val))
        self.main.timer.setInterval(new_val)
        
        # on calcule le ratio d'affichage base sur un temps standard de 100ms
        speed_ratio = 100.0 / new_val
        self.view.append_log(f">>> Vitesse modifiée : x{speed_ratio:.2f}")

# controller.py

class SimLaunchController:
    """Gere le demarrage reel de la boucle temporelle et les remises a zero."""
    def __init__(self, main_controller):
        self.main = main_controller
        self.view = main_controller.view.simulation_panel

    def handle_start_simulation(self):
        if not self.main.check_system_ready(): 
            return
            
        # si on démarre à t=0, c'est une nouvelle run: on prépare le terrain
        if self.main.sim_backend and self.main.sim_backend.simulator.global_time == 0:
            self.handle_reset_simulation()
            
            # on déclenche la création physique du csv et les hooks
            self._setup_data_logging()
            
            self.view.shell_output.clear() 
            
        if not self.main.timer.isActive():
            self.main.timer.start(100)
            self.main.simulation_active = True
            self.main.view.simulation_panel.update_pause_button(True)
            self.view.append_log(">>> Simulation démarrée.")

    def _setup_data_logging(self):
        """Initialise le DataLogger et les abonnements uniquement au lancement effectif."""
        sys_name = self.main.selected_system_name
        gui = self.main.display_ctrl.current_gui_instance
        
        if gui and hasattr(self.main, 'data_logger'):
            active_keys = []
            # on récupère les capteurs cochés dans l'interface
            for comp, obs_dict in gui.saved_sensor_states.items():
                for obs, config in obs_dict.items():
                    if config["checked"]:
                        active_keys.append(f"{comp}.{obs}")
            
            if active_keys:
                # création réelle du fichier sur le disque
                self.main.data_logger.initialize_file(sys_name, active_keys)
                
                # on met en place des abonnements sur le bus d'événements
                for key in active_keys:
                    comp, obs = key.split(".")
                    callback = lambda val, k=key: self.main.data_logger.log_event(k, val)
                    self.main.sim_backend.subscribe_callback_to_observable_channel(comp, obs, callback)

    def handle_reset_simulation(self):
        """Reinitialise l'arbre physique a t=0 sans créer de fichier CSV immédiatement."""
        if not self.main.check_system_ready(): 
            return
            
        if self.main.timer.isActive():
            self.main.timer.stop()
            self.main.view.simulation_panel.update_pause_button(False)
            
        self.main.simulation_active = False 
        self.main.last_gui_update_time = 0.0 

        if hasattr(self.main, 'data_logger'):
            self.main.data_logger.flush()
            
        sys_name = self.main.selected_system_name
        path = self.main.imported_systems[sys_name]
        self.main.sim_backend.initialize_system(path, "root", sys_name)
        
        self.main.view.simulation_panel.shell_output.clear()
        self.main.view.detailed_view_panel.curve_plotter.clear_plots()

        # on prépare une nouvelle instance sans appeler initialize_file
        self.main.data_logger = DataLogger()
        
        gui = self.main.display_ctrl.current_gui_instance
        if gui:
            # on se contente de reconnecter le backend à l'interface
            gui.set_backend(self.main.sim_backend, lambda: self.main.simulation_active)

        self.view.append_log(f">>> Simulation de '{sys_name}' réinitialisée à t=0.")
    
    def handle_import_anomaly(self):
        """Ouvre un explorateur de fichiers pour parser un scenario d'anomalies csv."""
        if not self.main.selected_system_name:
            QMessageBox.warning(self.view, "Action impossible", "Veuillez d'abord sélectionner et charger un système.")
            return

        # on bloque l'importation si la simulation a déjà commencé à avancer
        if self.main.sim_backend and self.main.sim_backend.simulator:
            if self.main.sim_backend.simulator.global_time > 0:
                QMessageBox.warning(self.view, "Bloqué", 
                                    "Impossible d'importer des anomalies pendant la simulation.\nCliquez sur 'Reset Simulation' d'abord.")
                return

        # QFileDialog invoque une boite de l'os pour chopper un chemin avec un filtre csv
        file_path, _ = QFileDialog.getOpenFileName(
            self.view, 
            "Sélectionner un fichier de planification d'anomalies", 
            "", 
            "Fichiers CSV (*.csv);;Tous les fichiers (*)"
        )
        
        if file_path:
            # on load et on parse le fichier dans le moteur
            success = self.main.sim_backend.load_anomaly_file(file_path)
            
            # on coupe la chaine de caractere via le separateur de dossier pour isoler le nom
            file_name = file_path.split("/")[-1] 
            
            if success:
                self.view.append_log(f">>> Fichier d'anomalies chargé : '{file_name}'")
            else:
                QMessageBox.warning(self.view, "Erreur", "Le fichier d'anomalies est invalide, mal formaté ou introuvable.")
                self.view.append_log(f">>> ERREUR : Impossible de charger '{file_name}'")

class AppController:
    """Controleur global instanciant les vues et les bus pour synchroniser l'affichage."""
    def __init__(self):
        self.view = MainWindow()
        self.sim_backend = SimulationController()
        
        # initialisation des variables contenant les metadonnees
        self.simulation_active = False
        self.imported_systems = {}
        self.imported_guis = {}
        self.selected_system_name = None
        self.current_simulated_system = None
        
        # QTimer est la classe pyqt qui declenche une boucle continue sans geler l'interface graphique
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_step)
        self.dt = 0.1 
        
        # memoire du dernier temps pour brider le framerate
        self.last_gui_update_time = 0.0 

        # instanciation des sous controleurs modulaires
        self.system_list_ctrl = SystemListController(self)
        self.display_ctrl = DisplayController(self)
        self.sim_launch_ctrl = SimLaunchController(self)
        self.sim_playback_ctrl = SimPlaybackController(self)
        
        # connexion des signaux globaux 
        self.view.simulation_panel.launch_sim_btn.clicked.connect(self.sim_launch_ctrl.handle_start_simulation)
        self.view.simulation_panel.reset_btn.clicked.connect(self.sim_launch_ctrl.handle_reset_simulation)
        self.view.simulation_panel.import_anomaly_btn.clicked.connect(self.sim_launch_ctrl.handle_import_anomaly)
    
    def check_system_ready(self):
        """Verifie si un systeme est en memoire et declenche une boite d'erreur le cas echeant."""
        if not self.selected_system_name:
            QMessageBox.warning(self.view, "Action impossible", 
                                "Veuillez d'abord sélectionner et charger un système.")
            return False
        return True

    def _recursive_extract(self, component, prefix=""):
        """Descend recursivement dans l'arbre physique pour recuperer toutes les observables en vrac."""
        
        res = {f"{prefix}{k}": v.get_value() for k, v in component.observables.items()}
        
        # boucle qui rappelle cette meme fonction pour aller fouiller dans les noeuds enfants
        for child_name, child in component.children.items():
            res.update(self._recursive_extract(child, f"{prefix}{child_name}."))
        return res

    def update_step(self):
        """Methode appelee a chaque tick du QTimer pour faire avancer la simulation d'un delta."""
        
        self.sim_backend.update_simulation(self.dt)
        sim = self.sim_backend.simulator
        
        if sim and sim.system_root:
            gui = self.display_ctrl.current_gui_instance
            if gui and gui.new_messages:
                
                # on ecrit les donnees dans le csv au rythme maximum de la boucle
                if hasattr(self, 'data_logger'):
                    self.data_logger.write_snapshot(sim.global_time)

                # on parse les nouvelles valeurs recues en texte pour le terminal shell
                first_key = list(gui.new_messages.keys())[0]
                real_time = gui.new_messages[first_key][1]
                data_list = [f"{k}: {v[0]:.2f}" for k, v in gui.new_messages.items()]
                log_msg = f"[t={real_time:.1f}s] " + " | ".join(data_list)
                self.view.simulation_panel.append_log(log_msg)

                # on utilise un timer delta pour brider l'envoi de donnees au pyqtgraph a 1 maj/s
                if sim.global_time - self.last_gui_update_time >= 1.0:
                    
                    graph_data = {k: v[0] for k, v in gui.new_messages.items()}
                    self.view.detailed_view_panel.curve_plotter.update_data(sim.global_time, graph_data)
                    
                    self.last_gui_update_time = sim.global_time
                
                # on flush la stack de messages une fois que tout le processus est traite
                gui.new_messages.clear()