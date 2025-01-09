import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

IMG_PATH = Path(__file__).parents[1] / "img"

DATA_PATH = (
    Path(__file__).parents[1] / "data" / "serial_data_Felix_2025-01-09_17-39-41.csv"
)
# print("CSV-Pfad:", DATA_PATH)

# ---------------------------------------------
# 1) CSV als Text einlesen
# ---------------------------------------------
with open(DATA_PATH, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Erste Zeile enthält den Header, den überspringen wir
lines = lines[1:]

# ---------------------------------------------
# 2) Daten-Arrays anlegen
# ---------------------------------------------
times_left = []
vals_left = []
times_right = []
vals_right = []

# ---------------------------------------------
# 3) Zeilen parsen
# ---------------------------------------------
for line in lines:
    line = line.strip()
    if not line:
        continue  # leere Zeilen ignorieren

    # CSV-Spalten: timestamp_str, position, value_str
    cols = line.split(",")
    if len(cols) < 3:
        continue  # ungültige Zeile?

    timestamp_str, position_str, value_str = cols
    timestamp = float(timestamp_str)
    value = float(value_str)

    if value > 500:
        continue
    # Nach Position filtern
    if position_str.strip() == "Left":
        times_left.append(timestamp)
        vals_left.append(value)
    elif position_str.strip() == "Right":
        times_right.append(timestamp)
        vals_right.append(value)

# ---------------------------------------------
# 4) Zeit normalisieren (t=0 beim kleinsten Timestamp)
# ---------------------------------------------
if len(times_left) == 0 and len(times_right) == 0:
    raise ValueError("Keine Daten gefunden!")

t0 = min(times_left + times_right)
times_left_rel = [t - t0 for t in times_left]
times_right_rel = [t - t0 for t in times_right]

# ---------------------------------------------
# 5) Plot 1: Left & Right vs. Zeit
# ---------------------------------------------
plt.figure(figsize=(10, 5))
plt.plot(times_left_rel, vals_left, label="Left", marker="o", markersize=2)
plt.plot(times_right_rel, vals_right, label="Right", marker="o", markersize=2)

plt.title("Left- und Right-Werte vs. Zeit (ab 0 Sekunden)")
plt.xlabel("Zeit [s] (relativ zum ersten Messwert)")
plt.ylabel("Wert [kg]")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(IMG_PATH / "Messdaten.png")
plt.cla()
# plt.show()

# ---------------------------------------------
# 6) Plot 2: Differenz (Left - Right) vs. Zeit
# ---------------------------------------------
# ACHTUNG: Hier gehen wir davon aus, dass die "Left"-
# und "Right"-Werte 1-zu-1 zusammengehören (gleiche Anzahl
# und identische Zeitstempel). Wenn das nicht so ist,
# muss man sie auf gemeinsame Timestamps matchen.
# Für eine einfache Demo nehmen wir an:
#   times_left[i] ~ times_right[i].
# Dann plotten wir difference[i] = vals_left[i] - vals_right[i].

min_length = min(len(vals_left), len(vals_right))
common_times = times_left_rel[:min_length]
difference = [vals_left[i] - vals_right[i] for i in range(min_length)]

plt.figure(figsize=(10, 4))
plt.plot(common_times, difference, marker="o", markersize=2, color="purple")
plt.title("Differenz (Left - Right) vs. Zeit")
plt.xlabel("Zeit [s] (relativ zum ersten Messwert)")
plt.ylabel("Left - Right [kg]")
plt.grid(True)
plt.tight_layout()
plt.savefig(IMG_PATH / "Differenz.png")
plt.cla()
# plt.show()


# Plot 3:
# times_left = []
# vals_left = []
# times_right = []
# vals_right = []
person_weight = 60
average_weight = person_weight / 2

left = [abs(vals_left[i] - average_weight) for i in range(min_length)]
right = [abs(vals_right[i] - average_weight) for i in range(min_length)]

plt.figure(figsize=(10, 4))
plt.plot(common_times, left, marker="o", markersize=2, color="blue")
plt.plot(common_times, right, marker="o", markersize=2, color="red")
plt.title("Average Offset")
plt.xlabel("Zeit [s] (relativ zum ersten Messwert)")
plt.ylabel("Kraft Delta [kg]")
plt.grid(True)
plt.tight_layout()
plt.savefig(IMG_PATH / "Anys Idea.png")
plt.cla()
# plt.show()


print(f"Plots for {DATA_PATH} have been created")
