from pathlib import Path
from shiny import App, Inputs, Outputs, Session, ui, render, reactive
from tomlkit import loads
import asyncio
import pandas as pd
from plotly import express as px
from shinywidgets import output_widget, render_widget
import numpy as np
from collections import defaultdict

root_dir = Path(__file__).parent

public_dir = root_dir / "public"

config = loads((root_dir / "secrets.toml").open().read())

css_path = public_dir / "css" / "style.css"

# sheet

sheet_config = config.get("sheet")

sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_config.get('id')}"


def load_sheet(location: str) -> pd.DataFrame:
    """
    讀取表格
    """
    csv_url = f"{sheet_url}/export?format=csv&gid={sheet_config.get(location)}"

    df = pd.read_csv(csv_url, dtype=str)
    df.replace(["999", "TO", "undefined", "", "NA"], np.nan, inplace=True)

    common_cols = ['氣壓', '氣溫', '空氣相對溼度', '光強度', '風向', '風速']
    soil = ['土壤濕度', '土壤溫度', '土壤電導度']

    if location == "indoor":
        soil_cols = [i + str(j) for j in range(1, 3) for i in soil]
        df = df.assign(**df[common_cols + soil_cols].astype("float64"))
    elif location == "outdoor":
        soil_cols = [i + str(j) for j in range(1, 5) for i in soil]
        rain_cols = ['雨量', 'rain_event', 'rain_totalevent', 'rain_IPH']
        new_cols = common_cols + soil_cols + rain_cols
        df = df.assign(**df[new_cols].astype("float64"))
        new_cols = ['時間'] + new_cols
        df = df[new_cols]

    df['時間'] = pd.to_datetime(df['時間'], format='%Y-%m-%d %H:%M:%S')
    return df


def panel_box(*args, **kwargs):
    return ui.div(
        {"class": "card mb-3 h-100"},
        ui.div(
            {"class": "card-body"},
            *args
        ),
        **kwargs
    )


def spacer():
    """
    元素間空格
    """
    return ui.div({"class": "mt-2 mb-2"})


def data_range_filter_panel():
    return ui.row(
        ui.column(
            6,
            panel_box(
                ui.a(
                    "表單連結",
                    {
                        "href": sheet_url,
                        "target": "_blank"
                    }
                ),
                ui.input_date_range(
                    id="input_date_range",
                    label="測量期間",
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
                ui.input_selectize(
                    id="variable_select",
                    label="變數",
                    choices=[],
                    multiple=True
                ),
                ui.input_action_button(
                    id="btn_filter",
                    label="篩選",
                ),
            ),
        ),
        ui.column(
            6,
            panel_box(
                ui.input_radio_buttons(
                    id="sensors",
                    label="感測器位置",
                    choices={
                        "indoor": "溫室",
                        "outdoor": "室外"
                    },
                    selected="indoor"
                ),
                ui.input_action_button(
                    id="btn_reload_sheet",
                    label="讀取",
                    class_="btn-danger"
                ),
            ),
            class_="h-full"
        ),
        class_="mb-3"
    )

# Part 1: ui


def UI():
    # TODO: 選變數, 單選/多選

    return ui.page_fixed(
        ui.include_css(css_path),
        ui.tags.title("大溪感測器"),
        ui.markdown((root_dir / "introduction.md").open().read()),
        spacer(),
        data_range_filter_panel(),
        panel_box(
            ui.output_data_frame(id="df")
        ),

        ui.layout_sidebar(
            ui.panel_sidebar(
            ),
            ui.panel_main(
                ui.navset_pill(
                    ui.nav(
                        "圖",
                        output_widget(id="ts")
                    )
                ),
            )
        ),
        spacer()
    )

# Part 2: server


def server(input: Inputs, output: Outputs, session: Session):
    sheet = reactive.Value(load_sheet("indoor"))

    @reactive.Effect
    @reactive.event(input.btn_reload_sheet)
    def reload_sheet():
        sheet.set(load_sheet(input.sensors()))

    @reactive.Calc
    def get_date_range():
        m = sheet.get()['時間'].min().date()
        M = sheet.get()['時間'].max().date()
        return m, M

    @reactive.Calc
    def get_variables():
        return sheet.get().columns.drop('時間').tolist()

    @reactive.Effect
    def _():
        m, M = get_date_range()
        ui.update_date_range(
            id="input_date_range",
            start=m,
            end=M,
            min=m,
            max=M,
        )
        variables = get_variables()
        ui.update_selectize(
            id="variable_select",
            choices=variables,
            selected=variables
        )
        

    @output
    @render.data_frame
    @reactive.event(input.btn_filter)
    @reactive.event(input.frequency_select)
    @reactive.event(input.variable_select)
    def df():
        df1 = sheet.get().copy()
        m, M = input.input_date_range()
        mask = ((df1['時間'].dt.date >= m) & (df1['時間'].dt.date <= M))
        df1 = df1.loc[mask]

        if input.frequency_select() == "hour":
            df1 = df1.resample('H', on='時間').mean()
            df1['時間'] = df1.index.strftime('%Y/%m/%d %H:%M')
        elif input.frequency_select() == "day":
            df1 = df1.resample('D', on='時間').mean()
            df1['時間'] = df1.index.strftime('%Y/%m/%d')
        else:
            df1['時間'] = df1['時間'].dt.strftime('%Y/%m/%d %H:%M:%S')
        
        new_cols = ['時間'] + list(input.variable_select())

        return df1[new_cols]

    @output
    @render_widget
    def ts():
        df = sheet.get().copy()
        fig = px.line(df, x="時間", y="氣溫")
        return fig


app = App(
    ui=UI(),
    server=server,
    static_assets=public_dir,
    debug=True
)
