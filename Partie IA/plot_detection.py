import csv
from pathlib import Path

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BASE_DIR / "results"
TEST_RAW_DIR = BASE_DIR / "data" / "test_raw"
COMPARISONS = [
    (
        RESULTS_DIR / "ferrari_2026-04-21_02-33-43_scores_smooth21.csv",
        TEST_RAW_DIR / "ferrari_2026-04-21_02-33-43.csv",
    ),
    (
        RESULTS_DIR / "ferrari_2026-04-21_11-41-21_10000_scores_smooth21.csv",
        TEST_RAW_DIR / "ferrari_2026-04-21_11-41-21_10000.csv",
    ),
]


def load_detected_curve(scores_csv):
    """Charge les timestamps et la courbe detectee depuis le CSV de scores."""

    with scores_csv.open("r", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter=";")
        if reader.fieldnames is None:
            raise ValueError(f"CSV invalide : {scores_csv}")

        if "Timestamp" not in reader.fieldnames:
            raise ValueError("Le CSV de scores doit contenir une colonne Timestamp.")
        if "is_anomaly" not in reader.fieldnames:
            raise ValueError("Le CSV de scores doit contenir une colonne is_anomaly.")

        timestamps = []
        detected = []
        for row in reader:
            timestamps.append(float(row["Timestamp"]))
            detected.append(int(row["is_anomaly"]))

    return timestamps, detected


def load_anomaly_events(anomalies_csv):
    """Charge les evenements d'injection/resolution."""

    with anomalies_csv.open("r", newline="", encoding="utf-8") as csvfile:
        first_line = csvfile.readline()
        delimiter = ";" if ";" in first_line else ","
        csvfile.seek(0)
        reader = csv.DictReader(csvfile, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ValueError(f"CSV invalide : {anomalies_csv}")

        events = []
        for row in reader:
            events.append(
                {
                    "time": float(row["global_time"]),
                    "component_name": row["component_name"].strip(),
                    "anomaly_name": row["anomaly_name"].strip(),
                    "action": row["action"].strip().lower(),
                }
            )

    events.sort(key=lambda event: event["time"])
    return events


def build_truth_curve(timestamps, events):
    """Construit une courbe binaire de verite terrain a partir des evenements."""

    truth = []
    active_anomalies = set()
    event_index = 0

    for timestamp in timestamps:
        while event_index < len(events) and events[event_index]["time"] <= timestamp:
            event = events[event_index]
            anomaly_key = (event["component_name"], event["anomaly_name"])
            if event["action"] == "inject":
                active_anomalies.add(anomaly_key)
            elif event["action"] == "resolve":
                active_anomalies.discard(anomaly_key)
            event_index += 1

        truth.append(1 if active_anomalies else 0)

    return truth


def plot_curves(timestamps, truth, detected, output_path):
    """Trace les deux courbes sur deux graphes et sauvegarde l'image."""

    figure, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=True)

    axes[0].step(timestamps, truth, where="post", linewidth=2, color="tab:blue")
    axes[0].set_ylim(-0.1, 1.1)
    axes[0].set_ylabel("Reelle")
    axes[0].set_title("Anomalies reelles")
    axes[0].grid(True, alpha=0.3)

    axes[1].step(timestamps, detected, where="post", linewidth=2, color="tab:red")
    axes[1].set_ylim(-0.1, 1.1)
    axes[1].set_xlabel("Temps")
    axes[1].set_ylabel("Detectee")
    axes[1].set_title("Anomalies detectees par le modele")
    axes[1].grid(True, alpha=0.3)

    figure.suptitle("Comparaison : verite terrain vs detection modele")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_one_comparison(scores_csv, anomalies_csv):
    """Trace une comparaison pour un seul couple de fichiers."""
    if not scores_csv.exists():
        raise FileNotFoundError(f"CSV de scores introuvable : {scores_csv}")
    if not anomalies_csv.exists():
        raise FileNotFoundError(f"CSV d'anomalies introuvable : {anomalies_csv}")

    timestamps, detected = load_detected_curve(scores_csv)
    events = load_anomaly_events(anomalies_csv)
    truth = build_truth_curve(timestamps, events)
    output_path = RESULTS_DIR / f"{scores_csv.stem}_comparison.png"
    plot_curves(timestamps, truth, detected, output_path)
    print(f"Graphe sauvegarde dans {output_path}")


def main():
    """Trace les deux comparaisons."""

    for scores_csv, anomalies_csv in COMPARISONS:
        plot_one_comparison(scores_csv, anomalies_csv)


if __name__ == "__main__":
    main()
