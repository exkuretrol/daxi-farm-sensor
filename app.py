from pathlib import Path
from htmltools import Tag, TagChild
from shiny import App, Inputs, Outputs, Session, ui, render, reactive
from shiny.types import NavSetArg
from tomlkit import loads
import asyncio
import pandas as pd
from plotly import express as px
from plotly.subplots import make_subplots
from plotly import graph_objects as go
from shinywidgets import output_widget, render_widget
import numpy as np
from collections import defaultdict
import io
from typing import List

# project configuration

root_dir = Path(__file__).parent

public_dir = root_dir / "public"

config = loads((root_dir / "secrets.toml").open().read())

css_path = public_dir / "css" / "style.css"

js_path = public_dir / "js" / "main.js"

# sheet configuration

sheet_config = config.get("sheet")

sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_config.get('id')}"

# sensors dict

sensor_dict = {
    "indoor": "溫室",
    "outdoor": "室外"
}

# HTML elements


def container(*args: TagChild, _class=""):
    return ui.div(
        {"class": "container" + " " + _class},
        *args,
    )


def faicon(_class="") -> Tag:
    return ui.tags.i(
        {"class": _class}
    )


def spacer():
    """
    元素間空格
    """
    return ui.div({"class": "mt-2 mb-2"})


def panel_box(*args, **kwargs):
    return ui.div(
        {"class": "card mb-3 h-100"},
        ui.div(
            {"class": "card-body d-flex flex-column"},
            *args
        ),
        **kwargs
    )


def load_sheet(location: str) -> pd.DataFrame:
    """
    讀取表格
    """
    csv_url = f"{sheet_url}/export?format=csv&gid={sheet_config.get(location)}"

    df = pd.read_csv(csv_url, dtype=str)
    df.replace(["999", "TO", "undefined", "", "NA"], np.nan, inplace=True)

    common_cols = ['氣壓', '氣溫', '空氣相對溼度', '光強度', '風向', '風速']
    soil = ['土壤溫度', '土壤濕度', '土壤電導度']

    new_cols = None

    if location == "indoor":
        soil_cols = [i + str(j) for j in range(1, 3) for i in soil]
        new_cols = common_cols + soil_cols

    elif location == "outdoor":
        soil_cols = [i + str(j) for j in range(1, 5) for i in soil]
        rain_cols = ['雨量', 'rain_event', 'rain_totalevent', 'rain_IPH']
        new_cols = common_cols + soil_cols + rain_cols

    df = df.assign(**df[new_cols].astype("float64"))
    new_cols = ['時間'] + new_cols
    df = df[new_cols]

    df['時間'] = pd.to_datetime(df['時間'], format='%Y-%m-%d %H:%M:%S')
    print(f"sheet {location} loaded successfully!")
    return df


def expand_soil_cols(cols):
    """
    展開土壤感測器欄位
    土壤感測器1 -> ...溫度 ...濕度 ...電導度
    """
    l = list()
    for i in cols:
        if str(i).startswith("土壤感測器"):
            num = i[-1]
            l.append("土壤溫度" + num)
            l.append("土壤濕度" + num)
            l.append("土壤電導度" + num)
        else:
            l.append(i)
    return l


def collapse_soil_cols(cols):
    """
    縮減土壤感測器欄位
    ...溫度 ...濕度 ...電導度 -> 土壤感測器1
    """
    def isSoil(x: str):
        return x.startswith("土壤")

    def notSoil(x: str):
        return not x.startswith("土壤")

    num = [int(j) for j in list(set([i[-1]
                                     for i in list(filter(isSoil, cols))]))]
    num.sort()
    return list(filter(notSoil, cols)) + ["土壤感測器" + str(j) for j in num]


def get_date_range(sheet: pd.DataFrame):
    """
    取得資料框的日期區間
    """
    m = sheet['時間'].min().date()
    M = sheet['時間'].max().date()
    return m, M


def get_variables(sheet: pd.DataFrame):
    """
    取得資料框除了時間以外的所有變數名稱
    """
    return sheet.columns.drop('時間').tolist()


