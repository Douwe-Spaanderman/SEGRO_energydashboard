###################################
###     All code for Plotting   ###
###################################

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from scipy import signal
import numpy as np
from datetime import datetime, date, timedelta
import pandas as pd
from lib.utils.utils import human_format

### Setup layout and color
pie_colors = dict(
     Mon = '#FFEDA0',
     Tue = '#FA9FB5',
     Wed = '#A1D99B',
     Thu = '#67BD65',
     Fri = '#BFD3E6',
     Sat = '#B3DE69',
     Sun = '#FDBF6F',
)

layout = dict(
    yaxis={
        'zerolinecolor':'rgba(0.75,0.75,0.75, 0.3)',
        'zerolinewidth':1,
        'gridcolor':'rgba(0.75,0.75,0.75, 0.3)',
        'title':"kWh",
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
    legend=dict(font=dict(size=10), orientation='h')
)

### Setup layout and color ###

def figure1a_data(data_cache, adresses, month):
    # Overall info
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    colors = []
    line_color = ['rgb(99, 110, 250)', 'rgb(239, 85, 59)', 'rgb(0, 204, 150)', 'rgb(171, 99, 250)', 'rgb(255, 161, 90)', 'rgb(25, 211, 243)', 'rgb(255, 102, 146)', 'rgb(182, 232, 128)', 'rgb(255, 151, 255)', 'rgb(254, 203, 82)']
    for j in range(0, len(data_cache["Maand"].unique())):
        if j >= int(month[0]) and j < int(month[1]):
            colors.append(1)
        else:
            colors.append(0.2)

    for i, adress in enumerate(adresses):
        data = data_cache[data_cache["adress"] == adress]
        data["Max value"] = data["OP value"]
        data = data.groupby(['Maand'], as_index = False, sort=False).agg({'OP value': 'sum', "dag": "nunique", 'BP montly value': "mean", "OP value daysum": "mean", "OP value weeksum": 'mean', 'Max value': 'max'})
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
            ),
            secondary_y=False)

            fig.add_trace(go.Bar(
                x=data['Maand'],
                y=data["OP value"],
                name = 'Saldo',
                marker=dict(
                    opacity=colors,
                    ),
            ),
            secondary_y=False)

            fig.add_trace(go.Bar(
                x=data['Maand'],
                y=data["BP montly value"],
                name = 'Produced',
                marker=dict(
                    opacity=colors,
                    ),
                customdata = text_data,
                hovertemplate = "%{y}<br>dagelijks gemiddelde: %{customdata[0]} </br>wekelijks gemiddelde: %{customdata[1]}",
            ),
            secondary_y=False)

            fig.add_trace(go.Scatter(
                x=data['Maand'],
                y=data["Max value"],
                hoverinfo='skip',
                showlegend=False,
                mode='lines',
                line=dict(
                    color=line_color[i],
                    ),
            ),
            secondary_y=True)
            
        else:
            fig.add_trace(go.Bar(
                x=data['Maand'],
                y=data["OP value"],
                name = adress,
                customdata = text_data,
                marker=dict(
                    opacity=colors,
                    color=line_color[i]
                    ),
                hovertemplate = "%{y}<br>dagelijks gemiddelde: %{customdata[0]} </br>wekelijks gemiddelde: %{customdata[1]}",
            ),
            secondary_y=False)

            fig.add_trace(go.Scatter(
                x=data['Maand'],
                y=data["Max value"],
                hoverinfo='skip',
                showlegend=False,
                mode='lines',
                line=dict(
                    color=line_color[i],
                    ),
            ),
            secondary_y=True)

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
            )
        )

    fig.update_xaxes(showline=False, showgrid=False)
    fig.update_yaxes(showline=True, zeroline=True, zerolinecolor="black", linecolor="black", zerolinewidth=1, range=[-15000, 30000])
    fig.update_yaxes(title_text="Maximale kWh", secondary_y=True, zeroline=False, range=[-20, 40])

    return fig

def figure1b_data(data_cache, capaciteit, ophalen):
    # Overall info
    fig = go.Figure()

    data = data_cache.groupby(['Maand'], as_index = False, sort=False).agg({'OP value': 'sum'})
    best_line = data["OP value"].sum()/len(data)

    data["delta"] = data["OP value"] - best_line

    data["positief"] = [0 if int(x) <= 0 else x for x in data["OP value"]]
    data["negatief"] = [0 if int(x) > 0 else x for x in data["OP value"]]

    # Create saldo
    data["saldo"] = 0
    for idx in range(len(data)):
        x = data.loc[idx, "OP value"]
        if idx <= 0:
            data.loc[idx, "saldo"] = x
        elif x >= 0:
            x = x + data.loc[idx-1, "saldo"]
            if x > capaciteit:
                data.loc[idx, "saldo"] = capaciteit
            else:
                data.loc[idx, "saldo"] = x
        else:
            # Check if ophalen > capaciteteit
            if ophalen > capaciteit:
                ophalen = capaciteit

            # do by 30* instead of actuall number of days
            y = (ophalen * 6 * 30) + x + data.loc[idx-1, "saldo"]
            if y > capaciteit:
                data.loc[idx, "saldo"] = capaciteit
            else:
                data.loc[idx, "saldo"] = y

    overproduced = data["positief"].sum()
    underproduced = data["negatief"].sum()

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

    fig.add_trace(go.Scatter(
        x=data['Maand'],
        y=data["saldo"],
        name = 'Saldo op basis van ingevoerde capaciteit en opname uit net',
        mode='lines',
        line=dict(
            shape="spline",
            smoothing=0.8,
            #color='#fac1b7',
            width=4,
        )
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

    return fig, [f'{human_format(int(overproduced))}', f'{human_format(abs(int(underproduced)))}', f'{human_format(int(best_line))}', f'{human_format(abs(int(underproduced_perfect)))}']

def figure2_data(data_cache, adresses):
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

def figure3_data(data, capaciteit, ophalen, week=False):
    if week != False:
        text_tile = '24 uur profiel van de geselecteerde week'
        data = data[data["Week"] == week]
    else:
        text_tile = '24 uur profiel van de geselecteerde maand(en)'
    data["time"] = [datetime.strptime(x, '%Y-%m-%d %H:%M:%S').strftime("%H:%M:%S") for x in data["Date"]]
    data = data.groupby(['time', 'soort_dag'], as_index = False, sort=False).agg({'OP value': 'mean', "dag": "nunique"})


    fig1_tmp = data[data["soort_dag"] == "Werkdag"]
    fig2_tmp = data[data["soort_dag"] == "Weekend"]

    #tmp = fig1_tmp
    #print(tmp)

    
    #if ophalen != 0:
        #for idx in range(len(tmp)):
            #x = data.loc[idx, "OP value"]
            #y = data.loc[idx, "snachts opladen"]
            #if y < x:

    #for tmp in [fig1_tmp, fig2_tmp]
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
        title_text=text_tile,
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

def figure4_data(data):
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