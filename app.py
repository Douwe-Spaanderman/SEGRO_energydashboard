###################################
### All code for data mangement ###
###################################

import requests
from base64 import b64encode
from datetime import datetime, date, timedelta
import pandas as pd
from functools import reduce
from scipy import signal

def read_data(location):

    meetdata = pd.read_pickle(location)
    data = meetdata

    # Functie voor het achterhalen van dagen en week info
    all_days = [x.split(' ')[0] for x in data["Date"]]
    unique_days = dict.fromkeys(all_days)

    i = 0
    for k in unique_days:
        unique_days[k] = 1+i
        i += 1
        
    data["dag"] = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S').strftime("%d %B %Y") for x in data["Date"]]

    data["soort_dag"] = ["Werkdag" if datetime.strptime(x, '%Y-%m-%d %H:%M:%S').weekday() < 5 else "Weekend" for x in data["Date"]]

    data["Week"] = [' '.join(map(str, datetime.strptime(x, '%Y-%m-%d %H:%M:%S').isocalendar()[:2])) for x in data["Date"]]
    data["Maand"] = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S').strftime("%B %Y") for x in data["Date"]]

    data = data[data["Maand"] != "March 2019"].reset_index(drop=True)

    return data

def correct_month(tmp, month):

    maanden = tmp["Maand"].unique()[month[0]:month[1]]
    maand_data = tmp[tmp["Maand"].isin(maanden)]

    return maand_data

def correct_week(tmp, month):
    month_data = correct_month(tmp, month)
    weken = tmp[tmp["Week"].isin(month_data["Week"].unique())]
    weken = weken.groupby(['Week','dag']).size().reset_index()  

    tmp_info = []
    tmp_keys = []
    for i in weken["Week"].unique():
        tmp = weken[weken["Week"] == i].reset_index(drop=True)
        tmp["month"] = [x.split(' ')[1] for x in tmp["dag"]]
        month_tmp = tmp["month"].unique()
        if len(month_tmp) > 1:
            min_tmp = list(tmp[tmp["month"] == month_tmp[1]]["dag"])[0]
            max_tmp = list(tmp[tmp["month"] == month_tmp[0]]["dag"])[-1]
        else:
            min_tmp = tmp["dag"][0].split(" ")[0]
            max_tmp = list(tmp["dag"])[-1]
            
        tmp_info.append(f"{min_tmp} - {max_tmp}")
        tmp_keys.append(f"{i}")
        
    weken = dict(zip(tmp_keys, tmp_info))
    
    return weken

def standardized_frame(data_cache, adresses):
    combined_data = []
    for adress in adresses:
        data = data_cache[['Date', 'dag', 'soort_dag', 'Week', 'Maand', f'{adress}', f'{adress} monthly BP']]
        data = data.rename(columns={f'{adress}': "OP value", f'{adress} monthly BP': "BP montly value"})
        data["adress"] = adress

        data["OP value"] = data["OP value"] * -1 
        # Dag sum
        tmp = data.groupby(['dag'], as_index = False, sort=False).agg({'OP value': 'sum'})
        tmp = tmp.rename(columns={"OP value": "OP value daysum"})
        data = pd.merge(data, tmp, on="dag")

        #Het gemiddelde 24 uurs energieprofiel (verbruik, productie en saldo) van de werkdagen per kalendermaand;
        tmp = data[data["soort_dag"] == "Werkdag"]
        tmp2 = tmp.groupby(['Week'], as_index = False, sort=False).agg({'OP value': 'sum', "OP value daysum": 'mean'})
        tmp2 = tmp2.rename(columns={"OP value": "OP value weeksum", "OP value daysum":"OP value weekmean"})
        tmp = pd.merge(tmp, tmp2, on="Week")

        #Het gemiddelde 24 uurs energieprofiel (verbruik, productie en saldo) van de weekenden perkalendermaand;
        tmp2 = data[data["soort_dag"] == "Weekend"]
        tmp3 = tmp2.groupby(['Week'], as_index = False, sort=False).agg({'OP value': 'sum', "OP value daysum": 'mean'})
        tmp3 = tmp3.rename(columns={"OP value": "OP value weeksum", "OP value daysum":"OP value weekmean"})
        tmp2 = pd.merge(tmp2, tmp3, on="Week")

        data = pd.concat([tmp, tmp2]).sort_values(by=['Date']).reset_index(drop=True)
        combined_data.append(data)

    combined_data = pd.concat(combined_data).reset_index(drop=True)

    return(combined_data)

