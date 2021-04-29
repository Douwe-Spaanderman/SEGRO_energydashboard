####################################
###       Import libraries       ###
####################################

from lib.visualization.figures import *
from lib.auth.check import EncryptedAuth
from lib.utils.utils import human_format, read_data, correct_month, correct_week, standardized_frame, summarize_data

import requests
from datetime import datetime, date, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

import dash
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output

####################################
###       Setup Application      ###
####################################

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

auth = EncryptedAuth(
    app
)

####################################
###         Loading data         ###
####################################

# Get names
cache_data = read_data("data/data.pkl")

adresses = ["Tufsteen 4", "Tufsteen 5", "Tufsteen 6", "Tufsteen 7", "Tufsteen 8", "Tufsteen 9"]
maanden = cache_data["Maand"].unique()
maanden = dict(zip(range(0, len(maanden)), list(maanden)))

weer = pd.read_pickle("data/weer.pkl")

# global cache for buttons
cache_changed_button = []

####################################
###   All code for Application   ###
####################################

app.layout = html.Div([
    html.Div(
        [
            html.Img(
                src="https://github.com/Douwe-Spaanderman/SEGRO_energydashboard/blob/main/data/logo_lower.png?raw=true",
                className='one column',
                ),
            html.Div(
                [
                    html.H2(
                        'Elektrisiteit Dashboard',
                        ),
                    html.H4(
                        'Saldo en productie',
                        )
                    ],

                ),
            html.A(
                html.Button(
                    "Learn More",
                    id="learnMore"
                    ),
                href="https://github.com/Douwe-Spaanderman/SEGRO_energydashboard/",
                )
            ],
        id="header",
        className='row-header',
    ),
    html.Div(
        [
            html.Div(
                [
                    html.P(
                        'Selecteer het adress of meerdere adressen:',
                        className="control_label"
                    ),
                    dcc.Dropdown(
                        id='persisted-adress',
                        value=[adresses[0]],
                        options=[{'label': v, 'value': v} for v in adresses],
                        persistence=True,
                        multi=True,
                        persistence_type='session',
                        searchable=False, 
                    ),
                    html.P(
                        'Selecteer een of meerdere maanden:',
                        className="control_label"
                    ),
                    dcc.RangeSlider(
                        id='month-slider',
                        min=list(maanden)[0],
                        max=list(maanden)[-1],
                        value=[list(maanden)[0],list(maanden)[1]],
                        marks={label: maanden[label] for label in range(0, int(list(maanden)[-1]), 4)},
                        className="dcc_control",
                        persistence=True,
                        persistence_type='session',
                    ),
                    html.P(
                        'Selecteer de week:',
                        className="control_label"
                    ),
                    html.Div(
                        dcc.Slider(
                            id='week-slider', 
                            value=0), 
                        id='week-slider-container'
                    ),
                    html.Div(
                        [
                            html.Button(
                                'Analyseer normale Data', 
                                id='btn-1',
                                n_clicks=1, 
                                className="btn active"
                                ),
                            html.Button(
                                'Reken nodige capaciteit uit', 
                                id='btn-2',
                                n_clicks=0,
                                className="btn"),
                    ],
                    id="myDIV",
                    className="myDiv"
                    ),
                    html.Div(
                        'Hoeveelheid capaciteit in kWh: ',
                        id='capaciteit-slider-output',
                        className="control_label"
                    ),
                    dcc.Slider(
                        id='capaciteit-slider',
                        marks={i: '{}'.format(1000 ** i) for i in range(4)},
                        max=75000,
                        value=5000,
                        step=100
                    ),
                    html.Div(
                        'Hoeveelheid kWh op te halen per uur in winternachten (12-6): ',
                        id='ophalen-slider-output',
                        className="control_label"
                    ),
                    dcc.Slider(
                        id='ophalen-slider',
                        marks={i: '{}'.format(10 ** i) for i in range(4)},
                        max=250, 
                        value=2,
                        step=0.5
                    ),
                ],
                className="pretty_container four columns"
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.P(
                                        id="productie_header",
                                        className="info_text"
                                        ),
                                    html.H6(
                                        id="productie_text",
                                        className="info_text"
                                        )
                                ],
                                id="productie",
                                className="pretty_container"
                            ),
                            html.Div(
                                [
                                    html.P(
                                        id="verbruik_header",
                                        className="info_text"
                                        ),
                                    html.H6(
                                        id="verbruik_text",
                                        className="info_text"
                                        )
                                ],
                                id="verbruik",
                                className="pretty_container"
                            ),
                            html.Div(
                                [
                                    html.P(
                                        id="saldo_header",
                                        className="info_text"
                                        ),
                                    html.H6(
                                        id="saldo_text",
                                        className="info_text"
                                        )
                                ],
                                id="saldo",
                                className="pretty_container"
                            ),
                            html.Div(
                                [
                                    html.P(
                                        id="weer_header",
                                        className="info_text"
                                        ),
                                    html.H6(
                                        id="weer_text",
                                        className="info_text"
                                        )
                                ],
                                id="zon",
                                className="pretty_container"
                            ),
                        ],
                        id="infoContainer",
                        className="row"
                    ),
                    html.Div(
                        [
                            dcc.Graph(
                                id='figure-1-container',
                            )
                        ],
                        id="Graph1Container",
                        className="pretty_container"
                    )
                ],
                id="rightCol",
                className="eight columns"
            )
            ],
            className="row"
        ),
        html.Div(
                [
                    html.Div(
                        [
                            dcc.Graph(id='figure-2-container')
                        ],
                        className='pretty_container seven columns',
                    ),
                    html.Div(
                        [
                            dcc.Graph(id='figure-3-container')
                        ],
                        className='pretty_container five columns',
                    ),
                ],
                className='row'
            ),
            html.Div(
                [
                    html.Div(
                        [
                            dcc.Graph(id='figure-4-container')
                        ],
                        className='pretty_container seven columns',
                    ),
                    html.Div(
                        [
                            dcc.Graph(id='figure-5-container')
                        ],
                        className='pretty_container five columns',
                    ),
                ],
                className='row'
        ),
    ],
    id="mainContainer",
    style={
        "display": "flex",
        "flex-direction": "column"
    }
)

