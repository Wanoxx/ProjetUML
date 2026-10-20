from pathlib import Path
import csv
import json
from keras import Input, Model
from keras.layers import Dense
from numpy import array


BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
TRAIN_TEST_DATA_DIR = BASE_DIR / "data" / "train_test"
MODELS_DIR = BASE_DIR / "models"
MODEL_PATH = MODELS_DIR / "autoencoder.keras"
GLOBAL_STATS_PATH = PROCESSED_DATA_DIR / "global_stats.json"
BINARY_COLUMNS = {"battery.relay_state"}
SCALED_COLUMNS = {"gearbox.gear": 7.0}

def load_prepared_data(csv_path):
    """Charge les données préparées pour l'entraînement de l'autoencoder."""
    with csv_path.open("r", newline="", encoding="utf-8") as csvfile:
        # on lit les données préparées à partir du CSV
        reader = csv.DictReader(csvfile, delimiter=";")
        if reader.fieldnames is None:
            print("Le fichier CSV est vide ou invalide.")
            return  
        
        feature_columns = list()
        for column in reader.fieldnames:
            if column != "Timestamp":
                feature_columns.append(column)

        # on construit une liste de listes pour les données d'entraînement
        dataset_rows = list()
        # pour chaque ligne du CSV 
        for row in reader:
            values = list()
            for column in feature_columns:
                # on ajoute les valeurs numériques dans la liste des valeurs de la ligne
                values.append(float(row[column]))
            dataset_rows.append(values)

    return feature_columns, dataset_rows


def load_raw_data(csv_path):
    """Charge un CSV brut en conservant les colonnes utiles."""

    with csv_path.open("r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        if reader.fieldnames is None:
            print(f"Le fichier CSV est vide ou invalide : {csv_path}")
            return None, None

        feature_columns = []
        for column in reader.fieldnames:
            if column != "Timestamp":
                feature_columns.append(column)

        dataset_rows = []
        for row in reader:
            values = {}
            for column in feature_columns:
                values[column] = float(row[column])
            dataset_rows.append(values)

    return feature_columns, dataset_rows


def normalize_raw_rows(feature_columns, dataset_rows, global_stats):
    """Normalise un CSV brut avec le scaler global du train."""

    normalized_columns = []
    for column in feature_columns:
        if column in BINARY_COLUMNS or column in SCALED_COLUMNS or column in global_stats:
            normalized_columns.append(column)

    normalized_rows = []
    for row in dataset_rows:
        normalized_row = []
        for column in normalized_columns:
            if column in BINARY_COLUMNS:
                normalized_row.append(row[column])
                continue

            if column in SCALED_COLUMNS:
                normalized_row.append(row[column] / SCALED_COLUMNS[column])
                continue

            mean_value = global_stats[column]["mean"]
            std_value = global_stats[column]["std"]
            normalized_row.append((row[column] - mean_value) / std_value)
        normalized_rows.append(normalized_row)

    return normalized_columns, normalized_rows


def load_train_dataset():
    """Charge les fichiers normalisés d'entraînement correspondant aux CSV de raw/."""

    raw_csv_files = sorted(RAW_DATA_DIR.glob("*.csv"))
    if not raw_csv_files:
        print("Aucun fichier CSV brut trouvé dans ml/data/raw.")
        return None, None

    all_dataset_rows = []
    reference_feature_columns = None

    for raw_csv_path in raw_csv_files:
        normalized_csv_path = PROCESSED_DATA_DIR / f"{raw_csv_path.stem}_normalized.csv"
        if not normalized_csv_path.exists():
            print(f"CSV normalisé introuvable pour {raw_csv_path.name} : {normalized_csv_path}")
            return None, None

        feature_columns, dataset_rows = load_prepared_data(normalized_csv_path)

        if reference_feature_columns is None:
            reference_feature_columns = feature_columns
        elif feature_columns != reference_feature_columns:
            print(f"Colonnes incompatibles dans le fichier : {normalized_csv_path}")
            return None, None

        print(f"Fichier train chargé : {normalized_csv_path}")
        print(f"Nombre de lignes dans ce fichier : {len(dataset_rows)}")
        all_dataset_rows.extend(dataset_rows)

    return reference_feature_columns, all_dataset_rows


def load_validation_dataset(reference_feature_columns):
    """Charge les fichiers bruts de train_test/ et les normalise avec le scaler global."""

    validation_csv_files = sorted(TRAIN_TEST_DATA_DIR.glob("*.csv"))
    if not validation_csv_files:
        return None

    global_stats = load_global_stats()
    all_dataset_rows = []

    for csv_path in validation_csv_files:
        feature_columns, dataset_rows = load_raw_data(csv_path)
        if feature_columns is None or dataset_rows is None:
            return None

        normalized_columns, normalized_rows = normalize_raw_rows(
            feature_columns,
            dataset_rows,
            global_stats,
        )

        if normalized_columns != reference_feature_columns:
            print(f"Colonnes incompatibles dans le fichier de validation : {csv_path}")
            return None

        print(f"Fichier validation charge : {csv_path}")
        print(f"Nombre de lignes dans ce fichier : {len(normalized_rows)}")
        all_dataset_rows.extend(normalized_rows)

    return array(all_dataset_rows, dtype=float)

def build_autoencoder(input_dim):
    """Construit un autoencoder Keras avec une architecture simple : 
    4 couches denses avec avec 16 neurones pour faire le bottleneck qui 
    nous permet de réduire la dimensionnalité des données d'entrée."""
    
    input_layer = Input(shape=(input_dim,))
    encoded = Dense(32, activation="relu")(input_layer)
    bottleneck = Dense(16, activation="relu")(encoded)
    decoded = Dense(32, activation="relu")(bottleneck)
    output_layer = Dense(input_dim, activation="linear")(decoded)

    model = Model(inputs=input_layer, outputs=output_layer)
    return model

def train_autoencoder(model, train_rows, validation_rows=None):
    """Entraîne un autoencoder Keras sur les données préparées."""

    # on compile le modele avec Adam et la loss mse
    model.compile(optimizer="adam", loss="mse")

    # epochs = nombre de passages sur les donnees
    # batch_size = taille des paquets de lignes
    fit_kwargs = {
        "x": train_rows,
        "y": train_rows,
        "epochs": 10,
        "batch_size": 32,
        "verbose": 1,
    }

    if validation_rows is not None and len(validation_rows) > 0:
        fit_kwargs["validation_data"] = (validation_rows, validation_rows)

    history = model.fit(**fit_kwargs)
    return history
    


def main():
    """le main de ce module pour lancer le training de l'autoencoder"""
    reference_feature_columns, all_dataset_rows = load_train_dataset()
    if reference_feature_columns is None or all_dataset_rows is None:
        return

    print(f"Nombre total de colonnes train : {len(reference_feature_columns)}")
    print(f"Nombre total de lignes train : {len(all_dataset_rows)}")

    if all_dataset_rows:
        print("Première ligne train :")
        print(all_dataset_rows[0])

    train_array = array(all_dataset_rows, dtype=float)
    validation_array = load_validation_dataset(reference_feature_columns)
    if validation_array is not None:
        print(f"Nombre total de lignes validation : {len(validation_array)}")

    input_dim = len(reference_feature_columns)

    model = build_autoencoder(input_dim)
    print("Resume du modele :")
    model.summary()

    history = train_autoencoder(model, train_array, validation_array)
    print("Entraînement terminé.")
    print(f"Loss finale : {history.history['loss'][-1]:.6f}")

    model.save(MODEL_PATH)
    print(f"Modèle sauvegardé dans {MODEL_PATH}")


if __name__ == "__main__":
    main()