def summarize_data(data, month, weer):
    data = correct_month(data, month)

    #weer
    weer = weer.drop(['dag'], axis=1)
    weer = weer.groupby(['Maand'], as_index = False, sort=False).agg({'zon': 'sum'})
    data = pd.merge(data, weer, on="Maand")
    
    data = data.groupby(['Maand'], as_index = False, sort=False).agg({'OP value': 'sum', 'BP montly value': "mean", "zon":"mean"})
    saldo = float(data["OP value"].sum())
    produced = float(data["BP montly value"].sum())
    used = saldo - produced
    weer = float(data["zon"].sum())
    
    return [f'{int(produced)} kW', f'{int(used)} kW', f'{int(saldo)} kW', f'{int(weer)} Uur']

def figure1a_data(data_cache, adresses, month, layout):
    # Overall info
    fig = go.Figure()

    colors = []
    for j in range(0, len(data_cache["Maand"].unique())):
        if j >= int(month[0]) and j < int(month[1]):
            colors.append(1)
        else:
            colors.append(0.2)

    for i, adress in enumerate(adresses):
        data = data_cache[data_cache["adress"] == adress]
        data = data.groupby(['Maand'], as_index = False, sort=False).agg({'OP value': 'sum', "dag": "nunique", 'BP montly value': "mean", "OP value daysum": "mean", "OP value weeksum": 'mean'})
        data["used"] = [float(x["OP value"]) - float(x["BP montly value"]) for index, x in data.iterrows()]
        data = data.round(1)
        text_data = list(zip([str(x) for x in data["OP value daysum"]], [str(x) for x in data["OP value weeksum"]]))

        if len(adresses) == 1:
            fig.add_trace(go.Bar(
                x=data['Maand'],
                y=data["used"],
                name = 'Used',
                marker=dict(
                    opacity=colors,
                    ),
            ))

            fig.add_trace(go.Bar(
                x=data['Maand'],
                y=data["OP value"],
                name = 'Saldo',
                marker=dict(
                    opacity=colors,
                    ),
            ))

            fig.add_trace(go.Bar(
                x=data['Maand'],
                y=data["BP montly value"],
                name = 'Produced',
                marker=dict(
                    opacity=colors,
                    ),
                customdata = text_data,
                hovertemplate = "%{y}<br>dagelijks gemiddelde: %{customdata[0]} </br>wekelijks gemiddelde: %{customdata[1]}",
            ))

        else:
            fig.add_trace(go.Bar(
                x=data['Maand'],
                y=data["OP value"],
                name = adress,
                customdata = text_data,
                marker=dict(
                    opacity=colors,
                    ),
                hovertemplate = "%{y}<br>dagelijks gemiddelde: %{customdata[0]} </br>wekelijks gemiddelde: %{customdata[1]}",
            ))

    fig.update_layout(layout,
        title_text='Compleet profiel per maand',
        hovermode='x unified',
        margin=dict(
            l=30,
            r=30,
            b=20,
            t=40
            ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.4,
            xanchor="center",
            x=0.25,
            ),
        )

    fig.update_xaxes(showline=False, showgrid=False)
    fig.update_yaxes(showline=True, zeroline=True, zerolinecolor="black", linecolor="black", zerolinewidth=1)

    return fig

def figure1b_data(data_cache, layout):
    # Overall info
    fig = go.Figure()

    data = data_cache.groupby(['Maand'], as_index = False, sort=False).agg({'OP value': 'sum'})
    best_line = data["OP value"].sum()/len(data)

    data["delta"] = data["OP value"] - best_line

    overproduced = sum([0 if int(x) <= 0 else x for x in data["OP value"]])
    underproduced = sum([0 if int(x) > 0 else x for x in data["OP value"]])

    overproduced_perfect = sum([0 if int(x) <= 0 else x for x in data["delta"]])
    underproduced_perfect = sum([0 if int(x) > 0 else x for x in data["delta"]])

    fig.add_trace(go.Scatter(
        x=data['Maand'],
        y=data["OP value"],
        name = 'Saldo',
        mode='lines',
        line=dict(
            shape="spline",
            smoothing=0.8,
            color='#fac1b7',
            width=4,
        )
    ))

    fig.add_trace(go.Scatter(
        x=data['Maand'],
        y=[best_line] * len(data),
        name = 'Gemiddelde lijn (Ideaal)',
        mode='lines',
        line=dict(
            shape="spline",
            color='#a9bb95',
            width=3,
        ),
    ))

    fig.add_trace(go.Scatter(
        x=data['Maand'],
        y=[0] * len(data),
        name = '0 lijn (minste capaciteit nodig)',
        mode='lines',
        line=dict(
            shape="spline",
            color='#92d8d8',
            width=3,
        ),
    ))

    fig.update_layout(layout,
        title_text='Compleet profiel per maand',
        hovermode='x unified',
        margin=dict(
            l=30,
            r=30,
            b=20,
            t=40
            ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.4,
            xanchor="center",
            x=0.25,
            ),
        )

    fig.update_xaxes(showline=False, showgrid=False)
    fig.update_yaxes(showline=True, zeroline=True, zerolinecolor="black", linecolor="black", zerolinewidth=1)

    return fig, [f'{int(overproduced)} kW', f'{abs(int(underproduced))} kW', f'{int(best_line)} kW', f'{abs(int(underproduced_perfect))} kW']

