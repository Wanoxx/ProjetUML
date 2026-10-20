import os
import cv2
import math
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QPushButton, QStackedWidget, QLabel
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QPolygonF, QImage, QPixmap
from core.AbstractSystemGUI import AbstractSystemGUI


class VideoWidget(QWidget):
    """Fenetre video pour la Ferrari avec zones cliquables polygonales."""
    def __init__(self, gui_parent):
        super().__init__()
        self.gui = gui_parent
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_label = QLabel(self)
        self.video_label.setMinimumSize(1, 1)
        
        # on desactive le scale natif pour gerer manuellement le ratio de l'image
        self.video_label.setScaledContents(False)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # on remplace le noir par le gris de fond de l'application pour fondre les bandes
        self.video_label.setStyleSheet("background-color: #1e1e1e;")
        layout.addWidget(self.video_label)
        
        self.frames = []
        self.current_frame_idx = 0
        self.direction = 1  
        
        # on map les masques de collision en pourcentage de l'image pour s'adapter au 
        # chaque point est un sommet d'un polygone qui forme la zone clickable de chaque composant, sous système donc
        self.zones = {
            "transmission": [(0.509, 0.497), (0.532, 0.484), (0.546, 0.475), (0.559, 0.456), (0.575, 0.439), (0.579, 0.469), 
                             (0.527, 0.510), (0.513, 0.518)],
            "exhaust": [(0.441, 0.588), (0.458, 0.574), (0.473, 0.588), (0.522, 0.546), (0.521, 0.518), (0.552, 0.497), 
                        (0.573, 0.482), (0.578, 0.505), (0.534, 0.531), (0.535, 0.563), (0.478, 0.616), (0.443, 0.595)],
            "engine": [(0.312, 0.520), (0.361, 0.537), (0.410, 0.597), (0.406, 0.635), (0.443, 0.618), (0.453, 0.667), 
                       (0.413, 0.695), (0.387, 0.663), (0.298, 0.571)],
            "cooling": [(0.250, 0.520), (0.310, 0.610),(0.356, 0.665), (0.384, 0.684), (0.387, 0.787), (0.314, 0.729), 
                        (0.311, 0.795), (0.215, 0.655), (0.218, 0.582), (0.246, 0.522)],
            "suspension": [(0.517, 0.588), (0.530, 0.574), (0.548, 0.593), (0.544, 0.680), (0.534, 0.695), (0.533, 0.712), 
                           (0.520, 0.738), (0.522, 0.697), (0.514, 0.682), (0.517, 0.582)],
            "wheels": [(0.501, 0.887), (0.528, 0.723), (0.557, 0.684), (0.613, 0.729), (0.606, 0.842), (0.576, 0.910)],
            "battery": [(0.527, 0.352), (0.486, 0.384), (0.542, 0.443), (0.578, 0.407), (0.528, 0.354)],
            "intake": [(0.324, 0.486), (0.387, 0.435), (0.428, 0.424), (0.460, 0.452), (0.452, 0.486), (0.418, 0.582), 
                       (0.400, 0.569), (0.408, 0.550), (0.382, 0.552), (0.355, 0.522), (0.354, 0.495), (0.332, 0.501), 
                       (0.320, 0.484), (0.343, 0.461)],
            "differential": [(0.634, 0.313), (0.616, 0.356), (0.635, 0.384), (0.647, 0.371), (0.661, 0.382), (0.664, 0.409), 
                             (0.674, 0.386), (0.669, 0.330), (0.644, 0.305)],
            "gearbox": [(0.612, 0.365), (0.637, 0.384), (0.645, 0.373), (0.661, 0.388), (0.663, 0.418), (0.656, 0.443), 
                        (0.607, 0.475), (0.577, 0.471), (0.600, 0.405), (0.609, 0.365)],
            "brakes": [(0.446, 0.780), (0.440, 0.697), (0.480, 0.659), (0.501, 0.670), (0.502, 0.731), (0.485, 0.772)],
        }
        
        # on parse le chemin absolu pour load le media local
        base_dir = os.path.dirname(os.path.abspath(__file__))
        video_path = os.path.join(base_dir, "ferrari_video_gui.mp4")
        self._load_video(video_path)
        
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        
        # on garde le timer a l'arret ici car il sera trigger manuellement a l'arrivée sur l'onglet
        
        if self.frames:
            self._display_current_frame()

    def start_video_playback(self):
        """Methode appelée par le main pour reset et lancer l'animation."""
        self.current_frame_idx = 0
        self.direction = 1
        self._display_current_frame()
        self.animation_timer.start(33)

    def _load_video(self, path):
        """Precharge l'ensemble des frames via opencv en memoire ram."""
        if not os.path.exists(path):
            print(f"Attention Video introuvable ({path})")
            return
            
        # VideoCapture permet d'ouvrir et de parser le stream video
        cap = cv2.VideoCapture(path)
        
        # boucle pour dump chaque frame du buffer opencv vers une liste locale
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_BGR888)
            self.frames.append(QPixmap.fromImage(q_img))
            
        cap.release()

    def _display_current_frame(self):
        """Affiche la frame en cours tout en maintenant l'aspect ratio."""
        if not self.frames:
            return
            
        pixmap = self.frames[self.current_frame_idx]
        
        # KeepAspectRatio evite la deformation et SmoothTransformation applique un lissage qu'on appelle bilineaire
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.video_label.setPixmap(scaled_pixmap)

    def _update_animation(self):
        """Fait avancer ou reculer la tete de lecture."""
        if not self.frames:
            return

        next_idx = self.current_frame_idx + self.direction
        
        if 0 <= next_idx < len(self.frames):
            self.current_frame_idx = next_idx
            self._display_current_frame()
        else:
            # on kill le timer aux extremites pour save le cpu
            self.animation_timer.stop()

    def mousePressEvent(self, event):
        """Detecte les clics utilisateur et declenche les actions sur la video."""
        if event.button() == Qt.MouseButton.LeftButton:
            last_frame_index = len(self.frames) - 1
            
            if self.current_frame_idx == last_frame_index:
                # on declenche le calcul de hitbox si l'animation est finie
                hit = self._check_click_zones(event.pos())
                
                # on inverse la lecture uniquement si le clic tombe dans le vide
                if not hit:
                    self.direction = -1
                    self.animation_timer.start(33)
            else:
                # si ca bouge deja on fait juste un reverse
                self.direction *= -1
                self.animation_timer.start(33)
                
        super().mousePressEvent(event)

    def _check_click_zones(self, pos):
        """Projette les clics sur l'image interne pour valider les masques polygonaux."""
        if not self.frames:
            return False
            
        lbl_w = self.video_label.width()
        lbl_h = self.video_label.height()
        
        pixmap = self.video_label.pixmap()
        if not pixmap:
            return False
            
        pix_w = pixmap.width()
        pix_h = pixmap.height()
        
        # on recalcule le decalage introduit par le scale aspect ratio
        offset_x = (lbl_w - pix_w) / 2
        offset_y = (lbl_h - pix_h) / 2
        
        px = pos.x() - offset_x
        py = pos.y() - offset_y
        
        if px < 0 or px > pix_w or py < 0 or py > pix_h:
            return False
            
        rel_x = px / pix_w
        rel_y = py / pix_h
        
        click_point = QPointF(rel_x, rel_y)
        
        # on boucle qui teste chaque shape mathematique
        for zone_name, points in self.zones.items():
            poly = QPolygonF([QPointF(x, y) for x, y in points])
            
            # OddEvenFill utilise l'algorithme du rayon pour valider la collision interne
            if poly.containsPoint(click_point, Qt.FillRule.OddEvenFill):
                self.gui.trigger_sensor_popup(zone_name)
                return True
                
        return False

    def resizeEvent(self, event):
        self._display_current_frame()
        super().resizeEvent(event)


