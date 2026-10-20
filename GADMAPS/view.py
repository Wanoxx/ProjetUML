from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QListWidget, QTextEdit, QFileDialog, QDialog,
                             QListWidgetItem, QStyle, QStackedWidget, QScrollArea, QGridLayout)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal
import pyqtgraph as pg

class ImportDialog(QDialog):
    """Fenetre de dialogue pour valider l'importation d'un dossier et afficher ses composants ou erreurs."""
    def __init__(self, validation_result, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import System")
        self.resize(500, 600) 
        
        layout = QVBoxLayout(self)
        
        # on recupere les donnees depuis le dictionnaire
        folder_name = validation_result.get("folder_name", "Inconnu")
        components = validation_result.get("components", [])
        errors = validation_result.get("errors", [])
        
        title = QLabel(f"Bilan de l'introspection pour '{folder_name}':")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        # on affiche la liste des composants valides
        comp_label = QLabel(f"Composants valides trouvés ({len(components)}):")
        layout.addWidget(comp_label)
        
        # on instancie la liste visuelle et on la remplit
        self.comp_list = QListWidget()
        
        # on boucle sur chaque composant trouve pour l'ajouter a la liste ui
        for comp in components:
            nb_obs = len(comp.get('linked_observables', []))
            self.comp_list.addItem(f"✅ {comp['class_name']} ({nb_obs} observables)")
        layout.addWidget(self.comp_list)
        
        # on affiche les erreurs en rouge s'il y en a
        if errors:
            err_label = QLabel(f"Erreurs détectées ({len(errors)}):")
            err_label.setStyleSheet("color: #ff5555; font-weight: bold; margin-top: 10px;")
            layout.addWidget(err_label)
            
            self.err_list = QListWidget()
            self.err_list.setStyleSheet("color: #ff5555;")
            
            # on boucle pour afficher chaque erreur detectee dans la liste
            for err in errors:
                self.err_list.addItem(f"[{err['severity']}] {err['message']}")
            layout.addWidget(self.err_list)
        
        # on creer le bouton pour valider l'importation
        self.validate_btn = QPushButton("Validate Import")
        self.validate_btn.clicked.connect(self.accept) 
        layout.addWidget(self.validate_btn)

        # on verifie s'il y a des erreurs bloquantes
        has_critical_errors = any(err['severity'] in ['FATAL', 'ERROR'] for err in errors)
        
        # si on detecte une erreur fatale ou une liste vide on desactive le bouton d'import
        if has_critical_errors or not components:
            self.validate_btn.setEnabled(False)
            self.validate_btn.setStyleSheet("background-color: #555555; color: #888888;")
            self.validate_btn.setText("Importation bloquée (Corrigez les erreurs métier)")


class CurvePlotter(QWidget):
    """Classe dediee pour dessiner et gerer les courbes en temps reel via pyqtgraph avec Scroll."""
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # pg gere les graphiques hautes performances en python
        # on lui donne des couleurs globales pour s'integrer au theme sombre
        pg.setConfigOption('background', '#1e1e1e')
        pg.setConfigOption('foreground', '#cccccc')
        
        # on instancie QScrollArea qui permet de faire defiler son contenu si la fenetre est trop petite
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True) 
        self.scroll_area.setStyleSheet("QScrollArea { border: none; }")
        
        # on create un widget conteneur invisible et on lui applique un layout en grille
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        
        # on integre le contenu dans la zone defilante, puis la zone dans le layout principal
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)
        
        # on initialise les dictionnaires qui vont stocker les objets graphiques et l'historique de donnees
        self.plots = {}   
        self.curves = {}  
        self.data_x = {}  
        self.data_y = {}  

    def update_data(self, time_step, observables_data):
        """Met à jour les courbes avec les nouvelles données et gère le placement en grille."""
        
        # boucle qui parcours chaque nouvelle donnee pour update ou create sa courbe
        for name, value in observables_data.items():
            
            if name not in self.plots:
                # on create un widget de graphique individuel pyqtgraph
                plot = pg.PlotWidget(title=name)
                plot.showGrid(x=True, y=True, alpha=0.3)
                plot.setMinimumHeight(250) 
                
                # on desactive l'autorange natif de pyqtgraph pour eviter des crashs de perf
                plot.disableAutoRange()
                
                curve = plot.plot(pen=pg.mkPen(color='#007acc', width=2))
                
                # on calcule dynamiquement la ligne et colone pour placer le graph
                row = len(self.plots) // 2
                col = len(self.plots) % 2
                self.grid_layout.addWidget(plot, row, col)
                
                self.plots[name] = plot
                self.curves[name] = curve
                self.data_x[name] = []
                self.data_y[name] = []

            self.data_x[name].append(time_step)
            self.data_y[name].append(value)
            
            # on garde seulement les 1000 derniers points en memoire pour pas saturer la ram
            self.data_x[name] = self.data_x[name][-1000:]
            self.data_y[name] = self.data_y[name][-1000:]
            
            # on gere le focus de la camera sur l'axe x
            min_x = self.data_x[name][0]
            max_x = self.data_x[name][-1]
            
            # on cale la vue exactement du premier au dernier point
            if max_x > min_x:
                self.plots[name].setXRange(min_x, max_x, padding=0)
            else:
                self.plots[name].setXRange(max_x - 1.0, max_x + 1.0, padding=0)

            # on calcule manuellement l'echelle y pour bien cadrer la courbe
            y_min = min(self.data_y[name])
            y_max = max(self.data_y[name])
            diff = y_max - y_min
            
            if diff < 0.001:
                # si la courbe est plate on force un petit zoom autour de la valeur
                val = self.data_y[name][-1]
                self.plots[name].setYRange(val - 1.0, val + 1.0, padding=0)
            else:
                # sinon on rajoute un peu de marge en haut et en bas pour l'esthetique
                margin = diff * 0.1
                self.plots[name].setYRange(y_min - margin, y_max + margin, padding=0)
            
            # on set les nouvelles listes de donnees sur la courbe
            self.curves[name].setData(self.data_x[name], self.data_y[name])

    def clear_plots(self):
        """Efface la grille native et vide la memoire."""
        self.data_x.clear()
        self.data_y.clear()
        self.curves.clear()
        self.plots.clear()
        
        # boucle qui parcours le layout en grille pour detruire  chaque widget
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
    def reset_view(self):
        """Reactive l'auto-focus sur tous les graphiques."""
        
        # on reactive le comportement par defaut de pyqtgraph pour la vue
        for plot in self.plots.values():
            plot.enableAutoRange()