def figure2_data(data_cache, adresses, layout):
    fig = go.Figure()
    for adress in adresses:
        data = data_cache[data_cache["adress"] == adress]
        data = data.groupby(['dag'], as_index = False, sort=False).agg({'OP value': 'sum', "dag": "unique", 'soort_dag': "unique"})

        data['dag'] = [x[0] for x in data['dag']]
        data['soort_dag'] = [x[0] for x in data['soort_dag']]
        Werkdag = [x["OP value"] if x["soort_dag"] == "Werkdag" else None for index, x in data.iterrows()]
        Weekend = [x["OP value"] if x["soort_dag"] == "Weekend" else None for index, x in data.iterrows()]

        if len(adresses) > 1:
            fig.add_trace(go.Scatter(
                x=data['dag'],
                y=data["OP value"],
                name = f'{adress}',
                line=dict(
                    shape="spline",
                    smoothing=1,
                    ),
                showlegend=True,
            ))
        else:
            fig.add_trace(go.Scatter(
                x=data['dag'],
                y=signal.savgol_filter(data["OP value"], 5, 3),
                name = 'combined',
                line=dict(
                    color="#989898",
                    shape="spline"
                    ),
                showlegend=False,
            ))

            fig.add_trace(go.Scatter(
                x=data['dag'],
                y=Werkdag,
                name = 'Werkdag',
                mode='markers',
                marker=dict(size=8, symbol='diamond-open')
            ))

            fig.add_trace(go.Scatter(
                x=data['dag'],
                y=Weekend,
                name = 'Weekend',
                mode='markers',
                marker=dict(size=8, symbol='diamond-open')
            ))

    fig.update_layout(layout,
        title_text='Gemiddelde profiel over de geselecteerde maand(en)',
        margin=dict(
            l=30,
            r=30,
            b=20,
            t=40
            ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.5,
            xanchor="center",
            x=0.0,
            ),
        )

    tickvals = int(len(data) / 6.125)
    tickvals = np.arange(0, len(data)).astype(int)[0::tickvals]
    fig.update_xaxes(
                 tickmode = 'array',
                 tickvals = tickvals,
                 )

    return fig

def figure3_data(data, layout):
    data["time"] = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S').strftime("%H:%M:%S") for x in data["Date"]]
    data = data.groupby(['time', 'soort_dag'], as_index = False, sort=False).agg({'OP value': 'mean', "dag": "nunique"})

    fig1_tmp = data[data["soort_dag"] == "Werkdag"]
    fig2_tmp = data[data["soort_dag"] == "Weekend"]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=fig1_tmp['time'],
        y=fig1_tmp["OP value"],
        name = 'Werkdag',
        line=dict(
            shape="spline",
            smoothing=0.8,
            width=3,
            color='#fac1b7'
        )
    ))

    fig.add_trace(go.Scatter(
        x=fig2_tmp['time'],
        y=fig2_tmp['OP value'],
        name = 'Weekend',
        line=dict(
            shape="spline",
            smoothing=0.8,
            width=3,
            color='#a9bb95'
        )
    ))

    fig.update_layout(layout,
        title_text='24 uur profiel van de geselecteerde maand(en)',
        margin=dict(
            l=30,
            r=30,
            b=20,
            t=40
            ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.4,
            xanchor="center",
            x=0.25,
            ),
        hovermode='x unified',
        )

    tickvals = np.arange(0, 192).astype(int)[0::16]
    fig.update_xaxes(
                 tickmode = 'array',
                 tickvals = tickvals,
                 )

    return fig

