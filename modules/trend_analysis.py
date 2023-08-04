from shiny import ui, module, Inputs, Outputs, Session, reactive
from shinywidgets import output_widget, render_widget
from utils.ui_utils import panel_box, container
from utils.server_utils import collapse_soil_cols, get_date_range, get_variables, expand_soil_cols
from config import sensor_info
from plotly import (
    express as px,
    graph_objects as go,
)
from plotly.subplots import make_subplots

import pandas as pd


@module.ui
def trend_analysis_ui():
    """
    資料篩選面板
    """
    return container(
        ui.row(
            ui.column(
                3,
                panel_box(
                    ui.h5(
                        {"class": "card-title"},
                        "選擇感測器位置"
                    ),
                    ui.input_radio_buttons(
                        id="sensor_location",
                        label="位置",
                        choices=sensor_info,
                        selected="indoor",
                    ),
                ),
                class_="h-full"
            ),
            ui.column(
                3,
                panel_box(
                    ui.h5(
                        {"class": "card-title"},
                        "篩選測量區間"
                    ),
                    ui.div(
                        {"class": "d-flex row"},
                        ui.input_selectize(
                            id="frequency_select",
                            label="頻率",
                            choices={
                                "default": "預設（每五分鐘）",
                                "hour": "時",
                                "day": "日"
                            },
                        ),
                        ui.input_date_range(
                            id="input_date_range",
                            label="測量區間",
                            separator=" 至 ",
                            language="zh-TW",
                        ),
                    ),
                ),
            ),
            ui.column(
                6,
                panel_box(
                    ui.h5(
                        {"class": "card-title"},
                        "篩選變數",
                    ),
                    ui.input_selectize(
                        id="variable_select",
                        label="變數",
                        choices=[],
                        multiple=True,
                        width="100%"
                    ),
                )
            ),
            class_="mb-3",
        ),
        panel_box(
            ui.h5(
                {"class": "card-title"},
                "趨勢圖"
            ),
            output_widget(
                id="user_select_time_variable_plot",
                height="auto"
            )
        )
    ),


@module.ui
def trend_analysis_ui_deprecated():
    return container(
        ui.navset_tab_card(
            ui.nav(
                "各變數趨勢圖",
                ui.div(
                    {"id": "plots"},
                )
            )
        )
    ),


@module.server
def trend_analysis_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    indoor_sheet: pd.DataFrame,
    outdoor_sheet: pd.DataFrame,
    user_sheet: pd.DataFrame
):
    @reactive.Effect
    @reactive.event(input.sensor_location)
    def _():
        location = input.sensor_location()
        df = None
        if location == "indoor":
            df = indoor_sheet.get()
        else:
            df = outdoor_sheet.get()

        m, M = get_date_range(df)

        ui.update_date_range(
            id="input_date_range",
            start=m,
            end=M,
            min=m,
            max=M,
        )
        variables = collapse_soil_cols(get_variables(df))
        ui.update_selectize(
            id="variable_select",
            choices=variables,
            selected=variables[1]
        )

    @reactive.Calc
    def set_user_sheet():
        location = input.sensor_location()
        m, M = input.input_date_range()
        new_cols = ['時間', '原本的時間'] + \
            list(expand_soil_cols(input.variable_select()))

        df = None
        if location == "indoor":
            df = indoor_sheet.get().copy()
        else:
            df = outdoor_sheet.get().copy()

        mask = ((df['時間'].dt.date >= m) & (df['時間'].dt.date <= M))
        df = df.loc[mask]
        df['原本的時間'] = df['時間']

        if input.frequency_select() == "hour":
            df = df.resample('H', on='時間').mean()
            df['時間'] = df.index.strftime('%Y/%m/%d %H:%M')
        elif input.frequency_select() == "day":
            df = df.resample('D', on='時間').mean()
            df['時間'] = df.index.strftime('%Y/%m/%d')
        else:
            df['時間'] = df['時間'].dt.strftime('%Y/%m/%d %H:%M:%S')

        df = df[new_cols]
        user_sheet.set(df)
        print("user sheet has been set.")
        return df

    @output
    @render_widget
    def user_select_time_variable_plot():
        fig = go.Figure()
        df = set_user_sheet()
        columns = df.drop(["時間", "原本的時間"], axis=1).columns.tolist()

        for i, column in enumerate(columns):
            fig.add_trace(
                go.Scatter(
                    y=df[column],
                    x=df["原本的時間"],
                    name=column
                ),
            )

        fig.update_layout(
            autosize=True,
            height=350,
            margin={
                "t": 0,
                "b": 0
            },
        )
        return fig


