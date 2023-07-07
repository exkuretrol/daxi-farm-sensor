from pathlib import Path
from shiny import App, ui, render, reactive
from tomlkit import loads
import pandas as pd

config = loads(open("secrets.toml").read())

def load_sheet() -> pd.DataFrame:
    csv_url = f"https://docs.google.com/spreadsheets/d/{config['sheet']['sheet_id']}/export?format=csv"
    return pd.read_csv(csv_url)

# Part 1: ui
app_ui = ui.page_fluid(
    ui.input_slider(
        id="n",
        label="N",
        min=0,
        max=100,
        value=40
    ),
    ui.output_text_verbatim(id="text")
)

# Part 2: server
def server(input, output, session):
    @output
    @render.text
    def text():
        return f"n*2 is {input.n() * 2}"


app = App(app_ui, server)
