from pathlib import Path
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import threading
import time
import csv
from datetime import datetime

# Try to import serial, but handle it gracefully if it fails
try:
    import serial
except ImportError:
    serial = None
    print("Warning: pyserial not installed. No serial reading will occur.")

# Global Variables
serial_data = []  # Store (timestamp, value) tuples
data_folder = None
data_file_path = None

# Serial port configuration
BAUD_RATE = 115200
SERIAL_PORT = 'COM11'  # Change to your serial port
SHOWN_POINTS = 100
N_NACHKOMMASTELLEN = 2

ser = None
connected = False

def connect_to_serial():
    """Try to connect to the serial port. Retry every 5 seconds if it fails."""
    global ser, connected
    if serial is None:
        print("Serial module not available. Cannot connect.")
        return
    while True:
        if ser and ser.is_open:
            connected = True
            print("Serial port is open and connected.")
            break
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            if ser.is_open:
                connected = True
                print(f"Connected to {SERIAL_PORT}")
                break
        except Exception as e:
            print(f"Failed to connect to {SERIAL_PORT}: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# Start the serial connection in a separate thread if pyserial is available
if serial is not None:
    threading.Thread(target=connect_to_serial, daemon=True).start()


def read_serial():
    """Read data from the serial port and store it."""
    global serial_data, data_file_path, ser, connected
    if serial is None:
        return  # no serial available

    # Wait until connected
    while not connected:
        time.sleep(0.5)

    print("Reading from serial...")
    while True:
        try:
            if ser.in_waiting > 0:
                # Read line from serial
                raw_line = ser.readline()
                if not raw_line:
                    # No data this time, sleep and continue
                    time.sleep(0.1)
                    continue

                # Attempt to decode and strip the line
                line = raw_line.decode('utf-8', errors='replace').strip()
                print(f"Raw line received: {repr(line)}")

                if line == '':
                    print("Warning: Received an empty line. Skipping.")
                    continue

                # If your Arduino sends pure numeric data:
                # For example, if Arduino sends "12345" for a weight of 123.45 kg:
                # We divide by 10**N_NACHKOMMASTELLEN.
                # If the Arduino sends already in decimal form like "123.45", you might NOT need to divide.

                # Try to parse a float directly
                # If your Arduino data is something like "Weight: 123.45", you need to extract the numeric part
                # Let's try extracting digits, decimal points, and minus sign:
                filtered = ''.join(ch for ch in line if ch.isdigit() or ch == '.' or ch == '-')

                if filtered == '':
                    print(f"Warning: Could not find numeric content in line: {repr(line)}. Skipping.")
                    continue

                try:
                    # If the Arduino already sends a proper float, consider not dividing by 10**N_NACHKOMMASTELLEN.
                    # If Arduino sends integer representing centi-grams, for example, then dividing is correct.
                    value = float(filtered) / (10 ** N_NACHKOMMASTELLEN)
                    print(f"Parsed numeric value: {value}")
                except ValueError:
                    print(f"Warning: Failed to parse {repr(filtered)} as float. Skipping.")
                    continue

                timestamp = time.time()
                serial_data.append((timestamp, value))

                # Save to CSV if run started
                if data_file_path:
                    with data_file_path.open('a', newline='') as f:
                        writer = csv.writer(f)
                        writer.writerow([timestamp, value])
            else:
                time.sleep(0.1)
        except Exception as e:
            print(f"Error reading from serial: {e}")
            time.sleep(0.5)

if serial is not None:
    serial_thread = threading.Thread(target=read_serial, daemon=True)
    serial_thread.start()

# Dash app layout
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.layout = html.Div([
    html.H1('Arduino-based Data Monitor', className='text-center mb-4'),
    dcc.Graph(id='live-plot', style={'height': '65vh'}),
    dcc.Interval(id='interval-component', interval=500, n_intervals=0),
    html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Input(id='run-name', type='text', placeholder='Enter run name (optional)', className='form-control mb-2'),
            ], width=6),
            dbc.Col([
                dbc.Button('Start New Run', id='new-run', n_clicks=0, className='btn btn-primary mt-2'),
            ], width=6),
        ]),
    ], className='text-center mt-4'),
    html.Div(id='run-info', className='mt-2 text-center')
], style={'padding-left': '20px', 'padding-right': '20px',
          'padding-top': '20px', 'padding-bottom': '20px'})

@app.callback(
    Output('live-plot', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_plot(n):
    global serial_data
    if len(serial_data) == 0:
        # No data yet, return an empty plot
        return go.Figure(layout=go.Layout(
            title='Live Data Plot (no data yet)',
            xaxis_title='Time (s)',
            yaxis_title='Value',
            template='plotly_white'
        ))

    # Limit to last SHOWN_POINTS points
    if len(serial_data) > SHOWN_POINTS:
        serial_data = serial_data[-SHOWN_POINTS:]

    timestamps = [p[0] for p in serial_data]
    values = [p[1] for p in serial_data]

    relative_times = [t - timestamps[0] for t in timestamps]
    figure = go.Figure(
        data=[
            go.Scatter(
                x=relative_times,
                y=values,
                mode='lines+markers',
                line=dict(color='royalblue'),
                marker=dict(size=5)
            )
        ],
        layout=go.Layout(
            title='Live Data Plot',
            xaxis_title='Time (s)',
            yaxis_title='Value',
            template='plotly_white'
        )
    )
    return figure

@app.callback(
    Output('run-info', 'children'),
    Input('new-run', 'n_clicks'),
    State('run-name', 'value'),
    prevent_initial_call=True
)
def start_new_run(n_clicks, run_name):
    global data_folder, data_file_path

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    folder_name = timestamp
    if run_name:
        folder_name += f"_{run_name.replace(' ', '_')}"

    data_folder = Path('data') / folder_name
    data_folder.mkdir(parents=True, exist_ok=True)

    data_file_path = data_folder / f"serial_data_{timestamp}.csv"
    with data_file_path.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Unix Timestamp', 'Value'])

    return f"New run started: {folder_name}"

if __name__ == '__main__':
    app.run_server(debug=True)