@module.server
def trend_analysis_server_deprecated(
    input: Inputs,
    output: Outputs,
    session: Session,
    user_sheet: pd.DataFrame,
):
    @output
    @render_widget
    def temperature():
        df = user_sheet.get()
        fig = px.line(df, x="原本的時間", y="氣溫")
        return fig

    @output
    @render_widget
    def pressure():
        df = user_sheet.get()
        fig = px.line(df, x="原本的時間", y="氣壓")
        return fig

    @output
    @render_widget
    def humidity():
        df = user_sheet.get()
        fig = px.line(df, x="原本的時間", y="空氣相對溼度")
        return fig

    @output
    @render_widget
    def brightness():
        df = user_sheet.get()
        fig = px.line(df, x="原本的時間", y="光強度")
        return fig

    @output
    @render_widget
    def winddirection():
        df = user_sheet.get()
        fig = px.line(df, x="原本的時間", y="風向")
        return fig

    @output
    @render_widget
    def windspeed():
        df = user_sheet.get()
        fig = px.line(df, x="原本的時間", y="風速")
        return fig

    @output
    @render_widget
    def soilsensor1():
        df = user_sheet.get()
        fig = make_subplots(rows=3, cols=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤溫度1"]), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤濕度1"]), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤電導度1"]), row=3, col=1)
        fig.update_layout(height=600)
        return fig

    @output
    @render_widget
    def soilsensor2():
        df = user_sheet.get()
        fig = make_subplots(rows=3, cols=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤溫度2"]), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤濕度2"]), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤電導度2"]), row=3, col=1)
        fig.update_layout(height=600)
        return fig

    @output
    @render_widget
    def soilsensor3():
        df = user_sheet.get()
        fig = make_subplots(rows=3, cols=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤溫度3"]), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤濕度3"]), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤電導度3"]), row=3, col=1)
        fig.update_layout(height=600)
        return fig

    @output
    @render_widget
    def soilsensor4():
        df = user_sheet.get()
        fig = make_subplots(rows=3, cols=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤溫度4"]), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤濕度4"]), row=2, col=1)
        fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤電導度4"]), row=3, col=1)
        fig.update_layout(height=600)
        return fig

    @reactive.Effect
    def _():
        ui.remove_ui(selector=".card:has(.plot)", multiple=True)

        user_select_variable = collapse_soil_cols(
            user_sheet.get().columns.tolist())

        if "氣壓" in user_select_variable:
            ui.insert_ui(
                panel_box(
                    {"class": "plot"},
                    ui.h5(
                        {"class": "card-title"},
                        "氣壓",
                    ),
                    output_widget(id="pressure")
                ),
                "#plots"
            )

        if "氣溫" in user_select_variable:
            ui.insert_ui(
                panel_box(
                    {"class": "plot"},
                    ui.h5(
                        {"class": "card-title"},
                        "氣溫",
                    ),
                    output_widget(id="temperature")
                ),
                "#plots"
            )

        if "空氣相對溼度" in user_select_variable:
            ui.insert_ui(
                panel_box(
                    {"class": "plot"},
                    ui.h5(
                        {"class": "card-title"},
                        "空氣相對溼度",
                    ),
                    output_widget(id="humidity")
                ),
                "#plots"
            )

        if "光強度" in user_select_variable:
            ui.insert_ui(
                panel_box(
                    {"class": "plot"},
                    ui.h5(
                        {"class": "card-title"},
                        "光強度",
                    ),
                    output_widget(id="brightness")
                ),
                "#plots"
            )

        if "風向" in user_select_variable:
            ui.insert_ui(
                panel_box(
                    {"class": "plot"},
                    ui.h5(
                        {"class": "card-title"},
                        "風向",
                    ),
                    output_widget(id="winddirection")
                ),
                "#plots"
            )

        if "風速" in user_select_variable:
            ui.insert_ui(
                panel_box(
                    {"class": "plot"},
                    ui.h5(
                        {"class": "card-title"},
                        "風速",
                    ),
                    output_widget(id="windspeed")
                ),
                "#plots"
            )

        if "土壤感測器1" in user_select_variable:
            ui.insert_ui(
                panel_box(
                    {"class": "plot"},
                    ui.h5(
                        {"class": "card-title"},
                        "土壤感測器1",
                    ),
                    output_widget(id="soilsensor1")
                ),
                "#plots"
            )

        if "土壤感測器2" in user_select_variable:
            ui.insert_ui(
                panel_box(
                    {"class": "plot"},
                    ui.h5(
                        {"class": "card-title"},
                        "土壤感測器2",
                    ),
                    output_widget(id="soilsensor2")
                ),
                "#plots"
            )

        if "土壤感測器3" in user_select_variable:
            ui.insert_ui(
                panel_box(
                    {"class": "plot"},
                    ui.h5(
                        {"class": "card-title"},
                        "土壤感測器3",
                    ),
                    output_widget(id="soilsensor3")
                ),
                "#plots"
            )

        if "土壤感測器4" in user_select_variable:
            ui.insert_ui(
                panel_box(
                    {"class": "plot"},
                    ui.h5(
                        {"class": "card-title"},
                        "土壤感測器4",
                    ),
                    output_widget(id="soilsensor4")
                ),
                "#plots"
            )
