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
use_fake_data = False   # Set to False to attempt reading from serial
SERIAL_PORT = 'COM11'  # Default serial port (adjust as needed)
BAUD_RATE = 115200     # Baud rate for serial communication
SHOWN_POINTS = 200     # Number of points to show in the plot
UPDATE_INTERVAL_MS = 1000  # Plot update interval in milliseconds
N_DECIMALS = 2         # Number of decimals for values

DATA_FOLDER = Path('data')

# ------------------------------------------------------------
# Global Variables
# ------------------------------------------------------------
serial_data = []  # Will store tuples of (timestamp, value)

# ------------------------------------------------------------
# Setup CSV Logging
# ------------------------------------------------------------
timestamp_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
DATA_FOLDER.mkdir(parents=True, exist_ok=True)
data_file_path = DATA_FOLDER / f"serial_data_{timestamp_str}.csv"

with data_file_path.open('w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Unix Timestamp', 'Value'])

def log_data(timestamp: float, value: float):
    """
    Log a single data point (timestamp, value) to the CSV file.
    """
    with data_file_path.open('a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, value])

# ------------------------------------------------------------
# Data Acquisition Functions
# ------------------------------------------------------------
def generate_fake_data():
    """
    Continuously generate fake data (e.g., a sine wave) and store it in serial_data.
    This function runs in a background thread if use_fake_data = True.
    """
    i = 0
    while True:
        # Create some fake oscillating data
        value = math.sin(i / 10) + 0.5 * math.sin(i / 5)
        value_rounded = round(value, N_DECIMALS)
        t = time.time()
        serial_data.append((t, value_rounded))
        log_data(t, value_rounded)

        i += 1
        time.sleep(0.2)  # Generates data ~5 samples/second

def read_real_data():
    """
    Attempt to connect to the specified SERIAL_PORT and read real data continuously.
    If not available, this will retry until successful.
    Each line read from the serial is parsed into a float and logged.
    """
    try:
        import serial
    except ImportError:
        print("pyserial is not installed. Using fake data instead.")
        generate_fake_data()
        return

    ser = None
    # Keep trying to connect until successful
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"Connected to {SERIAL_PORT}")
            break
        except Exception as e:
            print(f"Failed to connect to {SERIAL_PORT}: {e}. Retrying in 5 seconds...")
            time.sleep(5)

    # Read continuously from the serial port
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().decode('utf-8', errors='replace').strip()

            # Try direct parsing
            try:
                value = float(line) / (10 ** N_DECIMALS)
            except ValueError:
                # If direct parsing fails, try filtering out non-numeric chars
                filtered = "".join(ch for ch in line if ch.isdigit() or ch == '.' or ch == '-')
                if not filtered:
                    continue
                try:
                    value = float(filtered) / (10 ** N_DECIMALS)
                except ValueError:
                    continue

            t = time.time()
            serial_data.append((t, value))
            log_data(t, value)
        else:
            time.sleep(0.1)

def start_data_thread():
    """
    Start a background thread to acquire data (fake or real) depending on use_fake_data flag.
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
    """
    Create and return the layout for the Dash app.
    """
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
    """
    Update the plot every UPDATE_INTERVAL_MS.
    Show the last SHOWN_POINTS points, with time re-based so the oldest point is at time 0.
    """
    if len(serial_data) == 0:
        # No data yet
        return go.Figure(layout=go.Layout(
            title='No data yet...',
            template='plotly_white',
            xaxis_title='Time (s)',
            yaxis_title='Value'
        ))

    # Only show the most recent SHOWN_POINTS data points
    data_subset = serial_data[-SHOWN_POINTS:]
    timestamps = [d[0] for d in data_subset]
    values = [d[1] for d in data_subset]

    # Calculate relative times so the oldest data point shown starts at t=0
    min_time = timestamps[0]
    relative_times = [t - min_time for t in timestamps]

    figure = go.Figure(
        data=[go.Scatter(x=relative_times, y=values, mode='lines+markers')],
        layout=go.Layout(
            title='Live Data Plot',
            xaxis_title='Time (s)',
            yaxis_title='Value',
            template='plotly_white'
        )
    )
    return figure

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
if __name__ == '__main__':
    start_data_thread()
    app.run_server(debug=True)
