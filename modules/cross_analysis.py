from shiny import ui, module, Inputs, Outputs, Session, reactive
from shiny.reactive import Value
from shinywidgets import output_widget, render_widget
from utils.ui_utils import panel_box, container
from utils.server_utils import get_variables, get_date_range, collapse_soil_cols
from config import sensor_info
import pandas as pd
from plotly import graph_objects as go


@module.ui
def cross_analysis_ui():
    """
    交叉分析 ui

    """

    return container(
        ui.div(
            ui.row(
                ui.column(
                    4,
                    panel_box(
                        ui.h5(
                            {"class": "card-title"},
                            "變數 1"
                        ),
                        ui.input_selectize(
                            id="cross_analysis_sensor_1",
                            label="感測器位置",
                            choices=sensor_info,
                        ),
                        ui.input_selectize(
                            id="cross_analysis_var_1",
                            label="變數",
                            choices=[],
                        ),
                    ),
                ),
                ui.column(
                    4,
                    panel_box(
                        ui.h5(
                            {"class": "card-title"},
                            "變數 2"
                        ),
                        # TODO: input_selectize broken
                        ui.input_select(
                            id="cross_analysis_sensor_2",
                            label="感測器位置",
                            choices=sensor_info,
                            selectize=True,
                            selected="outdoor"
                        ),
                        ui.input_selectize(
                            id="cross_analysis_var_2",
                            label="變數",
                            choices=[],
                        ),
                    ),
                ),
                ui.column(
                    4,
                    panel_box(
                        ui.panel_conditional(
                            "input.cross_analysis_sensor_1 && input.cross_analysis_sensor_2 && input.cross_analysis_var_1 && input.cross_analysis_var_2",
                            ui.h5(
                                {"class": "card-title"},
                                "篩選測量區間"
                            ),
                            ui.input_selectize(
                                id="frequency_select_alt",
                                label="頻率",
                                choices={
                                    "default": "預設（每五分鐘）",
                                    "hour": "時",
                                    "day": "日"
                                },
                            ),
                            ui.input_date_range(
                                id="input_date_range_alt",
                                label="測量區間",
                                language="zh-TW",
                            ),
                        )
                    )
                ),
                {"class": "mb-3"}
            ),
        ),

        panel_box(
            ui.h5(
                {"class": "card-title"},
                "散佈圖"
            ),
            output_widget(id="cross_analysis", height="auto")
        ),
    )


@module.server
def cross_analysis_server(
    input: Inputs,
    output: Outputs,
    session: Session,
    indoor_sheet: Value,
    outdoor_sheet: Value,
):
    """
    交叉分析 server
    
    """

    @reactive.Effect
    @reactive.event(input.cross_analysis_sensor_1)
    def _():
        location = input.cross_analysis_sensor_1()
        df = None
        if location == "indoor":
            df = indoor_sheet.get()
        else:
            df = outdoor_sheet.get()

        variables = collapse_soil_cols(get_variables(df))
        ui.update_selectize(
            id="cross_analysis_var_1",
            choices=variables,
            selected=variables[0]
        )

    @reactive.Effect
    @reactive.event(input.cross_analysis_sensor_2)
    def _():
        location = input.cross_analysis_sensor_2()
        df = None
        if location == "indoor":
            df = indoor_sheet.get()
        else:
            df = outdoor_sheet.get()

        variables = get_variables(df)
        ui.update_selectize(
            id="cross_analysis_var_2",
            choices=variables,
            selected=variables[0]
        )

    @reactive.Effect
    @reactive.event(input.cross_analysis_sensor_1, input.cross_analysis_sensor_2)
    def _():
        location1 = input.cross_analysis_sensor_1()
        location2 = input.cross_analysis_sensor_2()

        df1, df2 = None, None

        if location1 == "indoor":
            df1 = indoor_sheet.get()
        else:
            df1 = outdoor_sheet.get()

        if location2 == "indoor":
            df2 = indoor_sheet.get()
        else:
            df2 = outdoor_sheet.get()

        m1, M1 = get_date_range(df1)
        m2, M2 = get_date_range(df2)

        m = max(m1, m2)
        M = min(M1, M2)

        ui.update_date_range(
            id="input_date_range_alt",
            start=m,
            end=M,
            min=m,
            max=M,
        )

    @output
    @render_widget
    def cross_analysis():
        with reactive.isolate():
            location1 = input.cross_analysis_sensor_1()
            location2 = input.cross_analysis_sensor_2()

        fig = go.Figure()
        column1 = input.cross_analysis_var_1()
        column2 = input.cross_analysis_var_2()


        var1_label_name = sensor_info[location1] + column1
        var2_label_name = sensor_info[location2] + column2


        df1, df2 = None, None

        if location1 == "indoor":
            df1 = indoor_sheet.get()
        else:
            df1 = outdoor_sheet.get()

        if location2 == "indoor":
            df2 = indoor_sheet.get()
        else:
            df2 = outdoor_sheet.get()

        m, M = input.input_date_range_alt()
        mask1 = ((df1['時間'].dt.date >= m) & (df1['時間'].dt.date <= M))
        df1 = df1.loc[mask1]
        mask2 = ((df2['時間'].dt.date >= m) & (df2['時間'].dt.date <= M))
        df2 = df2.loc[mask2]

        if input.frequency_select_alt() == "hour":
            df1 = df1.resample('H', on='時間').mean()
            df2 = df2.resample('H', on='時間').mean()
        elif input.frequency_select_alt() == "day":
            df1 = df1.resample('D', on='時間').mean()
            df2 = df2.resample('D', on='時間').mean()

        try:
            fig.add_trace(
                go.Scatter(
                    x=df1[column1],
                    y=df2[column2],
                    mode='markers'
                )
            )
        except KeyError as e:
            pass

        fig.update_layout(
            autosize=True,
            height=350,
            xaxis_title=var1_label_name,
            yaxis_title=var2_label_name,
            margin={
                "t": 0,
                "b": 0
            }
        )
        return fig
