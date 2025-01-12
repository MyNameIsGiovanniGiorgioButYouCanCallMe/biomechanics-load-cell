from pathlib import Path
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import threading
import time
import csv
from datetime import datetime
import pandas as pd  # For handling CSV files
import base64  # For decoding the uploaded file contents
from io import StringIO


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
SERIAL_PORT = "COM11"  # Change to your serial port
SHOWN_POINTS = 100
N_NACHKOMMASTELLEN = 2

ser = None
connected = False

# Dash app layout
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.layout = html.Div(
    [
        html.H1("Arduino-based Data Monitor", className="text-center mb-4"),
        dcc.Graph(id="live-plot", style={"height": "65vh"}),
        dcc.Interval(id="interval-component", interval=500, n_intervals=0),
        html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Input(
                                    id="run-name",
                                    type="text",
                                    placeholder="Enter run name (optional)",
                                    className="form-control mb-2",
                                ),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Button(
                                    "Start New Run",
                                    id="new-run",
                                    n_clicks=0,
                                    className="btn btn-primary mt-2",
                                ),
                            ],
                            width=6,
                        ),
                    ]
                ),
            ],
            className="text-center mt-4",
        ),
        html.Div(id="run-info", className="mt-2 text-center"),
        html.Hr(),
        html.H2("Upload and Display CSV Data", className="text-center mt-4"),
        dcc.Upload(
            id="upload-data",
            children=html.Div(
                [
                    "Drag and Drop or ",
                    html.A("Select a CSV File", href="#"),
                ]
            ),
            style={
                "width": "100%",
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "1px",
                "borderStyle": "dashed",
                "borderRadius": "5px",
                "textAlign": "center",
                "margin": "10px",
            },
            multiple=False,
        ),
        html.Div(id="uploaded-file-info", className="mt-2"),
        dcc.Graph(id="csv-data-plot", style={"height": "65vh"}),
    ],
    style={
        "padding-left": "20px",
        "padding-right": "20px",
        "padding-top": "20px",
        "padding-bottom": "20px",
    },
)


@app.callback(
    Output("csv-data-plot", "figure"),
    Output("uploaded-file-info", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True,
)
def upload_and_display_csv(contents, filename):
    if not contents or not filename.endswith(".csv"):
        return go.Figure(), "Invalid file. Please upload a CSV file."

    # Decode and parse the uploaded CSV data
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    try:
        df = pd.read_csv(StringIO(decoded.decode("utf-8")))

        # Ensure the CSV has the expected columns
        if not {"Unix Timestamp", "Position", "Value [kg]"}.issubset(df.columns):
            return (
                go.Figure(),
                "CSV file must contain 'Unix Timestamp', 'Position', and 'Value [kg]' columns.",
            )

        # Prepare data for plotting
        left_values = df[df["Position"] == "Left"]
        right_values = df[df["Position"] == "Right"]

        figure = go.Figure(
            data=[
                go.Scatter(
                    x=left_values["Unix Timestamp"],
                    y=left_values["Value [kg]"],
                    mode="lines+markers",
                    name="Left",
                    line=dict(color="blue"),
                ),
                go.Scatter(
                    x=right_values["Unix Timestamp"],
                    y=right_values["Value [kg]"],
                    mode="lines+markers",
                    name="Right",
                    line=dict(color="red"),
                ),
            ],
            layout=go.Layout(
                title="Uploaded CSV Data",
                xaxis_title="Unix Timestamp",
                yaxis_title="Value [kg]",
                template="plotly_white",
            ),
        )
        return figure, f"Uploaded file: {filename}"

    except Exception as e:
        return go.Figure(), f"Error processing file: {e}"


if __name__ == "__main__":
    app.run_server(debug=False)
