import os
import csv
import sys
import re
import fileinput

import pandas as pd
import numpy as np

import base64
import matplotlib.pyplot as plt
from IPython.display import HTML

from google.colab import drive
from google.colab import widgets
from google.colab import output

from bokeh.palettes import Spectral10, brewer, Set3_12
from bokeh.models import ColumnDataSource, LabelSet
from bokeh.models.tools import HoverTool
from bokeh.plotting import figure, show
from bokeh.layouts import widgetbox
from bokeh.models import FixedTicker
from bokeh.models.widgets import DataTable, DateFormatter, TableColumn
import bokeh.io
bokeh.io.output_notebook()

from bokeh.palettes import Dark2_5 as palette
import itertools 

FIG_SIZE = (17, 8)
PLOT_HEIGHT = 550
PLOT_WIDTH = 1200
FONTSIZE = 14

#@title Helper functions

# https://stackoverflow.com/a/42907645/564240
def create_download_link(df, title = "Download CSV file", filename = "data.csv"):
    csv = df.to_csv()
    b64 = base64.b64encode(csv.encode())
    payload = b64.decode()
    html = '<a download="{filename}" href="data:text/csv;base64,{payload}" target="_blank">{title}</a>'
    html = html.format(payload=payload, title=title, filename=filename)
    return HTML(html)

def tabbar(params):
    tb = widgets.TabBar(list(params.keys()))
    for index, key in enumerate(params.keys()):
        with tb.output_to(index):
            f, f_args = params[key]
            f(*f_args)

def plot_matplotlib_(df, title, xlabel, ylabel, stacked):
    alpha = 0.5
    if stacked:
        df.plot(kind='area', stacked=True, figsize=FIG_SIZE, alpha=alpha)
    else:
        df.plot(figsize=FIG_SIZE, alpha=alpha)
    plt.grid(True, axis='y')
    plt.xlabel(xlabel, fontsize=FONTSIZE)
    plt.ylabel(ylabel, fontsize=FONTSIZE)
    plt.title(title, fontsize=FONTSIZE+2)
    plt.show()

def plot_bokeh_(df, title, xlabel, ylabel, stacked, need_table):
    tmp = df.reset_index().fillna(0)
    source = ColumnDataSource(tmp)
    p = figure(x_axis_type="datetime", plot_height=PLOT_HEIGHT, plot_width=PLOT_WIDTH)

    tooltips = list()
    if stacked:
        clmns=list(df.columns.values)
        if len(clmns) > 2:
            color = brewer['Spectral'][len(clmns)]
        elif len(clmns) == 2:
            color = [Spectral10[1], Spectral10[3]]
        else:
            color = [Spectral10[0]]
        p.varea_stack(stackers=clmns, x=df.index.name, color=color, legend_label=clmns, source=source)
        p.legend.items.reverse()
        tooltips = [(column, "@" + column) for column in clmns]
    else:
      for index, column in enumerate(list(tmp.columns.values)):
          if column == df.index.name: 
              continue
          legend=column + " "    
          if index < 10:
              color = Spectral10[index]
          elif index < 12:
              color = Set3_12[index]
          else:
              color = Spectral10[len(Spectral10) % index]
          p.line(x=df.index.name, y=column, line_width=2, source=source, color=color, legend=legend)
          tooltips.append(
              (legend, "@" + column + ("{0.00}" if tmp.at[0, column] < 1 else "") + " | @" + df.index.name + "{%F}")
          )

    p.legend.click_policy='hide'
    p.legend.location = "top_left"
    p.title.text = title
    p.xaxis.axis_label = xlabel
    p.yaxis.axis_label = ylabel
    p.y_range.start = 0    
    p.left[0].formatter.use_scientific = False

    hover = HoverTool(tooltips=tooltips, formatters={'@' + df.index.name: 'datetime'})
    p.add_tools(hover)

    show(p)

    if need_table:
        columns = list()
        for index, column in enumerate(list(tmp.columns.values)):
            if column == df.index.name: 
                columns.append(
                    TableColumn(field=column, title=column, formatter=DateFormatter())
                ) 
            else:
                columns.append(
                    TableColumn(field=column, title=column)
                )

        data_table = DataTable(source=source, columns=columns, width=PLOT_WIDTH, height=PLOT_HEIGHT)
        show(widgetbox(data_table))

        display(create_download_link(tmp))

PLOT_MATPLOTLIB=False
def plot_df(df, title, xlabel, ylabel, stacked=False, need_table=True):
    if PLOT_MATPLOTLIB:
        plot_matplotlib_(df, title, xlabel, ylabel, stacked)
    else:
        plot_bokeh_(df, title, xlabel, ylabel, stacked, need_table)

def read_csvs_in_folder(source_folder):
    files = [os.path.join(source_folder, f)  for f in os.listdir(source_folder) if re.match(r'.*.csv', f)] 
    if len(files) == 1:
        pd.read_csv(files[0])
    dfs = [pd.read_csv(file_) for file_ in files]
    return pd.concat(dfs)        

def scatter_plot(data_to_display, title, xlabel, ylabel, hover_tooltips, x, y, text):
    def scatter_plot_helper(p, df, x, y, marker, fill_color, text):
        source = ColumnDataSource(df)
        p.scatter(
            x=x, y=y, marker=marker, source=source,
            line_color=fill_color, fill_color=fill_color, fill_alpha=0.5, size="Size")
        
        p.add_layout(
            LabelSet(
                x=x, y=y, text=text, 
                level='glyph',text_font_size='9pt',
                text_color=fill_color,
                x_offset=7, y_offset=7, 
                source=source, render_mode='canvas')
        )
    p = figure(plot_height=PLOT_HEIGHT, plot_width=PLOT_WIDTH)
    p.add_tools(HoverTool(tooltips=hover_tooltips))

    for (data_, figure_, color_) in data_to_display:
        scatter_plot_helper(p, data_, x, y, figure_, color_, text)

    p.legend.location = "top_left"
    p.title.text = title
    p.xaxis.axis_label = xlabel
    p.yaxis.axis_label = ylabel
    p.left[0].formatter.use_scientific = False
    p.below[0].formatter.use_scientific = False
    show(p)
