from pathlib import Path
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import threading
import time
import csv
import random
from datetime import datetime

# Try to import serial, but handle it gracefully if it fails
try:
    import serial
except ImportError:
    serial = None

# Global Variables
serial_data = []
use_fake_data = True  # Flag to use mouse-based data if the serial port is unavailable
data_folder = None
data_file_path = None

# Serial port configuration
BAUD_RATE = 115200
SERIAL_PORT = 'COM3'  # Change to your serial port

SHOWN_POINTS = 100  # Number of points to show on the plot

# Serial connection (with automatic retry)
ser = None

def connect_to_serial():
    """Try to connect to the serial port. Retry every 5 seconds if it fails."""
    global ser
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
            print(f"Connected to {SERIAL_PORT}")
            break
        except Exception as e:
            print(f"Failed to connect to {SERIAL_PORT}: {e}. Retrying in 5 seconds...")
            time.sleep(5)  # Retry every 5 seconds

# Start the serial connection in a separate thread
if serial:
    threading.Thread(target=connect_to_serial, daemon=True).start()

# Background thread to read serial data
def read_serial():
    """Read data from the serial port or generate fake data."""
    global serial_data, data_file_path
    while True:
        if use_fake_data:
            # Simulate fake data
            value = random.uniform(0, 100)  # Random value between 0 and 100
            print(f"Fake Data: {value}")
        elif ser and ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').strip()
                value = float(line)
                print(f"Serial Data: {value}")
            except ValueError:
                continue  # Ignore invalid data
        else:
            time.sleep(0.1)
            continue

        # Store the data in the global list
        serial_data.append(value)

        if data_file_path:
            # Write the data to the CSV file
            with data_file_path.open('a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), value])

        time.sleep(0.2)  # Delay for CPU optimization

# Start the serial reading thread
serial_thread = threading.Thread(target=read_serial, daemon=True)
serial_thread.start()

# Dash app layout
app = dash.Dash(__name__, external_stylesheets=['https://cdnjs.cloudflare.com/ajax/libs/bootswatch/5.2.3/flatly/bootstrap.min.css'])

app.layout = html.Div([
   html.H1('Arduino-based Data Monitor', className='text-center mb-4'),

   dcc.Graph(
      id='live-plot',
      style={'height': '65vh'}
   ),

   dcc.Interval(
      id='interval-component',
      interval=500,  # Update every 0.5 second
      n_intervals=0
   ),

   html.Div([
      html.Button('Start', id='start-data', n_clicks=0, className='btn btn-success mx-2', style={'font-size': '3em'}),
      html.Button('Stop', id='stop-data', n_clicks=0, className='btn btn-danger mx-2', style={'font-size': '3em'})
   ], className='text-center mt-4'),

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
], style={'padding-left': '20px', 'padding-right': '20px', 'padding-top': '20px', 'padding-bottom': '20px'})

# Callback to update the plot
@app.callback(
    Output('live-plot', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_plot(n):
    global serial_data
    if len(serial_data) > SHOWN_POINTS:  # Limit to SHOWN_POINTS points
        serial_data = serial_data[-SHOWN_POINTS:]

    figure = go.Figure(
        data=[
            go.Scatter(
                x=list(range(len(serial_data))),
                y=serial_data,
                mode='lines+markers',
                line=dict(color='royalblue'),
                marker=dict(size=5)
            )
        ],
        layout=go.Layout(
            title='Live Data Plot',
            xaxis_title='Time [s]',
            yaxis_title='Weight [kg]',
            xaxis=dict(range=[0, SHOWN_POINTS]),  # Fixed range for 100 points
            yaxis=dict(range=[0, SHOWN_POINTS]),  # Range for simulated data
            template='plotly_white'
        )
    )
    return figure

# Callbacks to control fake data
@app.callback(
    Output('start-data', 'disabled'),
    Output('stop-data', 'disabled'),
    Input('start-data', 'n_clicks'),
    Input('stop-data', 'n_clicks'),
    prevent_initial_call=True
)
def toggle_fake_data(start_clicks, stop_clicks):
    """Start or stop generating fake data."""
    global use_fake_data
    if dash.ctx.triggered_id == 'start-data':
        use_fake_data = True
    elif dash.ctx.triggered_id == 'stop-data':
        use_fake_data = False

    return (True, False) if use_fake_data else (False, True)

# Callback to start a new run
@app.callback(
    Output('run-info', 'children'),
    Input('new-run', 'n_clicks'),
    State('run-name', 'value'),
    prevent_initial_call=True
)
def start_new_run(n_clicks, run_name):
    """Start a new run and create a new folder for the data."""
    global data_folder, data_file_path

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    folder_name = f"{timestamp}"
    if run_name:
        folder_name += f"_{run_name.replace(' ', '_')}"

    data_folder = Path('data') / folder_name
    data_folder.mkdir(parents=True, exist_ok=True)  # Create the folder for the run

    data_file_path = data_folder / f"serial_data_{timestamp}.csv"

    # Write CSV headers
    with data_file_path.open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'Value'])

    return f"New run started: {folder_name}"

# Run the Dash app
if __name__ == '__main__':
    app.run_server(debug=True)
