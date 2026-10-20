"""Teste un autoencoder sauvegarde sur un CSV brut."""

import csv
import json
from pathlib import Path

from keras.models import load_model
from numpy import array, mean


BASE_DIR = Path(__file__).resolve().parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "models"
RESULTS_DIR = BASE_DIR / "results"
TEST_RAW_DIR = BASE_DIR / "data" / "test_raw"
MODEL_PATH = MODELS_DIR / "autoencoder.keras"
GLOBAL_STATS_PATH = PROCESSED_DATA_DIR / "global_stats.json"
BINARY_COLUMNS = {"battery.relay_state"}
SCALED_COLUMNS = {"gearbox.gear": 7.0}
SMOOTHING_WINDOW = 21
THRESHOLD = 0.4
TEST_FILES = [
    TEST_RAW_DIR / "ferrari_2026-04-21_02-33-43.csv",
    TEST_RAW_DIR / "ferrari_2026-04-21_11-41-21_10000.csv",
]


def load_global_stats():
    """Charge les statistiques globales du scaler."""

    with GLOBAL_STATS_PATH.open("r", encoding="utf-8") as json_file:
        return json.load(json_file)


def load_raw_csv(csv_path):
    """Charge les timestamps et les valeurs du CSV brut."""

    with csv_path.open("r", newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile, delimiter=";")
        rows = list(reader)

    if not rows:
        raise ValueError(f"Le fichier CSV est vide ou invalide : {csv_path}")

    header = rows[0]
    data_rows = rows[1:]

    if "Timestamp" not in header:
        raise ValueError("Le CSV de test doit contenir une colonne Timestamp.")

    feature_columns = []
    for column in header:
        if column != "Timestamp":
            feature_columns.append(column)

    timestamps = []
    column_values = {}
    for column in feature_columns:
        column_values[column] = []

    timestamp_index = header.index("Timestamp")
    column_indexes = {}
    for column in feature_columns:
        column_indexes[column] = header.index(column)

    for row in data_rows:
        if not row:
            continue
        if len(row) != len(header):
            raise ValueError(f"Le fichier CSV est vide ou invalide : {csv_path}")
        timestamps.append(float(row[timestamp_index]))
        for column in feature_columns:
            column_values[column].append(float(row[column_indexes[column]]))

    return timestamps, feature_columns, column_values


def normalize_columns(feature_columns, column_values, global_stats):
    """Applique la meme normalisation que celle utilisee pour l'entrainement."""

    normalized_columns = []
    normalized_rows = []

    for column in feature_columns:
        if column in BINARY_COLUMNS:
            normalized_columns.append(column)
            continue

        if column in SCALED_COLUMNS:
            normalized_columns.append(column)
            continue

        if column in global_stats:
            normalized_columns.append(column)

    if not normalized_columns:
        return normalized_columns, normalized_rows

    first_column = normalized_columns[0]
    num_rows = len(column_values[first_column])

    for row_index in range(num_rows):
        row = []
        for column in normalized_columns:
            if column in BINARY_COLUMNS:
                row.append(column_values[column][row_index])
                continue

            if column in SCALED_COLUMNS:
                row.append(column_values[column][row_index] / SCALED_COLUMNS[column])
                continue

            mean_value = global_stats[column]["mean"]
            std_value = global_stats[column]["std"]
            row.append((column_values[column][row_index] - mean_value) / std_value)
        normalized_rows.append(row)

    return normalized_columns, normalized_rows


def compute_reconstruction_errors(model, dataset_array):
    """Calcule l'erreur de reconstruction moyenne par ligne."""

    reconstructed = model.predict(dataset_array, verbose=0)
    squared_errors = (dataset_array - reconstructed) ** 2
    return mean(squared_errors, axis=1), reconstructed


def smooth_errors(errors, window_size):
    """Lisse les scores avec une moyenne glissante centree."""

    if window_size <= 1:
        return errors

    smoothed_errors = []
    half_window = window_size // 2

    for index in range(len(errors)):
        start_index = max(0, index - half_window)
        end_index = min(len(errors), index + half_window + 1)
        smoothed_errors.append(float(mean(errors[start_index:end_index])))

    return array(smoothed_errors, dtype=float)


def write_results(csv_path, timestamps, raw_errors, smoothed_errors):
    """Ecrit un CSV avec les scores d'anomalie par ligne."""

    output_path = RESULTS_DIR / f"{csv_path.stem}_scores_smooth{SMOOTHING_WINDOW}.csv"

    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, delimiter=";")
        header = ["Timestamp", "reconstruction_error"]
        header.append("smoothed_reconstruction_error")
        header.append("is_anomaly")
        writer.writerow(header)

        for timestamp, raw_error, smoothed_error in zip(timestamps, raw_errors, smoothed_errors):
            row = [timestamp, float(raw_error)]
            row.append(float(smoothed_error))
            row.append(int(smoothed_error > THRESHOLD))
            writer.writerow(row)

    return output_path


def test_one_csv(csv_path, model, global_stats):
    """Teste un seul csv."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modele introuvable : {MODEL_PATH}")

    if not GLOBAL_STATS_PATH.exists():
        raise FileNotFoundError(f"Scaler global introuvable : {GLOBAL_STATS_PATH}")

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV introuvable : {csv_path}")

    timestamps, feature_columns, column_values = load_raw_csv(csv_path)
    normalized_columns, normalized_rows = normalize_columns(feature_columns, column_values, global_stats)

    if not normalized_columns:
        raise ValueError("Aucune colonne exploitable dans le CSV de test.")

    dataset_array = array(normalized_rows, dtype=float)
    raw_errors, _ = compute_reconstruction_errors(model, dataset_array)
    smoothed_errors = smooth_errors(raw_errors, SMOOTHING_WINDOW)
    output_path = write_results(csv_path, timestamps, raw_errors, smoothed_errors)



def main():
    """Charge le modele puis teste les deux csv de test."""

    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Modele introuvable : {MODEL_PATH}")

    if not GLOBAL_STATS_PATH.exists():
        raise FileNotFoundError(f"Scaler global introuvable : {GLOBAL_STATS_PATH}")

    global_stats = load_global_stats()
    model = load_model(MODEL_PATH)

    for csv_path in TEST_FILES:
        test_one_csv(csv_path, model, global_stats)


if __name__ == "__main__":
    main()