# Button
@app.callback(
    [Output(f"btn-{i}", "className") for i in range(1, 3)],
    [Input(f"btn-{i}", "n_clicks") for i in range(1, 3)],
)
def set_active(*args):
    ctx = dash.callback_context

    if not ctx.triggered or not any(args):
        return ["btn active", "btn"]

    # get id of triggering button
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    return [
        "btn active" if button_id == f"btn-{i}" else "btn" for i in range(1, 3)
    ]

# Sliders
@app.callback(
    Output('week-slider-container', 'children'),
    Input('month-slider', 'value'),
)
def week_slider(month):
    weken = correct_week(cache_data, month)
    return dcc.Dropdown(
        id='week-slider',
        value=list(weken.keys())[0],
        options=[{'label': k, 'value': v} for v,k in weken.items()],
        persistence=True,
        persistence_type='session',
        searchable=False, 
    ),

@app.callback(
    Output('capaciteit-slider-output', 'children'),
    Output('ophalen-slider-output', 'children'),
    Input('capaciteit-slider', 'value'),
    Input('ophalen-slider', 'value'),
)
def capaciteit_ophalen_slider(capaciteit, ophalen):
    return f"Selecteer de hoeveelheid capaciteit in kWh: {capaciteit}", f"Hoeveelheid kWh op te halen per uur in winternachten (12-6): {ophalen}"

# Figures
@app.callback(
    Output('figure-1-container', 'figure'),
    Output('productie_text', 'children'),
    Output('productie_header', 'children'),
    Output('verbruik_text', 'children'),
    Output('verbruik_header', 'children'),
    Output('saldo_text', 'children'),
    Output('saldo_header', 'children'),
    Output('weer_text', 'children'),
    Output('weer_header', 'children'),
    Input('persisted-adress', 'value'),
    Input('month-slider', 'value'),
    Input('capaciteit-slider', 'value'),
    Input('ophalen-slider', 'value'),
    Input('btn-1', 'n_clicks'),
    Input('btn-2', 'n_clicks')
)
def main_figure_display(adress, month, capaciteit, ophalen, btn_1, btn_2):
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    global cache_changed_button

    try:
        if 'btn-' in changed_id:
            cache_changed_button = changed_id
    except UnboundLocalError:
        cache_changed_button = []

    if 'btn-2' in cache_changed_button:
        msg = 'Button 2 was most recently clicked'

        month_data = correct_month(cache_data, month)
        data = standardized_frame(month_data, adress)
        fig, summary = figure1b_data(data, capaciteit, ophalen)
        header = ["Overproductie volgens 0 lijn", "Capaciteit eisen volgens 0 lijn", "Gemiddelde (Ideaal)", "Capaciteit eisen volgens Ideaal"]

    else:
        msg = "None of the buttons have been clicked yet'"

        data = standardized_frame(cache_data, adress)
        summary = summarize_data(data, month, weer)
        fig = figure1a_data(data, adress, month)
        header = ["Productie", "Verbruik", "Saldo", "Zon"]
    
    return fig, summary[0], header[0], summary[1], header[1], summary[2], header[2], summary[3], header[3]

@app.callback(
    Output('figure-2-container', 'figure'),
    Output('figure-3-container', 'figure'),
    Output('figure-4-container', 'figure'),
    Output('figure-5-container', 'figure'),
    Input('persisted-adress', 'value'),
    Input('month-slider', 'value'),
    Input('week-slider', 'value'), 
    Input('capaciteit-slider', 'value'),
    Input('ophalen-slider', 'value'),
)
def create_figures(adress, month, week, capaciteit, ophalen):
    month_data = correct_month(cache_data, month)
    data = standardized_frame(month_data, adress)

    return figure2_data(data, adress), figure3_data(data, capaciteit, ophalen), figure4_data(data), figure3_data(data, capaciteit, ophalen, week)

if __name__ == '__main__':
    app.run_server(debug=True)