class DashboardWidget(QWidget):
    """Tableau de bord 2D dynamique affichant les données en temps réel."""
    def __init__(self, gui_parent):
        super().__init__()
        self.gui = gui_parent
        self.setStyleSheet("background-color: #0a0a0a;") 
        
        # on lie un qtimer a l'event update() pour repeindre le hud a 30 fps
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(33)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        rpm = 0.0
        speed_kmh = 0.0
        gear = 1.0
        oil_temp = 20.0
        
        # on fetch les datas directement sur l'arbre memoire pour fluidifier l'aiguille
        if self.gui.sim_backend and self.gui.sim_backend.simulator and self.gui.sim_backend.simulator.system_root:
            try:
                root = self.gui.sim_backend.simulator.system_root
                rpm = root.engine.rpm.get_value()
                wheel_rpm = root.wheels.wheel_rpm.get_value()
                speed_kmh = (wheel_rpm * 60.0 * 2.2) / 1000.0
                gear = root.gearbox.gear.get_value()
                oil_temp = root.engine.oil_temp.get_value()
            except AttributeError:
                pass 

        left_cx, left_cy = width * 0.3, height * 0.5
        right_cx, right_cy = width * 0.7, height * 0.5
        radius = min(width, height) * 0.3

        self._draw_gauge(painter, left_cx, left_cy, radius, 
                         value=rpm, min_val=0, max_val=10000, 
                         title="RPM", unit="x1000", is_rpm=True)
        
        self._draw_gauge(painter, right_cx, right_cy, radius, 
                         value=speed_kmh, min_val=0, max_val=360, 
                         title="SPEED", unit="km/h", is_rpm=False)

        self._draw_digital_center(painter, width * 0.5, height * 0.5, gear, oil_temp)

    def _draw_gauge(self, painter, cx, cy, radius, value, min_val, max_val, title, unit, is_rpm):
        """Dessine un compteur circulaire avec graduations et aiguille."""
        painter.save()
        painter.translate(cx, cy)
        
        painter.setPen(QPen(QColor("#333333"), 4))
        painter.drawEllipse(QPointF(0, 0), radius, radius)
        
        # on dessine l'arc de la zone rouge si c'est le compte-tours
        if is_rpm:
            rect = QRectF(-radius, -radius, radius*2, radius*2)
            painter.setPen(QPen(QColor("#C41E3A"), 6))
            
            start_angle = -225 + (0.85 * 270)
            span_angle = 270 * 0.15
            # drawArc utilise des seizièmes de degres
            painter.drawArc(rect, int(-start_angle * 16), int(-span_angle * 16))

        # on calcule et dessine les graduations
        painter.setPen(QPen(QColor("#ffffff"), 2))
        painter.setFont(QFont("Arial", int(radius*0.1), QFont.Weight.Bold))
        
        steps = 10 if is_rpm else 12
        
        # boucle qui iter et pose chaque ligne selon l'angle
        for i in range(steps + 1):
            angle_deg = -225 + (i / steps) * 270
            angle_rad = math.radians(angle_deg)
            
            x_outer = radius * math.cos(angle_rad)
            y_outer = radius * math.sin(angle_rad)
            x_inner = (radius - 15) * math.cos(angle_rad)
            y_inner = (radius - 15) * math.sin(angle_rad)
            painter.drawLine(QPointF(x_inner, y_inner), QPointF(x_outer, y_outer))
            
            val_text = str(i) if is_rpm else str(int((i/steps) * max_val))
            x_text = (radius - 35) * math.cos(angle_rad) - 8
            y_text = (radius - 35) * math.sin(angle_rad) + 5
            painter.drawText(QPointF(x_text, y_text), val_text)

        painter.setPen(QColor("#aaaaaa"))
        painter.setFont(QFont("Arial", int(radius*0.12), QFont.Weight.Bold))
        painter.drawText(QRectF(-50, radius*0.3, 100, 30), Qt.AlignmentFlag.AlignCenter, title)
        painter.setFont(QFont("Arial", int(radius*0.08)))
        painter.drawText(QRectF(-50, radius*0.45, 100, 30), Qt.AlignmentFlag.AlignCenter, unit)

        # animation mathematique de la rotation de l'aiguille
        safe_val = max(min_val, min(value, max_val))
        val_angle = -225 + ((safe_val - min_val) / (max_val - min_val)) * 270
        
        # l'aiguille de base regarde vers le haut, on compense avec un +90
        painter.rotate(val_angle + 90)
        
        needle = QPolygonF([QPointF(-4, 0), QPointF(4, 0), QPointF(0, -radius + 10)])
        painter.setBrush(QColor("#C41E3A"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(needle)
        
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QPointF(0, 0), 8, 8)

        painter.restore()

    def _draw_digital_center(self, painter, cx, cy, gear, oil_temp):
        """Affiche les informations digitales au centre du tableau de bord."""
        painter.save()
        painter.translate(cx, cy)
        
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Arial", 40, QFont.Weight.Bold))
        gear_str = str(int(gear)) if gear > 0 else "N"
        painter.drawText(QRectF(-50, -50, 100, 100), Qt.AlignmentFlag.AlignCenter, gear_str)
        
        painter.setPen(QColor("#aaaaaa"))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(QRectF(-50, 20, 100, 20), Qt.AlignmentFlag.AlignCenter, "GEAR")

        temp_color = "#00ff00" if oil_temp < 110 else "#ffaa00"
        if oil_temp > 130: temp_color = "#ff0000"
        
        painter.setPen(QColor(temp_color))
        painter.setFont(QFont("Consolas", 14, QFont.Weight.Bold))
        painter.drawText(QRectF(-60, 80, 120, 30), Qt.AlignmentFlag.AlignCenter, f"OIL: {int(oil_temp)}°C")

        painter.restore()


class SynopticCanvas(QWidget):
    """Zone de dessin interne qui sera placée dans la ScrollArea."""
    def __init__(self, gui_parent):
        super().__init__()
        self.gui = gui_parent
        self.setMinimumSize(1100, 700) 

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), Qt.GlobalColor.white)

        # on draw le cable routing en dur
        pen = QPen(QColor("#777777"), 2, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawLine(QPointF(320, 130), QPointF(320, 200)) 
        painter.drawLine(QPointF(190, 90), QPointF(250, 220))  
        painter.drawLine(QPointF(330, 310), QPointF(450, 420)) 
        painter.drawLine(QPointF(410, 255), QPointF(450, 255)) 
        painter.drawLine(QPointF(590, 255), QPointF(650, 255)) 
        painter.drawLine(QPointF(790, 255), QPointF(850, 255)) 
        painter.drawLine(QPointF(920, 295), QPointF(920, 480)) 

        # boucle qui construit les boites d'interfaces pour tous les noeuds
        for key, node in self.gui.nodes.items():
            comp = self.gui._find_component_in_backend(key)
            
            if comp:
                # on scale dynamiquement la hitbox pour contenir le nombre de variables variables
                needed_height = 30 + (len(comp.observables) * 12) + 5
                node["rect"].setHeight(max(node["rect"].height(), needed_height))

            painter.setPen(QPen(Qt.GlobalColor.black, 2))
            painter.setBrush(QColor("#fcfcfc"))
            painter.drawRoundedRect(node["rect"], 8, 8)
            
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.drawText(node["rect"], Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter, node["label"])
            
            font = QFont("Consolas", 7)
            painter.setFont(font)
            
            # on instance l'outil metrics pour gerer la typo et mesurer l'encombrement memoire
            metrics = painter.fontMetrics()
            
            y_pos = node["rect"].top() + 25
            
            if comp:
                # sous-boucle pour injecter chaque variable connue dans la boite ui
                for obs_name, obs_obj in comp.observables.items():
                    display_text = f"• {obs_obj.display_name} [{obs_name}]"
                    
                    max_width = int(node["rect"].width() - 15)
                    
                    # elidedText coupe la string et ajoute des points de suspension si c'est trop large
                    elided_text = metrics.elidedText(display_text, Qt.TextElideMode.ElideRight, max_width)
                    
                    painter.drawText(int(node["rect"].left() + 10), int(y_pos), elided_text)
                    y_pos += 12

    def mousePressEvent(self, event):
        # boucle pour hit tester les boites cliquables du synoptique
        for key, node in self.gui.nodes.items():
            if node["rect"].contains(event.position()):
                self.gui.trigger_sensor_popup(key)
                return
        super().mousePressEvent(event)


class FerrariGUI(AbstractSystemGUI):
    """Conteneur maitre qui assemble les vues empilees."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # dictionnaire referencant les coordonnees des boites de la vue synoptique
        self.nodes = {
            "battery":      {"rect": QRectF(50, 50, 140, 100),  "label": "Batterie / Démarreur"},
            "intake":       {"rect": QRectF(250, 50, 140, 100), "label": "Admission d'Air"},
            "engine":       {"rect": QRectF(250, 200, 160, 110),"label": "Moteur V12"},
            "cooling":      {"rect": QRectF(450, 50, 140, 100), "label": "Refroidissement"},
            "exhaust":      {"rect": QRectF(450, 380, 140, 100),"label": "Échappement"},
            "transmission": {"rect": QRectF(450, 215, 140, 100),"label": "Arbre de Transmission"},
            "gearbox":      {"rect": QRectF(650, 215, 140, 110),"label": "Boîte de Vitesses DCT"},
            "differential": {"rect": QRectF(850, 215, 140, 100),"label": "Différentiel (E-Diff)"},
            "brakes":       {"rect": QRectF(650, 480, 140, 100),"label": "Freins Carbone"},
            "suspension":   {"rect": QRectF(450, 550, 140, 100),"label": "Suspensions"},
            "wheels":       {"rect": QRectF(850, 480, 140, 100),"label": "Roues & Pneus"}
        }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # on utilise QStackedWidget pour superposer les ecrans de facon optimisee
        self.stack = QStackedWidget()
        
        self.video_widget = VideoWidget(self)
        self.stack.addWidget(self.video_widget) 
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.canvas = SynopticCanvas(self)
        self.scroll_area.setWidget(self.canvas)
        self.stack.addWidget(self.scroll_area) 
        
        self.dashboard = DashboardWidget(self)
        self.stack.addWidget(self.dashboard) 
        
        layout.addWidget(self.stack)

        # bouton pour cycler l'affichage
        self.btn_switch_view = QPushButton("Mode: Schéma")
        self.btn_switch_view.setParent(self) 
        self.btn_switch_view.setFixedSize(130, 30) 
        self.btn_switch_view.clicked.connect(self.toggle_view)
        
        # bouton de bypass des capteurs
        self.btn_master = self.create_global_activate_button("Activer les capteurs")
        self.btn_master.setParent(self) 
        self.btn_master.setFixedSize(130, 30) 
        
        # on ecrit un qss en dur pour pimper l'aspect des boutons
        btn_style = """
            QPushButton {
                background-color: #2c3e50;
                color: white;
                font-size: 11px;
                font-weight: bold;
                border-radius: 5px;
                border: 1px solid #34495e;
            }
            QPushButton:hover {
                background-color: #C41E3A; 
                border: 1px solid #96162c;
            }
        """
        self.btn_switch_view.setStyleSheet(btn_style)
        self.btn_master.setStyleSheet(btn_style)
        
        # on trigger automatiquement l'animation par defaut
        self.video_widget.start_video_playback()

    def toggle_view(self):
        """Bascule cyclique entre les differents ecrans du stack."""
        current_idx = self.stack.currentIndex()
        
        if current_idx == 0:
            self.stack.setCurrentIndex(1)
            self.btn_switch_view.setText("Mode: Cockpit")
            
            # on stop le thread de rafraichissement video en background
            self.video_widget.animation_timer.stop()
        elif current_idx == 1:
            self.stack.setCurrentIndex(2)
            self.btn_switch_view.setText("Mode: Vidéo")
        else:
            self.stack.setCurrentIndex(0)
            self.btn_switch_view.setText("Mode: Schéma")
            
            # on force le reset de l'animation quand on repop sur l'onglet video
            self.video_widget.start_video_playback()

    def resizeEvent(self, event):
        """On recalcule l'ancrage des overlay ui lors du resize de la fenetre."""
        super().resizeEvent(event)
        
        if hasattr(self, 'btn_switch_view'):
            self.btn_switch_view.move(20, 20)
            
            # raise passe le composant graphique au tout premier plan
            self.btn_switch_view.raise_() 
            
        if hasattr(self, 'btn_master'):
            self.btn_master.move(self.width() - 150, 20)
            self.btn_master.raise_()