# GADMAPS - Générateur d'Anomalies et de Données pour la MAintenance Prédictive de Systèmes

## Présentation du projet

GADMAPS est un outil de simulation physique et de génération de données conçu pour tester et éprouver des systèmes de maintenance prédictive. Il permet de modéliser un système physique complet, par exemple une Ferrari 812 Superfast.

Le dépôt contient également une partie IA (détection d'anomalies par autoencodeur) et les documents de conception (compte rendu UML, exigences, dictionnaire).

## Contenu du dépôt

* [`GADMAPS/`](GADMAPS/) : l'application principale (simulation physique + interface PyQt6).
* [`Partie IA/`](Partie IA/) : entraînement et test d'un autoencodeur pour la détection d'anomalies.
* [`Compte_rendu.pdf`](Compte_rendu.pdf), [`Exigences.pdf`](Exigences.pdf), [`Dictionnaire.pdf`](Dictionnaire.pdf) : documents de conception.

## Architecture du projet

Le projet suit une architecture claire séparant la logique métier, l'interface (inspirée du modèle MVC) et les tests.

* `core/` : Contient principalement les classes abstraites fondamentales (`AbstractComponent`, `AbstractObservable`, `MessageBus`, `Sensor`, etc...).
* `test_models/ferrari/` : Implémentation concrète d'un véhicule complet avec ses sous-systèmes (Moteur V12, Boîte DCT, Freins Carbone, etc...) et son interface (`FerrariGUI.py`).
* `test_technique/` : Suite de tests automatisés (unitaires, intégration, robustesse).
* `data_output/` : Dossier de destination pour l'export des données de simulation (CSV).
* `controller.py` et `view.py` : Contrôleurs et vues de l'interface principale PyQt6.
* `Simulator.py` et `ModelBuilder.py` : coeur du moteur de simulation et de validation des imports.

## Prérequis et Installation

Ce projet nécessite Python 3.10 ou supérieur. Afin d'éviter les conflits de dépendances avec votre système (notamment pour PyQt6 et OpenCV), l'utilisation d'un environnement virtuel est fortement recommandée.

### 1. Créer l'environnement virtuel
Ouvrez un terminal dans le dossier `GADMAPS` (là où se trouve `main.py`) :
```bash
python -m venv venv
```

### 2. Activer l'environnement virtuel
* Sous Windows (Invite de commandes / PowerShell) :
  ```bash
  venv\Scripts\activate
  ```
* Sous macOS / Linux :
  ```bash
  source venv/bin/activate
  ```
(L'indicateur `(venv)` doit apparaître au début de votre ligne de commande).

### 3. Installer les dépendances
Installez les paquets requis listés dans le fichier `requirements.txt` :
```bash
pip install -r requirements.txt
```

## Mode d'Emploi

### Lancement de l'application
Assurez-vous que votre environnement virtuel est activé, puis lancez le point d'entrée principal :
```bash
python main.py
```

### Déroulement d'une simulation
Une fois dans le logiciel, vous pouvez importer le dossier Ferrari pour tester le logiciel avec un modèle métier complet. Vous pouvez également tester les anomalies avec `anomalies_ferrari_realistic_10000.csv`.
