from PyQt6.QtWidgets import (QWidget, QDialog, QVBoxLayout, QHBoxLayout, 
                             QLabel, QCheckBox, QDoubleSpinBox, QPushButton, QMessageBox)

class GlobalIntervalDialog(QDialog):
    """Mini-popup pour demander uniquement l'intervalle global."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Activer tous les capteurs")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Choisissez le délai pour tous les capteurs :</b>"))
        
        row = QHBoxLayout()
        row.addWidget(QLabel("Intervalle (s) :"))
        self.sb = QDoubleSpinBox()
        self.sb.setRange(0.1, 60.0)
        self.sb.setValue(1.0)
        row.addWidget(self.sb)
        layout.addLayout(row)
        
        btns = QHBoxLayout()
        ok = QPushButton("Valider")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    def get_interval(self):
        return self.sb.value()


class SensorPopupDialog(QDialog):
    """Fenetre de configuration pour les capteurs."""
    def __init__(self, component_name, observables_list, previous_state=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configuration Capteur : {component_name}")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Selectionnez les donnees et l'intervalle :</b>"))
        
        self.obs_controls = {}
        for obs in observables_list:
            row = QHBoxLayout()
            cb = QCheckBox(obs)
            sb = QDoubleSpinBox()
            sb.setRange(0.1, 60.0)
            sb.setValue(1.0)
            
            if previous_state and obs in previous_state:
                cb.setChecked(previous_state[obs]["checked"])
                sb.setValue(previous_state[obs]["interval"])
            
            cb.toggled.connect(sb.setEnabled)
            sb.setEnabled(cb.isChecked())
            
            row.addWidget(cb)
            row.addWidget(QLabel("Intervalle (s) :"))
            row.addWidget(sb)
            layout.addLayout(row)
            self.obs_controls[obs] = {"cb": cb, "sb": sb}
            
        btns = QHBoxLayout()
        
        # Ajout du bouton "Tout sélectionner"
        self.btn_select_all = QPushButton("Tout sélectionner")
        self.btn_select_all.clicked.connect(self.select_all_checkboxes)
        btns.addWidget(self.btn_select_all)
        
        btns.addStretch() # Optionnel, juste pour pousser Valider/Annuler à droite
        
        ok = QPushButton("Valider")
        ok.clicked.connect(self.accept)
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    # Méthode ajoutée pour gérer la sélection globale
    def select_all_checkboxes(self):
        all_checked = all(ctrl["cb"].isChecked() for ctrl in self.obs_controls.values())
        new_state = not all_checked
        for ctrl in self.obs_controls.values():
            ctrl["cb"].setChecked(new_state)
            
            # Conserve la valeur modifiée, mais si elle est au minimum (0.1), force à 1.0 au cochage
            if new_state and ctrl["sb"].value() == 0.1:
                ctrl["sb"].setValue(1.0)
                
        self.btn_select_all.setText("Tout décocher" if new_state else "Tout sélectionner")

    def get_selected_data(self):
        state = {}
        active = []
        for obs, ctrl in self.obs_controls.items():
            checked = ctrl["cb"].isChecked()
            interval = ctrl["sb"].value()
            state[obs] = {"checked": checked, "interval": interval}
            if checked:
                active.append((obs, interval))
        return state, active

class AbstractSystemGUI(QWidget):
    """Classe mere pour les interfaces systemes."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sim_backend = None 
        self.is_running_cb = None 
        self.saved_sensor_states = {} 
        self.latest_sensor_data = {}  
        self.new_messages = {} 
        self.active_callbacks = [] 
        self.active_subscriptions = set() 
        self.csv_path = None

    def set_backend(self, backend, is_running_cb=None):
        """Associe le moteur et rebranche automatiquement les capteurs si le moteur vient d'être réinitialisé."""
        self.sim_backend = backend
        self.is_running_cb = is_running_cb
        
        # nettoyage des tampons au cas où on reçoit un moteur réinitialisé par le contrôleur
        self.latest_sensor_data.clear()
        self.new_messages.clear()
        self.active_callbacks.clear()
        self.active_subscriptions.clear()

        # reconnexion automatique des capteurs si l'utilisateur en avait déjà configuré)
        for component_name, states in self.saved_sensor_states.items():
            comp = self._find_component_in_backend(component_name)
            if not comp: 
                continue
            
            for obs, config in states.items():
                if config["checked"]:
                    key = f"{component_name}.{obs}"
                    
                    val = comp.observables[obs].get_value()
                    self.latest_sensor_data[key] = val
                    self.new_messages[key] = (val, 0.0)
                    
                    self.subscribe_to_observable(component_name, obs, config["interval"])
                    self.active_subscriptions.add(key)


    def _find_component_in_backend(self, name):
        if not self.sim_backend or not self.sim_backend.simulator:
            return None
        root = self.sim_backend.simulator.system_root
        def search(comp):
            if comp.name == name: return comp
            for c in comp.children.values():
                res = search(c)
                if res: return res
            return None
        return search(root)

    def trigger_sensor_popup(self, component_name):
        # on bloque la modification uniquement si la simulation a déjà avancé (t > 0)
        if self.sim_backend and self.sim_backend.simulator:
            if self.sim_backend.simulator.global_time > 0:
                QMessageBox.warning(self, "Bloqué", "Impossible de modifier les capteurs pendant la simulation.\nCliquez sur 'Reset Simulation' d'abord.")
                return

        comp = self._find_component_in_backend(component_name)
        if not comp: return

        prev = self.saved_sensor_states.get(component_name)
        dialog = SensorPopupDialog(component_name, list(comp.observables.keys()), prev, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            state, active = dialog.get_selected_data()
            
            # on sauvegarde juste la nouvelle configuration en mémoire
            # le bouton "Launch Simulation" se chargera de tout appliquer
            self.saved_sensor_states[component_name] = state


    def subscribe_to_observable(self, component_name, obs_name, interval):
        if self.sim_backend:
            def update_data(val):
                state = self.saved_sensor_states.get(component_name, {}).get(obs_name, {})
                if state.get("checked", False):
                    key = f"{component_name}.{obs_name}"
                    t = self.sim_backend.simulator.global_time
                    
                    # seulement pour le GUI
                    self.latest_sensor_data[key] = val
                    self.new_messages[key] = (val, round(t, 2))

            self.active_callbacks.append(update_data)
            self.sim_backend.add_sensor_and_subscribe(component_name, obs_name, interval, update_data)

    def _get_all_components(self):
        """Récupère récursivement tous les composants du système."""
        if not self.sim_backend or not self.sim_backend.simulator:
            return []
        root = self.sim_backend.simulator.system_root
        comps = []
        def traverse(comp):
            comps.append(comp)
            for child in comp.children.values():
                traverse(child)
        if root:
            traverse(root)
        return comps

    def create_global_activate_button(self, text="Activer tous les capteurs"):
        """Renvoie un bouton QPushButton configuré pour l'activation globale."""
        btn = QPushButton(text)
        btn.clicked.connect(self.trigger_global_activate)
        return btn

    def trigger_global_activate(self):
        """Ouvre le popup et active absolument tout si validé."""
        if self.sim_backend and self.sim_backend.simulator:
            if self.sim_backend.simulator.global_time > 0:
                QMessageBox.warning(self, "Bloqué", "Impossible de modifier les capteurs pendant la simulation.\nCliquez sur 'Reset Simulation' d'abord.")
                return

        dialog = GlobalIntervalDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            interval = dialog.get_interval()
            all_comps = self._get_all_components()
            count = 0
            
            for comp in all_comps:
                if comp.observables: # Si le système a des capteurs
                    if comp.name not in self.saved_sensor_states:
                        self.saved_sensor_states[comp.name] = {}
                        
                    for obs in comp.observables.keys():
                        self.saved_sensor_states[comp.name][obs] = {"checked": True, "interval": interval}
                        count += 1
                        
            QMessageBox.information(self, "Succès", f"{count} capteurs activés ({interval}s).")