class DetailedViewPanel(QWidget):
    """Panneau pour la visualisation detaillee, contenant la courbe et le bouton pour quitter."""
    
    # pyqtSignal permet de creer un evenement custom qu'on pourra ecouter ailleurs
    close_requested = pyqtSignal() 

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.close_btn = QPushButton("Close Detailed View")
        self.close_btn.clicked.connect(self.close_requested.emit)
        
        # on instancie la zone de dessin de la courbe
        self.curve_plotter = CurvePlotter()
        layout.addWidget(self.close_btn)
        layout.addWidget(self.curve_plotter, 1)


class SystemListPanel(QWidget):
    """Panneau en haut à gauche gérant la liste des systèmes importés."""
    
    # creation de signaux pour informer qu'on a clique sur un systeme ou sur le bouton importer
    system_selected = pyqtSignal(str)
    import_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # on creer le bouton d'importation et on le connecte au signal
        self.import_btn = QPushButton("Import New System")
        self.import_btn.clicked.connect(self.import_requested.emit)
        
        # on instancie QListWidget pour faire une liste selectionnable et on connecte le clic
        self.system_list = QListWidget()
        self.system_list.itemClicked.connect(lambda item: self.system_selected.emit(item.text()))
        
        layout.addWidget(self.import_btn)
        layout.addWidget(self.system_list)

    def ask_for_directory(self):
        """Ouvre une fenetre native de l'OS pour demander à l'utilisateur de choisir un dossier."""
        
        # on utilise la boite de dialogue native de l'os pour attraper un chemin de dossier
        return QFileDialog.getExistingDirectory(self, "Select System Directory")

    def add_system(self, folder_name):
        """Ajoute le dossier validé visuellement dans la liste de l'interface."""
        item = QListWidgetItem(folder_name)
        
        # on recupere l'icone de dossier native du systeme grace a QStyle
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        item.setIcon(icon)
        
        self.system_list.addItem(item)
        
        # on selectionne automatiquement ce nouvel item qu'on vient d'ajouter
        self.system_list.setCurrentItem(item)
        self.system_selected.emit(folder_name)


