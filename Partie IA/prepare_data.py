import csv
import json
import math
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
GLOBAL_STATS_PATH = PROCESSED_DATA_DIR / "global_stats.json"
BINARY_COLUMNS = {"battery.relay_state"}
SCALED_COLUMNS = {"gearbox.gear": 7.0}


def compute_mean(values):
    """Retourne la moyenne d'une colonne numerique."""

    return sum(values) / len(values)


def compute_std(values, mean):
    """Retourne l'ecart-type d'une colonne numerique."""

    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def normalize_values(values, mean, std):
    """Retourne les valeurs normalisees d'une colonne."""

    normalized = []
    for value in values:
        normalized.append((value - mean) / std)
    return normalized


def load_csv_data(csv_path):
    """Charge un CSV brut en memoire pour le preparer."""

    with csv_path.open("r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        if reader.fieldnames is None:
            raise ValueError(f"Le fichier CSV est vide ou invalide : {csv_path}")

        feature_columns = []
        for column in reader.fieldnames:
            if column != "Timestamp":
                feature_columns.append(column)

        column_values = {}
        for column in feature_columns:
            column_values[column] = []

        for row in reader:
            for column in feature_columns:
                column_values[column].append(float(row[column]))

    return feature_columns, column_values


def compute_global_stats(global_column_values, feature_columns):
    """Calcule une mean/std globale pour chaque observable non constante."""

    global_stats = {}

    for column in feature_columns:
        if column in BINARY_COLUMNS:
            continue
        if column in SCALED_COLUMNS:
            continue

        values = global_column_values[column]
        mean = compute_mean(values)
        std = compute_std(values, mean)

        if not std:
            print(f"Colonne ignoree pour la normalisation car constante : {column}")
            continue

        global_stats[column] = {
            "mean": mean,
            "std": std,
        }

    return global_stats


def write_global_stats(global_stats):
    """Ecrit le scaler global dans un fichier JSON."""

    GLOBAL_STATS_PATH.write_text(json.dumps(global_stats, indent=2), encoding="utf-8")
    print(f"Scaler global ecrit dans {GLOBAL_STATS_PATH}.")


def write_normalized_csv(csv_path, feature_columns, column_values, global_stats):
    """Ecrit un CSV normalise avec le scaler global."""

    normalized_values = {}
    normalized_columns = []

    for column in feature_columns:
        if column in BINARY_COLUMNS:
            normalized_values[column] = column_values[column]
            normalized_columns.append(column)
            continue

        if column in SCALED_COLUMNS:
            scale = SCALED_COLUMNS[column]
            normalized_values[column] = []
            for value in column_values[column]:
                normalized_values[column].append(value / scale)
            normalized_columns.append(column)
            continue

        if column not in global_stats:
            continue

        mean = global_stats[column]["mean"]
        std = global_stats[column]["std"]
        normalized_values[column] = normalize_values(column_values[column], mean, std)
        normalized_columns.append(column)

    normalized_output_path = PROCESSED_DATA_DIR / f"{csv_path.stem}_normalized.csv"

    with normalized_output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        writer.writerow(normalized_columns)

        if not normalized_columns:
            print(f"Aucune colonne exploitable dans {csv_path}")
            return

        first_column = normalized_columns[0]
        num_rows = len(normalized_values[first_column])
        for row_index in range(num_rows):
            row = []
            for column in normalized_columns:
                row.append(normalized_values[column][row_index])
            writer.writerow(row)

    print(f"CSV normalise ecrit dans {normalized_output_path}.")


def prepare_all_data(csv_files):
    """Prepare tous les CSV avec un seul scaler global."""

    datasets = []
    global_column_values = {}
    reference_feature_columns = None

    for csv_path in csv_files:
        print(f"Chargement du fichier {csv_path}...")
        feature_columns, column_values = load_csv_data(csv_path)

        # le premier fichier sert de reference pour l'ordre des colonnes
        if reference_feature_columns is None:
            reference_feature_columns = feature_columns
            for column in feature_columns:
                global_column_values[column] = []
        elif feature_columns != reference_feature_columns:
            raise ValueError(f"Colonnes incompatibles dans le fichier : {csv_path}")

        for column in feature_columns:
            global_column_values[column].extend(column_values[column])

        datasets.append((csv_path, feature_columns, column_values))

    if reference_feature_columns is None:
        print("Aucune colonne exploitable trouvee.")
        return

    print("Calcul du scaler global...")
    global_stats = compute_global_stats(global_column_values, reference_feature_columns)
    write_global_stats(global_stats)

    for csv_path, feature_columns, column_values in datasets:
        print(f"Normalisation globale du fichier {csv_path}...")
        write_normalized_csv(csv_path, feature_columns, column_values, global_stats)

    print("La preparation globale est terminee.")


if __name__ == "__main__":
    csv_files = sorted(RAW_DATA_DIR.glob("*.csv"))

    if not RAW_DATA_DIR.exists():
        print(f"Dossier introuvable : {RAW_DATA_DIR}")
    elif not csv_files:
        print("Aucun CSV trouve dans ml/data/raw.")
    else:
        prepare_all_data(csv_files)
