from pathlib import Path
from shiny import App, Inputs, Outputs, Session, ui, render, reactive
from tomlkit import loads
# import asyncio
import pandas as pd
from plotly import express as px
from shinywidgets import output_widget, render_widget

root_dir = Path(__file__).parent

config = loads((root_dir / "secrets.toml").open().read())

css_path = root_dir / "public" / "css" / "style.css"


def load_sheet(location: str) -> pd.DataFrame:
    """
    讀取表格
    """
    sheet_config = config.get("sheet")
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_config.get('id')}/export?format=csv&gid={sheet_config.get(location)}"
    df = pd.read_csv(csv_url)
    df['時間'] = pd.to_datetime(df['時間'], format='%Y-%m-%d %H:%M:%S')
    return df


# Part 1: ui
def UI():
    return ui.page_fixed(
        ui.include_css(css_path),
        ui.tags.title("大溪感測器"),
        ui.markdown((root_dir / "introduction.md").open().read()),
        ui.layout_sidebar(
            ui.panel_sidebar(
                ui.div(
                    ui.input_date_range(
                        id="input_date_range",
                        label="測量期間",
                        language="zh-TW",
                    ),
                    # ui.input_action_button(
                    #     id="btn_filter",
                    #     label="篩選"
                    # )
                ),
                ui.div(
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
                        label="重新讀取表格",
                        style="margin-top: 2rem;"
                    ),
                )
            ),
            ui.panel_main(
                ui.navset_pill(
                    ui.nav(
                        "資料框",
                        ui.output_data_frame(id="df")
                    ),
                    ui.nav(
                        "除錯頁面",
                        ui.markdown(
                            f"""
                            **感測器位置**：{ui.output_text("out_sensors", inline=True)}
                            """
                        ),
                    ),
                    ui.nav(
                        "圖",
                        output_widget(id="ts")
                    )
                ),
            )
        )
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

    @output
    @render.text
    def out_sensors():
        return f"{input.sensors()}"

    @output
    @render.data_frame
    # @reactive.event(input.btn_filter)
    def df():
        df1 = sheet.get().copy()
        m, M = input.input_date_range()
        mask = ((df1['時間'].dt.date >= m) & (df1['時間'].dt.date <= M))
        return df1.loc[mask]

    @output
    @render_widget
    def ts():
        df = sheet.get().copy()
        fig = px.line(df, x="時間", y=df.columns,
                      hover_data={"時間": "|%B %d, %Y"})
        return fig


app = App(UI(), server, debug=False)
