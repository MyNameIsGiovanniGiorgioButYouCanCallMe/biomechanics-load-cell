#!/usr/bin/env python3
"""
weight_logger.py

CLI-Tool zum Empfangen von Gewichtsdaten von einem Arduino (o. Ä.) über eine serielle Schnittstelle.
Die Daten werden nach Erkennen von "links" oder "rechts" zeilenweise in einer CSV-Datei gespeichert.

CSV-Format:
    Unix Timestamp, Position, Value [kg]
"""

import argparse
import csv
import time
import threading
from datetime import datetime
from pathlib import Path

# Optional: falls pyserial nicht installiert ist, gibt es nur einen Warnhinweis
try:
    import serial
except ImportError:
    serial = None
    print(
        "WARNUNG: 'pyserial' ist nicht installiert. Es können keine Daten empfangen werden."
    )

# Globale Variablen für den Datenaustausch zwischen Threads
ser = None
connected = False
data_file_path = None


def connect_to_serial(port: str, baudrate: int):
    """
    Baut eine serielle Verbindung auf. Schlägt es fehl, wird alle 5 Sekunden erneut versucht.
    """
    global ser, connected
    if serial is None:
        print("Das 'serial'-Modul ist nicht verfügbar. Verbindung nicht möglich.")
        return

    while True:
        try:
            ser = serial.Serial(port, baudrate, timeout=1)
            if ser.is_open:
                connected = True
                print(f"[INFO] Verbunden mit {port} bei {baudrate} Baud.")
                break
        except Exception as err:
            print(
                f"[WARN] Konnte nicht mit {port} verbinden: {err}. Erneuter Versuch in 5 Sekunden..."
            )
            time.sleep(5)


def extract_float_from_line(line: str):
    """
    Extrahiert eine Kommazahl aus einem beliebigen String.
    Erlaubt Ziffern, Punkt und Minuszeichen.
    Beispiel:
        'Gewicht rechts [kg]: -0.00118' -> -0.00118
    """
    filtered = "".join(ch for ch in line if ch.isdigit() or ch in ".-")
    try:
        return float(filtered)
    except ValueError:
        print(f"[WARN] Konnte keine gültige Zahl aus Zeile extrahieren: {repr(line)}.")
        return None


def read_serial():
    """
    Liest fortlaufend Zeilen vom seriellen Port, erkennt 'links' oder 'rechts',
    extrahiert den Wert und schreibt ihn in eine CSV-Datei.
    """
    global ser, connected, data_file_path

    if serial is None:
        print("Ohne 'serial'-Modul kann nichts gelesen werden.")
        return

    # Warte, bis die serielle Verbindung aufgebaut ist
    while not connected:
        time.sleep(0.5)

    print("[INFO] Starte das Einlesen der seriellen Daten...")

    while True:
        try:
            if ser and ser.is_open and ser.in_waiting > 0:
                line = ser.readline().decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                print(f"[DEBUG] Empfangen: {repr(line)}")

                # Prüfe, ob die Zeile "links" oder "rechts" enthält
                position = None
                if "rechts" in line.lower():
                    position = "Right"
                elif "links" in line.lower():
                    position = "Left"

                if position:
                    value = extract_float_from_line(line)
                    if value is not None:
                        timestamp = time.time()
                        print(f"[INFO] Speichere: {timestamp}, {position}, {value}")

                        # In CSV-Datei schreiben
                        if data_file_path:
                            with data_file_path.open("a", newline="") as csvfile:
                                writer = csv.writer(csvfile)
                                writer.writerow([timestamp, position, value])

            else:
                time.sleep(0.1)

        except Exception as err:
            print(f"[ERROR] Fehler beim Lesen der seriellen Daten: {err}")
            time.sleep(1)


def start_new_run(run_name: str) -> Path:
    """
    Erstellt einen neuen Ordner (data/YYYY-MM-DD_HH-MM-SS_[RunName]) und darin
    eine CSV-Datei mit Header: [Unix Timestamp, Position, Value [kg]].
    Gibt den Pfad zur CSV-Datei zurück.
    """
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    # folder_name = timestamp_str
    # if run_name:
    # Ersetze Leerzeichen durch Unterstriche, um saubere Pfade zu erzeugen
    # folder_name += f"_{run_name.replace(' ', '_')}"

    run_folder = Path("data")
    run_folder.mkdir(parents=True, exist_ok=True)

    csv_path = run_folder / f"serial_data_{run_name}_{timestamp_str}.csv"
    with csv_path.open("w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Unix Timestamp", "Position", "Value [kg]"])

    print(f"[INFO] Neuer Run gestartet: {run_folder}")
    return csv_path


def main():
    parser = argparse.ArgumentParser(description="Serial port data logger CLI.")
    parser.add_argument(
        "--port", default="COM11", help="Serieller Port (z.B. COM11 oder /dev/ttyUSB0)."
    )
    parser.add_argument(
        "--baudrate", type=int, default=115200, help="Baudrate (z.B. 9600, 115200)."
    )
    parser.add_argument(
        "--run-name", default="", help="Optionaler Zusatzname für den Datenordner."
    )
    args = parser.parse_args()

    # 1. Neues Run-Verzeichnis anlegen und CSV-Datei vorbereiten
    global data_file_path
    data_file_path = start_new_run(args.run_name)

    # 2. Thread für Verbindungsaufbau starten
    threading.Thread(
        target=connect_to_serial, args=(args.port, args.baudrate), daemon=True
    ).start()

    # 3. Serielle Daten einlesen (läuft in der Haupt-Thread)
    read_serial()


if __name__ == "__main__":
    main()