def data_range_filter_panel():
    return ui.row(
        ui.column(
            4,
            panel_box(
                ui.h5(
                    {"class": "card-title"},
                    "選擇感測器位置"
                ),
                ui.input_radio_buttons(
                    id="sensor_location",
                    label="感測器位置",
                    choices=sensor_dict,
                    selected="indoor",
                ),
            ),
            class_="h-full"
        ),
        ui.column(
            8,
            panel_box(
                ui.h5(
                    {"class": "card-title"},
                    "篩選測量區間"
                ),
                ui.div(
                    {"class": "d-flex row"},
                    ui.input_date_range(
                        id="input_date_range",
                        label="測量區間",
                        language="zh-TW",
                    ),
                    ui.input_selectize(
                        id="frequency_select",
                        label="頻率",
                        choices={
                            "default": "預設（每五分鐘）",
                            "hour": "時",
                            "day": "日"
                        },
                        selected="default"
                    ),
                ),
                ui.input_selectize(
                    id="variable_select",
                    label="變數",
                    choices=[],
                    multiple=True,
                    width="100%"
                ),
                ui.input_action_button(
                    id="btn_filter",
                    label="查詢",
                    class_="me-auto",
                ),
            ),
        ),
        class_="mb-3",
    )

# 導覽列


def nav_controls() -> List[NavSetArg]:
    return [
        ui.nav(
            "資料說明",
            container(
                ui.markdown((root_dir / "introduction.md").open().read()),
                _class="typographic",
            ),
            icon=faicon("fa-solid fa-circle-info me-1")
        ),
        ui.nav(
            "變數間趨勢圖",
            container(
                data_range_filter_panel(),
                panel_box(
                    ui.h5(
                        {"class": "card-title"},
                        "趨勢圖"
                    ),
                    output_widget(id="user_select_time_variable_plot", height="auto")
                ),
            ),
            icon=faicon("fa-solid fa-satellite-dish me-1")
        ),
        ui.nav(
            "敘述統計圖",
            container(
                ui.navset_tab_card(
                    ui.nav(
                        "各變數趨勢圖",
                        ui.div(
                            {"id": "plots"},
                        )
                    )
                )
            ),
            icon=faicon("fa-solid fa-compass-drafting me-1")
        ),
        ui.nav(
            "資料框",
            container(
                panel_box(
                    ui.h5(
                        {"class": "card-title"},
                        "indoor"
                    ),
                    ui.output_data_frame(id="indoor_df")
                ),
                panel_box(
                    ui.h5(
                        {"class": "card-title"},
                        "outdoor"
                    ),
                    ui.output_data_frame(id="outdoor_df")
                ),
                panel_box(
                    ui.h5(
                        {"class": "card-title"},
                        "user"
                    ),
                    ui.output_data_frame(id="user_df")
                ),
                # panel_box(
                #     ui.h5(
                #         {"class": "card-title"},
                #         "資料框非缺失值統計",
                #     ),
                #     ui.output_text_verbatim(
                #         id="sheet_info",
                #     )
                # )
            ),
            icon=faicon("fa-solid fa-table me-1")
        ),
        ui.nav_spacer(),
        ui.nav_control(
            ui.input_action_button(
                id="btn_reload_sheet",
                label="重新讀取表格",
                class_="nav-link bg-transparent border-0",
                icon=faicon("fa-solid fa-bomb")
            ),
            # ui.a(
            #     "所選的感測器：",
            #     ui.output_text("which_sensor"),
            #     {
            #         "class": "d-flex disabled"
            #     }
            # ),
        ),
        ui.nav(
            "已知問題",
            container(
                ui.markdown((root_dir / "issues.md").open().read()),
            ),
            icon=faicon("fa-solid fa-bug me-1")
        ),
        ui.nav_control(
            ui.a(
                faicon(
                    "fa-solid fa-arrow-up-right-from-square me-1"
                ),
                "表單連結",
                {
                    "href": sheet_url,
                    "target": "_blank"
                }
            ),
        ),
        ui.nav_control(
            ui.a(
                faicon("fa-brands fa-github me-1"),
                "查看原始碼",
                href="https://github.com/exkuretrol/daxi-farm-sensor",
                target="_blank"
            )
        )
    ]


# Part 1: ui


def UI():
    return ui.page_navbar(
        *nav_controls(),
        title="大溪農場物聯網",
        position="fixed-top",
        footer=ui.div(
            ui.head_content(
                ui.include_js(js_path),
                ui.include_css(css_path),
                ui.tags.script(
                    src="https://kit.fontawesome.com/365bdfe65e.js",
                    crossorigin="anonymous"
                )
            )
        )
    )


# Part 2: server


