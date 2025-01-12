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
SERIAL_PORT = 'COM11'    # Default serial port (adjust if needed)
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

ser = None
data_thread = None
stop_event = threading.Event()  # Used to stop threads gracefully

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
    with data_file_path.open('a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, left_value, right_value])

def reset_data_thread():
    """
    Reset the data thread and related global states.
    """
    global data_thread, ser, left_data, right_data, stop_event

    print("Resetting data thread...")
    stop_event.set()
    if data_thread is not None and data_thread.is_alive():
        data_thread.join(timeout=5.0)

    stop_event.clear()

    # Close serial if open
    if ser is not None:
        if ser.is_open:
            ser.close()
        ser = None

    # Clear existing data
    left_data.clear()
    right_data.clear()
    print("Data thread reset complete.")

# ------------------------------------------------------------
# Data Acquisition Functions
# ------------------------------------------------------------
def generate_fake_data():
    print("Starting fake data generation...")
    i = 0
    while not stop_event.is_set():
        value = math.sin(i / 10) + 0.5 * math.sin(i / 5)
        value_rounded = round(value, N_DECIMALS)
        t = time.time()

        if value_rounded not in BLACKLIST:
            if i % 2 == 0:
                left_data.append((t, value_rounded))
                log_data(t, value_rounded, '')
            else:
                right_data.append((t, value_rounded))
                log_data(t, '', value_rounded)

        i += 1
        time.sleep(0.2)
    print("Fake data generation stopped.")

def establish_connection():
    """
    Try to connect to the serial port, retrying every 5 seconds if it fails.
    """
    global ser
    from serial import Serial, SerialException
    while not stop_event.is_set():
        try:
            print(f"Attempting to connect to {SERIAL_PORT}...")
            ser = Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print(f"Connected to {SERIAL_PORT}")
            return  # Exit once connected
        except Exception as e:
            print(f"Failed to connect to {SERIAL_PORT}: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def read_real_data():
    print("Starting real data acquisition...")
    try:
        import serial
    except ImportError:
        print("pyserial not installed. Falling back to fake data.")
        generate_fake_data()
        return

    from serial import SerialException

    # Establish initial connection
    establish_connection()

    while not stop_event.is_set():
        if ser is None or not ser.is_open:
            # Try to reconnect if the serial port closed unexpectedly
            print("Serial port lost. Reconnecting...")
            establish_connection()

        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if not line:
                    continue

                upper_line = line.upper()
                is_left = 'LEFT' in upper_line
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

                t = time.time()
                if is_left:
                    left_data.append((t, value))
                    log_data(t, value, '')
                elif is_rechts:
                    right_data.append((t, value))
                    log_data(t, '', value)
            else:
                time.sleep(0.1)

        except (SerialException, OSError) as e:
            # If a serial error occurs (device unplugged, etc.), try to close and reconnect
            print(f"Serial error occurred: {e}. Attempting to reconnect...")
            if ser and ser.is_open:
                ser.close()
            ser = None
            time.sleep(5)  # Wait before reattempting connection

    # Cleanup when stopping
    if ser and ser.is_open:
        ser.close()
    print("Real data acquisition stopped.")

def start_data_thread():
    global data_thread
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
    left_subset = left_data[-SHOWN_POINTS:]
    right_subset = right_data[-SHOWN_POINTS:]

    if not left_subset and not right_subset:
        figure = go.Figure(layout=go.Layout(
            title='No data yet...',
            template='plotly_white',
            xaxis_title='Time (s)',
            yaxis_title='Value',
            showlegend=True
        ))
        figure.add_trace(go.Scatter(x=[], y=[], mode='lines+markers', name='LEFT', line=dict(color='blue')))
        figure.add_trace(go.Scatter(x=[], y=[], mode='lines+markers', name='RECHTS', line=dict(color='red')))
        return figure

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
        showlegend=True
    ))
    figure.add_trace(go.Scatter(
        x=left_times,
        y=left_values,
        mode='lines+markers',
        name='LEFT',
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
    time.sleep(2)  # Wait for threads to start
    start_data_thread()
    app.run_server(debug=True)