def figure4_data(data, layout):
    data["weekday"] = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S').strftime("%a") for x in data["Date"]]
    data = data.groupby(['weekday'], as_index = False, sort=False).agg({'OP value': 'sum', "dag": "nunique", 'OP value daysum': "mean"})
    data['weekday'] = pd.Categorical(
        data['weekday'], 
        categories=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'], 
        ordered=True
    )
    data = data.sort_values(by="weekday").round(1).reset_index(drop=True)
    text_data = [str(x["OP value"]) + " over " + str(x["dag"]) for index, x in data.iterrows()]

    produced_values = [float(x) for x in data["OP value daysum"]]
    used_values = [-float(x) for x in data["OP value daysum"]]

    fig = make_subplots(rows=1, cols=2, specs=[[{'type':'domain'}, {'type':'domain'}]])

    if all(i <= 0 for i in produced_values):
        fig.add_trace(
            go.Pie(
                labels=["Not enough produced"], 
                values=[1], 
                name = "",
                marker_colors=["#989898"],
                showlegend=False,
                textinfo='none',
                hoverinfo='none',
                ),
            1, 1
        )
    else:
        fig.add_trace(
            go.Pie(
                labels=data["weekday"], 
                values=produced_values, 
                sort=False,
                customdata = text_data,
                name = "",
                textinfo="label+percent",
                marker=dict(
                    colors=[pie_colors[i] for i in data["weekday"]]
                ),
                hovertemplate = "%{label}: <br>gemiddelde: %{value} </br>totaal: %{customdata} dagen",
                domain={"x": [0.55, 1], 'y':[0.2, 0.8]}
                ),
            1, 1
        )

    if all(i <= 0 for i in used_values):
        fig.add_trace(
            go.Pie(
                labels=["Not enough produced"], 
                values=[1], 
                name = "",
                marker_colors=["#989898"],
                showlegend=False,
                textinfo='none',
                hoverinfo='none',
                ),
            1, 2
        )
    else:
        fig.add_trace(
            go.Pie(
                labels=data["weekday"], 
                values=used_values,
                sort=False,
                customdata = text_data,
                name = "",
                textinfo="label+percent",
                marker=dict(
                    colors=[pie_colors[i] for i in data["weekday"]]
                ),
                hovertemplate = "%{label}: <br>gemiddelde: %{value} </br>totaal: %{customdata} dagen",
                domain={"x": [0.55, 1], 'y':[0.2, 0.8]}
                ),
            1, 2
        )

    fig.update_traces(hole=.5, textposition='inside')

    fig.update_layout(layout,
        title_text='Productie en verbruik saldo per dag van de week',
        title_x=0.5,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.5,
            xanchor="center",
            x=0.0,
            ),
        annotations=[dict(text='Produced', x=0.18, y=0.5, font_size=20, showarrow=False),
                 dict(text='Used', x=0.8, y=0.5, font_size=20, showarrow=False)]
    )

    return fig

def figure5_data(data, week, layout):
    data = data[data["Week"] == week]
    data["time"] = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S').strftime("%H:%M:%S") for x in data["Date"]]
    data = data.groupby(['time', 'soort_dag'], as_index = False, sort=False).agg({'OP value': 'mean', "dag": "nunique"})

    fig1_tmp = data[data["soort_dag"] == "Werkdag"]
    fig2_tmp = data[data["soort_dag"] == "Weekend"]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=fig1_tmp['time'],
        y=fig1_tmp["OP value"],
        name = 'Werkdag',
        mode='lines',
        line=dict(
            shape="spline",
            smoothing=0.8,
            width=3,
            color='#fac1b7'
        ),
    ))

    fig.add_trace(go.Scatter(
        x=fig2_tmp['time'],
        y=fig2_tmp['OP value'],
        name = 'Weekend',
        mode='lines',
        line=dict(
            shape="spline",
            smoothing=0.8,
            width=3,
            color='#a9bb95'
        ),
    ))

    fig.update_layout(layout,
        title_text='24 uur profiel van de week',
        margin=dict(
            l=30,
            r=30,
            b=20,
            t=40
            ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.4,
            xanchor="center",
            x=0.25,
            ),
        hovermode='x unified',
        )



    tickvals = np.arange(0, 192).astype(int)[0::16]
    fig.update_xaxes(
                 tickmode = 'array',
                 tickvals = tickvals,
                 )

    return fig

###################################
###     All code for Plotting   ###
###################################

import dash
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np


## In auth ##########

