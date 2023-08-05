from shiny import App, Inputs, Outputs, Session, ui, reactive
from shiny.types import NavSetArg
from typing import List
from utils.ui_utils import (
    container, 
    faicon
)
from utils.server_utils import reload_all
from config import (
    root_dir,
    js_path,
    css_path,
    public_dir,
)
from modules.cross_analysis import (
    cross_analysis_ui,
    cross_analysis_server
)
from modules.trend_analysis import (
    trend_analysis_ui,
    trend_analysis_server,
)
from modules.dataframe import (
    dataframe_ui,
    dataframe_server,
)


def introduction_ui():
    return container(
        ui.markdown((root_dir / "introduction.md").open().read()),
        _class="typographic",
    )

# 導覽列


def nav_controls() -> List[NavSetArg]:
    return [
        ui.nav(
            "資料說明",
            introduction_ui(),
            icon=faicon("fa-solid fa-circle-info me-1")
        ),
        ui.nav(
            "變數趨勢圖",
            trend_analysis_ui("trend_analysis"),
            icon=faicon("fa-solid fa-chart-line me-1")
        ),
        ui.nav(
            "交叉分析",
            cross_analysis_ui("cross_analysis"),
            icon=faicon("fa-solid fa-shuffle me-1")
        ),
        ui.nav(
            "資料框",
            dataframe_ui("dataframe"),
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
        ),
        # ui.nav_control(
        #     ui.a(
        #         faicon("fa-brands fa-github me-1"),
        #         "查看原始碼",
        #         href="https://github.com/exkuretrol/daxi-farm-sensor",
        #         target="_blank"
        #     )
        # )
    ]


# Part 1: ui


def ui_():
    return ui.page_navbar(
        *nav_controls(),
        title="智慧農場資料視覺化",
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
    indoor_sheet = reactive.Value()
    outdoor_sheet = reactive.Value()
    reload_all(
        indoor_sheet=indoor_sheet,
        outdoor_sheet=outdoor_sheet
    )

    user_sheet = reactive.Value()

    @reactive.Effect
    @reactive.event(input.btn_reload_sheet)
    def _():
        reload_all(
            indoor_sheet=indoor_sheet,
            outdoor_sheet=outdoor_sheet
        )

    dataframe_server(
        "dataframe",
        indoor_sheet=indoor_sheet,
        outdoor_sheet=outdoor_sheet
    )

    trend_analysis_server(
        "trend_analysis",
        indoor_sheet=indoor_sheet,
        outdoor_sheet=outdoor_sheet,
        user_sheet=user_sheet
    )

    cross_analysis_server(
        "cross_analysis",
        indoor_sheet=indoor_sheet,
        outdoor_sheet=outdoor_sheet
    )


app = App(
    ui=ui_(),
    server=server,
    static_assets=public_dir,
    debug=False
)