def server(input: Inputs, output: Outputs, session: Session):
    # sheet = reactive.Value(load_sheet("indoor"))
    indoor_sheet = reactive.Value(load_sheet("indoor"))
    outdoor_sheet = reactive.Value(load_sheet("outdoor"))
    user_sheet = reactive.Value()

    @reactive.Effect
    @reactive.event(input.btn_reload_sheet)
    def reload_sheet():
        # sheet.set(load_sheet(input.sensors()))
        indoor_sheet.set(load_sheet("indoor"))
        outdoor_sheet.set(load_sheet("outdoor"))

    # @output
    # @render.text
    # def sheet_info():
    #     buffer = io.StringIO()
    #     sheet.get().info(buf=buffer)
    #     return buffer.getvalue()

    # @output
    # @render.text
    # def which_sensor():
    #     return sensor_dict[input.sensors()]

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
            selected=variables
        )

    @output
    @render.data_frame
    def indoor_df():
        return indoor_sheet.get()

    @output
    @render.data_frame
    def outdoor_df():
        return outdoor_sheet.get()

    @output
    @render.data_frame
    def user_df():
        return user_sheet.get()

    @reactive.Effect
    @reactive.event(input.btn_filter)
    def _():
        location = input.sensor_location()
        df = None
        if location == "indoor":
            df = indoor_sheet.get().copy()
        else:
            df = outdoor_sheet.get().copy()

        m, M = input.input_date_range()
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

        new_cols = ['時間', '原本的時間'] + \
            list(expand_soil_cols(input.variable_select()))
        df = df[new_cols]
        user_sheet.set(df)
        print("user sheet has been set.")

    @output
    @render_widget
    def user_select_time_variable_plot():
        fig = go.Figure()
        df = user_sheet.get()
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
            height=450
        )
        return fig

    # plots ----
    # @output
    # @render_widget
    # def temperature():
    #     df = user_sheet.get()
    #     fig = px.line(df, x="原本的時間", y="氣溫")
    #     return fig

    # @output
    # @render_widget
    # def pressure():
    #     df = user_sheet.get()
    #     fig = px.line(df, x="原本的時間", y="氣壓")
    #     return fig

    # @output
    # @render_widget
    # def humidity():
    #     df = user_sheet.get()
    #     fig = px.line(df, x="原本的時間", y="空氣相對溼度")
    #     return fig

    # @output
    # @render_widget
    # def brightness():
    #     df = user_sheet.get()
    #     fig = px.line(df, x="原本的時間", y="光強度")
    #     return fig

    # @output
    # @render_widget
    # def winddirection():
    #     df = user_sheet.get()
    #     fig = px.line(df, x="原本的時間", y="風向")
    #     return fig

    # @output
    # @render_widget
    # def windspeed():
    #     df = user_sheet.get()
    #     fig = px.line(df, x="原本的時間", y="風速")
    #     return fig

    # @output
    # @render_widget
    # def soilsensor1():
    #     df = user_sheet.get()
    #     fig = make_subplots(rows=3, cols=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤溫度1"]), row=1, col=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤濕度1"]), row=2, col=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤電導度1"]), row=3, col=1)
    #     fig.update_layout(height=600)
    #     return fig

    # @output
    # @render_widget
    # def soilsensor2():
    #     df = user_sheet.get()
    #     fig = make_subplots(rows=3, cols=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤溫度2"]), row=1, col=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤濕度2"]), row=2, col=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤電導度2"]), row=3, col=1)
    #     fig.update_layout(height=600)
    #     return fig

    # @output
    # @render_widget
    # def soilsensor3():
    #     df = user_sheet.get()
    #     fig = make_subplots(rows=3, cols=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤溫度3"]), row=1, col=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤濕度3"]), row=2, col=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤電導度3"]), row=3, col=1)
    #     fig.update_layout(height=600)
    #     return fig

    # @output
    # @render_widget
    # def soilsensor4():
    #     df = user_sheet.get()
    #     fig = make_subplots(rows=3, cols=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤溫度4"]), row=1, col=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤濕度4"]), row=2, col=1)
    #     fig.add_trace(go.Scatter(x=df["原本的時間"], y=df["土壤電導度4"]), row=3, col=1)
    #     fig.update_layout(height=600)
    #     return fig

    # @reactive.Effect
    # def _():
    #     ui.remove_ui(selector=".card:has(.plot)", multiple=True)

    #     user_select_variable = collapse_soil_cols(
    #         user_sheet.get().columns.tolist())

    #     if "氣壓" in user_select_variable:
    #         ui.insert_ui(
    #             panel_box(
    #                 {"class": "plot"},
    #                 ui.h5(
    #                     {"class": "card-title"},
    #                     "氣壓",
    #                 ),
    #                 output_widget(id="pressure")
    #             ),
    #             "#plots"
    #         )

    #     if "氣溫" in user_select_variable:
    #         ui.insert_ui(
    #             panel_box(
    #                 {"class": "plot"},
    #                 ui.h5(
    #                     {"class": "card-title"},
    #                     "氣溫",
    #                 ),
    #                 output_widget(id="temperature")
    #             ),
    #             "#plots"
    #         )

    #     if "空氣相對溼度" in user_select_variable:
    #         ui.insert_ui(
    #             panel_box(
    #                 {"class": "plot"},
    #                 ui.h5(
    #                     {"class": "card-title"},
    #                     "空氣相對溼度",
    #                 ),
    #                 output_widget(id="humidity")
    #             ),
    #             "#plots"
    #         )

    #     if "光強度" in user_select_variable:
    #         ui.insert_ui(
    #             panel_box(
    #                 {"class": "plot"},
    #                 ui.h5(
    #                     {"class": "card-title"},
    #                     "光強度",
    #                 ),
    #                 output_widget(id="brightness")
    #             ),
    #             "#plots"
    #         )

    #     if "風向" in user_select_variable:
    #         ui.insert_ui(
    #             panel_box(
    #                 {"class": "plot"},
    #                 ui.h5(
    #                     {"class": "card-title"},
    #                     "風向",
    #                 ),
    #                 output_widget(id="winddirection")
    #             ),
    #             "#plots"
    #         )

    #     if "風速" in user_select_variable:
    #         ui.insert_ui(
    #             panel_box(
    #                 {"class": "plot"},
    #                 ui.h5(
    #                     {"class": "card-title"},
    #                     "風速",
    #                 ),
    #                 output_widget(id="windspeed")
    #             ),
    #             "#plots"
    #         )

    #     if "土壤感測器1" in user_select_variable:
    #         ui.insert_ui(
    #             panel_box(
    #                 {"class": "plot"},
    #                 ui.h5(
    #                     {"class": "card-title"},
    #                     "土壤感測器1",
    #                 ),
    #                 output_widget(id="soilsensor1")
    #             ),
    #             "#plots"
    #         )

    #     if "土壤感測器2" in user_select_variable:
    #         ui.insert_ui(
    #             panel_box(
    #                 {"class": "plot"},
    #                 ui.h5(
    #                     {"class": "card-title"},
    #                     "土壤感測器2",
    #                 ),
    #                 output_widget(id="soilsensor2")
    #             ),
    #             "#plots"
    #         )

    #     if "土壤感測器3" in user_select_variable:
    #         ui.insert_ui(
    #             panel_box(
    #                 {"class": "plot"},
    #                 ui.h5(
    #                     {"class": "card-title"},
    #                     "土壤感測器3",
    #                 ),
    #                 output_widget(id="soilsensor3")
    #             ),
    #             "#plots"
    #         )

    #     if "土壤感測器4" in user_select_variable:
    #         ui.insert_ui(
    #             panel_box(
    #                 {"class": "plot"},
    #                 ui.h5(
    #                     {"class": "card-title"},
    #                     "土壤感測器4",
    #                 ),
    #                 output_widget(id="soilsensor4")
    #             ),
    #             "#plots"
    #         )

    # @output
    # @render_widget
    # def all_variables_plot():
    #     df = user_sheet.get()
    #     fig = make_subplots()

    #     # df = user_sheet.get()
    #     # columns = df.drop(["時間", "原本的時間"], axis=1).columns.tolist()

    #     # fig = make_subplots(rows=len(columns), cols=1)

    #     # for i, column in enumerate(columns):
    #     #     fig.append_trace(
    #     #         go.Scatter(
    #     #             y=df[column],
    #     #             x=df["原本的時間"],
    #     #             name=column
    #     #         ),
    #     #         row=i + 1,
    #     #         col=1
    #     #     )

    #     # fig.update_layout(
    #     #     height=800,
    #     # )
    #     return fig


app = App(
    ui=UI(),
    server=server,
    static_assets=public_dir,
    debug=False
)