VALID_USERNAME_PASSWORD_PAIRS = {
    'Eelco': '28e5f0d9e2d5816554623c5d19ae6b1f08ba6c2bda8e355d996cee80'
}

from dash_auth.auth import Auth
import flask, base64, hashlib
from types import MethodType

class EncryptedAuth(Auth):
    def __init__(self, app, username_password_list):
        Auth.__init__(self, app)
        self._users = username_password_list \
            if isinstance(username_password_list, dict) \
            else {k: v for k, v in username_password_list}

    def is_authorized(self):
        header = flask.request.headers.get('Authorization', None)
        if not header:
            return False
        username_password = base64.b64decode(header.split('Basic ')[1])
        username_password_utf8 = username_password.decode('utf-8')
        username, password = username_password_utf8.split(':')
        return self._users.get(username) == hashlib.new('sha224', password.encode()).hexdigest()

    def login_request(self):
        return flask.Response(
            'Login Required',
            headers={'WWW-Authenticate': 'Basic realm="User Visible Realm"'},
            status=401)

    def auth_wrapper(self, f):
        def wrap(*args, **kwargs):
            if not self.is_authorized():
                return flask.Response(status=403)

            response = f(*args, **kwargs)
            return response
        return wrap

    def index_auth_wrapper(self, original_index):
        def wrap(*args, **kwargs):
            if self.is_authorized():
                return original_index(*args, **kwargs)
            else:
                return self.login_request()
        return wrap

##########

# Not nice 
pie_colors = dict(
     Mon = '#FFEDA0',
     Tue = '#FA9FB5',
     Wed = '#A1D99B',
     Thu = '#67BD65',
     Fri = '#BFD3E6',
     Sat = '#B3DE69',
     Sun = '#FDBF6F',
)

# Get names
cache_data = read_data("data/data.pkl")

adresses = ['Tufsteen 4 + 5', 'Tufsteen 6', 'Tufsteen 7', 'Tufsteen 8 + 9']
maanden = cache_data["Maand"].unique()
maanden = dict(zip(range(0, len(maanden)), list(maanden)))

weer = pd.read_pickle("data/weer.pkl")

# global cache for buttons
cache_changed_button = []

# Actual app

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server

auth = EncryptedAuth(
    app,
    VALID_USERNAME_PASSWORD_PAIRS
)

layout = dict(
    yaxis={
        'zerolinecolor':'rgba(0.75,0.75,0.75, 0.3)',
        'zerolinewidth':1,
        'gridcolor':'rgba(0.75,0.75,0.75, 0.3)',
        'title':None,
        'showticklabels': True
    },
    xaxis={
        'tickangle':45,
        'gridcolor':'rgba(0.75,0.75,0.75, 0.3)',
        'title':None,
        'linecolor':'black',
        'showticklabels': True
    },
    title_x=0.5,
    showlegend=True,
    autosize=True,
    plot_bgcolor="#f9f9f9",
    paper_bgcolor="#f9f9f9",
    legend=dict(font=dict(size=10), orientation='h'),
) 

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
    Input('btn-1', 'n_clicks'),
    Input('btn-2', 'n_clicks')
)
def main_figure_display(adress, month, btn_1, btn_2):
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
        fig, summary = figure1b_data(data, layout)
        header = ["Overproductie volgens 0 lijn", "Capaciteit eisen volgens 0 lijn", "Gemiddelde (Ideaal)", "Capaciteit eisen volgens Ideaal"]

    else:
        msg = "None of the buttons have been clicked yet'"

        data = standardized_frame(cache_data, adress)
        summary = summarize_data(data, month, weer)
        fig = figure1a_data(data, adress, month, layout)
        header = ["Productie", "Verbruik", "Saldo", "Zon"]
    
    return fig, summary[0], header[0], summary[1], header[1], summary[2], header[2], summary[3], header[3]

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
    Output('figure-2-container', 'figure'),
    Output('figure-3-container', 'figure'),
    Output('figure-4-container', 'figure'),
    Output('figure-5-container', 'figure'),
    Input('persisted-adress', 'value'),
    Input('month-slider', 'value'),
    Input('week-slider', 'value'), 
)
def create_figures(adress, month, week):
    month_data = correct_month(cache_data, month)
    data = standardized_frame(month_data, adress)
    return figure2_data(data, adress, layout), figure3_data(data, layout), figure4_data(data, layout), figure5_data(data, week, layout)

if __name__ == '__main__':
    app.run_server(debug=True)