class MainDisplayPanel(QWidget):
    """Panneau en haut à droite pour afficher le GUI du système introspecté."""
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # on garde une reference du gui actuellement affiche pour pouvoir le detruire au changement
        self.current_gui_widget = None
        
        # on setup un label de placeholder en attendant un vrai gui
        self.display_label = QLabel("Import a first system to visualize it here")
        self.display_label.setObjectName("MainDisplay") 
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.display_label)

    def set_system_gui(self, gui_widget):
        """Supprime l'ancien affichage et integre le GUI natif du systeme sélectionné."""
        
        # on cache le texte par defaut
        self.display_label.hide()
        
        # si un ancien gui etait deja affiche on le supprime de la memoire
        if self.current_gui_widget:
            self.current_gui_widget.setParent(None)
            self.current_gui_widget.deleteLater()
            
        # on integre le nouveau gui donne apres introspection
        self.current_gui_widget = gui_widget
        self.main_layout.addWidget(self.current_gui_widget)

    def update_display(self, folder_name):
        """Met à jour le texte affiché si jamais le système n'a pas de GUI natif"""
        if not self.current_gui_widget:
            self.display_label.setText(f"GUI of the system '{folder_name}' introspected\n(No GUI file found yet)")
            self.display_label.show()

class SimulationPanel(QWidget):
    """Panneau en bas gerant les boutons de simulation, le terminal et la lecture vidéo."""
    
    # signal pour demander l'affichage de la vue detaillee
    detailed_view_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #252526; border-top: 1px solid #333333;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # on setup un layout horizontal pour ranger les boutons de controle de simul
        sim_controls_layout = QHBoxLayout()
        self.launch_sim_btn = QPushButton("Launch Simulation")
        self.import_anomaly_btn = QPushButton("Import Anomaly File")
        self.detail_view_btn = QPushButton("Detailed Visualization")
        self.reset_btn = QPushButton("Reset Simulation")
        self.detail_view_btn.clicked.connect(self.detailed_view_requested.emit)
        
        sim_controls_layout.addWidget(self.launch_sim_btn)
        sim_controls_layout.addWidget(self.import_anomaly_btn)
        sim_controls_layout.addWidget(self.detail_view_btn)
        sim_controls_layout.addWidget(self.reset_btn)
        sim_controls_layout.addStretch()
        
        # on instancie QTextEdit pour faire un terminal visuel en lecture seule
        self.shell_output = QTextEdit()
        
        # on limite l'historique a 100 blocs memoire pour ne pas saturer la ram
        self.shell_output.document().setMaximumBlockCount(100)
        self.shell_output.setReadOnly(True)
        
        # on prepare la barre de lecture en bas facon lecteur multimedia
        media_controls_layout = QHBoxLayout()
        self.slow_btn = QPushButton("⏪ Slow Down")
        self.pause_btn = QPushButton("⏸ Pause")
        self.speed_btn = QPushButton("⏩ Speed Up")
        
        media_controls_layout.addStretch()
        media_controls_layout.addWidget(self.slow_btn)
        media_controls_layout.addWidget(self.pause_btn)
        media_controls_layout.addWidget(self.speed_btn)
        media_controls_layout.addStretch()

        layout.addLayout(sim_controls_layout)
        layout.addWidget(self.shell_output)
        layout.addLayout(media_controls_layout)

    def append_log(self, text):
        """Ajoute une ligne de texte dans le terminal et descend l'ascenseur tout en bas."""
        
        # on ajoute le texte et on force le scrollbar a descendre pour voir le dernier message
        self.shell_output.append(text)
        scrollbar = self.shell_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_pause_button(self, is_running):
        """Change le texte du bouton pause en fonction de si la simulation tourne ou non."""
        if is_running:
            self.pause_btn.setText("⏸ Pause")
        else:
            self.pause_btn.setText("▶ Resume")


