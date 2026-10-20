"""Point d'entrée de GADMAPS : Générateur d’Anomalies et de Données pour la MAintenance Prédictive de Systèmes."""

import sys
import os

import controller

# on setup le chemin absolu du projet courant pour clean les imports
project_root = os.path.dirname(os.path.abspath(__file__))

# on check si le dossier est dans le path systeme, sinon on l'ajoute
# methode necessaire pour que python trouve nos modules locaux sans faire d'erreur d'import
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from controller import AppController

def main():
    """Fonction principale qui s'occupe d'initialiser l'interface graphique et de faire le pont avec le backend."""
    # on instancie l'app pyqt
    app = QApplication(sys.argv)
    
    # on lance le controleur global qui gere la vue et le backend
    controller = AppController()
    
    # on affiche la fenetre
    # showMaximized permet d'ouvrir directement l'application en plein ecran
    controller.view.showMaximized()   

    # on lance la boucle d'evenements pyqt
    sys.exit(app.exec())

if __name__ == "__main__":
    main()