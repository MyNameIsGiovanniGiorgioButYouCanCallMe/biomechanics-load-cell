from pathlib import Path
import dash
from dash import dcc, html, Input, Output, State
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
data_folder = Path('data') / datetime.now().strftime('%Y-%m-%d')
data_folder.mkdir(parents=True, exist_ok=True)  # Create the folder to store data

# File to store the data
data_file_path = data_folder / f"serial_data_{datetime.now().strftime('%H-%M-%S')}.csv"

# Write CSV headers
with data_file_path.open('w', newline='') as f:
   writer = csv.writer(f)
   writer.writerow(['Timestamp', 'Value'])

# Serial port configuration
BAUD_RATE = 115200
SERIAL_PORT = 'COM3'  # Change to your serial port

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
   global serial_data
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
      interval=1000,  # Update every 1 second
      n_intervals=0
   ),

   html.Div([
      html.Button('Start', id='start-data', n_clicks=0, className='btn btn-success mx-2'),
      html.Button('Stop', id='stop-data', n_clicks=0, className='btn btn-danger mx-2')
   ], className='text-center mt-4'),
])

# Callback to update the plot
@app.callback(
   Output('live-plot', 'figure'),
   Input('interval-component', 'n_intervals')
)
def update_plot(n):
   global serial_data
   if len(serial_data) > 100:  # Limit to 100 points
      serial_data = serial_data[-100:]

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
         xaxis_title='Time (s)',
         yaxis_title='Value',
         xaxis=dict(range=[0, 100]),  # Fixed range for 100 points
         yaxis=dict(range=[0, 100]),  # Range for simulated data
         template='plotly_white'
      )
   )
   return figure

# Callbacks to control fake data using mouse movements
@app.callback(
   Output('start-data', 'disabled'),
   Output('stop-data', 'disabled'),
   Input('start-data', 'n_clicks'),
   Input('stop-data', 'n_clicks'),
   prevent_initial_call=True
)
def toggle_mouse_data(start_clicks, stop_clicks):
   """Start or stop generating mouse-based fake data."""
   global use_fake_data
   if dash.ctx.triggered_id == 'start-data':
      use_fake_data = True
   elif dash.ctx.triggered_id == 'stop-data':
      use_fake_data = False

   return (True, False) if use_fake_data else (False, True)

# Run the Dash app
if __name__ == '__main__':
   app.run_server(debug=True)
