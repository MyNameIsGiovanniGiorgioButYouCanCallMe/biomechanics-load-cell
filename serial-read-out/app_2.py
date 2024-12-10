import time
import threading
import csv
import math
from datetime import datetime
from pathlib import Path

import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objs as go

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
use_fake_data = False    # Set to True to generate fake data instead of reading from serial
SERIAL_PORT = 'COM11'    # Default serial port (adjust as needed)
BAUD_RATE = 115200       # Baud rate for serial communication
SHOWN_POINTS = 200       # Number of points to show in the plot
UPDATE_INTERVAL_MS = 1000  # Plot update interval in milliseconds
N_DECIMALS = 2           # Number of decimals for values

BLACKLIST = [7.11]

DATA_FOLDER = Path('data')

# ------------------------------------------------------------
# Global Variables
# ------------------------------------------------------------
left_data = []
right_data = []

# ------------------------------------------------------------
# Setup CSV Logging
# ------------------------------------------------------------
timestamp_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
data_file_path = DATA_FOLDER / f"serial_data_{timestamp_str}.csv"

with data_file_path.open('w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Unix Timestamp', 'Left Value', 'Right Value'])

def log_data(timestamp: float, left_value, right_value):
    """
    Log a single data point to the CSV file.
    left_value or right_value may be empty string '' if not applicable.
    """
    with data_file_path.open('a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, left_value, right_value])

# ------------------------------------------------------------
# Data Acquisition Functions
# ------------------------------------------------------------
def generate_fake_data():
    """
    Continuously generate fake data (e.g., a sine wave) and store it in left_data and right_data.
    For demonstration, alternate between LEFT and RECHTS readings.
    """
    i = 0
    while True:
        value = math.sin(i / 10) + 0.5 * math.sin(i / 5)
        value_rounded = round(value, N_DECIMALS)
        t = time.time()

        if i % 2 == 0:
            # LEFT data point
            if value_rounded not in BLACKLIST:
                left_data.append((t, value_rounded))
                log_data(t, value_rounded, '')
        else:
            # RECHTS data point
            if value_rounded not in BLACKLIST:
                right_data.append((t, value_rounded))
                log_data(t, '', value_rounded)

        i += 1
        time.sleep(0.2)  # ~5 samples/second

def read_real_data():
    """
    Connect to SERIAL_PORT and read real data continuously.
    Lines must contain "LEFT" or "RECHTS" and a numeric value.
    Values in BLACKLIST are skipped.
    """
    try:
        import serial
    except ImportError:
        print("pyserial is not installed. Using fake data instead.")
        generate_fake_data()
        return

    ser = None
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
            print(f"Connected to {SERIAL_PORT}")
            break
        except Exception as e:
            print(f"Failed to connect to {SERIAL_PORT}: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            if not line:
                continue

            upper_line = line.upper()
            is_left = 'LINKS' in upper_line
            is_rechts = 'RECHTS' in upper_line

            if not (is_left or is_rechts):
                continue

            filtered = "".join(ch for ch in line if ch.isdigit() or ch == '.' or ch == '-')
            if not filtered:
                continue

            try:
                value = float(filtered) / (10 ** N_DECIMALS)
            except ValueError:
                continue

            if value in BLACKLIST:
                continue


            print(f"Received: {line}")

            t = time.time()
            if is_left:
                left_data.append((t, value))
                log_data(t, value, '')
            elif is_rechts:
                right_data.append((t, value))
                log_data(t, '', value)
        else:
            time.sleep(0.1)


def reset_data_thread():
      """
      Clear the data lists and start fresh.
      """
      global left_data, right_data
      left_data = []
      right_data = []


def start_data_thread():
    """
    Start a background thread to acquire data.
    """
    if use_fake_data:
        data_thread = threading.Thread(target=generate_fake_data, daemon=True)
    else:
        data_thread = threading.Thread(target=read_real_data, daemon=True)
    data_thread.start()

# ------------------------------------------------------------
# Dash App and Callbacks
# ------------------------------------------------------------
def create_app_layout():
    return html.Div([
        html.H1("Live Data Monitor", className="text-center mb-4"),
        dcc.Graph(id='live-plot', style={'height': '65vh'}),
        dcc.Interval(id='interval-component', interval=UPDATE_INTERVAL_MS, n_intervals=0),
        html.Div(f"Data is being saved to: {data_file_path}", className='mt-2 text-center')
    ], style={'padding': '20px'})

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.layout = create_app_layout()

@app.callback(
    Output('live-plot', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_plot(n):
    # If no data at all, still show both traces empty to ensure the legend is displayed.
    left_subset = left_data[-SHOWN_POINTS:]
    right_subset = right_data[-SHOWN_POINTS:]

    # If no data for either, default earliest time to current time
    earliest_left = left_subset[0][0] if left_subset else time.time()
    earliest_right = right_subset[0][0] if right_subset else time.time()
    min_time = min(earliest_left, earliest_right)

    left_times = [d[0] - min_time for d in left_subset]
    left_values = [d[1] for d in left_subset]

    right_times = [d[0] - min_time for d in right_subset]
    right_values = [d[1] for d in right_subset]

    figure = go.Figure(layout=go.Layout(
        title='Live Data Plot',
        xaxis_title='Time (s)',
        yaxis_title='Value',
        template='plotly_white',
        showlegend=True  # Ensure legend is displayed
    ))

    # Always add both traces, even if empty, to ensure legend is present
    figure.add_trace(go.Scatter(
        x=left_times,
        y=left_values,
        mode='lines+markers',
        name='LINKS',
        line=dict(color='blue')
    ))

    figure.add_trace(go.Scatter(
        x=right_times,
        y=right_values,
        mode='lines+markers',
        name='RECHTS',
        line=dict(color='red')
    ))

    return figure

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
if __name__ == '__main__':
   reset_data_thread()
   time.sleep(1)
   start_data_thread()
   app.run_server(debug=True)