class MainWindow(QWidget):
    """Fenetre principale qui assemble et organise tous les sous-panneaux."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GADMAPS")

        self.setWindowIcon(QIcon("app_icon.png"))
        
        # on applique le qss global qui marche exactement comme du css pour styliser les widgets
        self.setStyleSheet("""
            QWidget { background-color: #1e1e1e; color: #cccccc; font-family: 'Segoe UI', Arial; }
            
            /* style de base des boutons */
            QPushButton { 
                background-color: #0e639c; 
                color: white; 
                border: none; 
                padding: 8px; 
                border-radius: 4px; 
            }
            
            /* etat au survol (le feedback mouvement) */
            QPushButton:hover { 
                background-color: #1177bb; 
                border: 1px solid #3291d3;
            }
            
            /* etat lors du clic (feedback ergonomique) */
            QPushButton:pressed { 
                background-color: #0a4a75; 
                padding-top: 10px; /* effet de légère pression */
                padding-bottom: 6px;
            }

            /* style specifique pour les boutons desactivés */
            QPushButton:disabled {
                background-color: #3e3e42;
                color: #808080;
            }
            
            QListWidget { background-color: #252526; border: 1px solid #333333; }
            QListWidget::item:selected { background-color: #37373d; border-left: 3px solid #007acc; } 
            QTextEdit { background-color: #000000; color: #4af626; font-family: 'Consolas', monospace; border: 1px solid #333333; }
            QLabel#MainDisplay { background-color: #2d2d30; font-size: 18px; color: #888888; }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # on initialise tous nos objets panneaux independants
        self.system_list_panel = SystemListPanel()
        self.main_display_panel = MainDisplayPanel()
        self.detailed_view_panel = DetailedViewPanel()
        
        # on regroupe la liste de gauche et l'affichage de droite dans un seul widget
        normal_top_widget = QWidget()
        normal_top_layout = QHBoxLayout(normal_top_widget)
        normal_top_layout.addWidget(self.system_list_panel, 1)
        normal_top_layout.addWidget(self.main_display_panel, 7)

        # on utilise QStackedWidget qui fonctionne comme un systeme d'onglets invisibles pour switch de vue
        self.top_stack = QStackedWidget()
        self.top_stack.addWidget(normal_top_widget) 
        self.top_stack.addWidget(self.detailed_view_panel) 
        
        # on instancie le panneau du bas
        self.simulation_panel = SimulationPanel()

        # on connecte directement les signaux visuels entre eux, ici la vue parle a la vue
        self.system_list_panel.system_selected.connect(self.main_display_panel.update_display)
        self.simulation_panel.detailed_view_requested.connect(lambda: self.top_stack.setCurrentIndex(1))
        self.detailed_view_panel.close_requested.connect(lambda: self.top_stack.setCurrentIndex(0))

        # on add les widgets au layout principal avec les proportions de taille souhaites
        main_layout.addWidget(self.top_stack, 2)
        main_layout.addWidget(self.simulation_panel, 1)