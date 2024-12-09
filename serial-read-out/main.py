import serial
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import datetime

import plotly.graph_objs as go

# Initialize serial port
# ser = serial.Serial('COM3', 115_200)  # Adjust 'COM3' to your serial port
ser = 0  # Adjust 'COM3' to your serial port

# Initialize Dash app
app = dash.Dash(__name__)
app.layout = html.Div([
   dcc.Graph(id='live-graph'),
   dcc.Interval(
      id='interval-component',
      interval=1*1000,  # Update every second
      n_intervals=0
   )
])

# Initialize data storage
data = []

@app.callback(Output('live-graph', 'figure'),
           [Input('interval-component', 'n_intervals')])
def update_graph_live(n):
   global data
   if ser.in_waiting:
      line = ser.readline().decode('utf-8').strip()
      timestamp = datetime.datetime.now()
      data.append({'time': timestamp, 'value': float(line)})

   df = pd.DataFrame(data)
   figure = {
      'data': [go.Scatter(
         x=df['time'],
         y=df['value'],
         mode='lines+markers'
      )],
      'layout': go.Layout(
         xaxis=dict(range=[min(df['time']), max(df['time'])]),
         yaxis=dict(range=[min(df['value']), max(df['value'])]),
      )
   }
   return figure

if __name__ == '__main__':
   app.run_server(debug=True)