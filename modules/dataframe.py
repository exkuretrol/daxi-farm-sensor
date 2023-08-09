from shiny import module, ui, render, Inputs, Outputs, Session
from shiny.reactive import Value
from utils.ui_utils import container
from utils.server_utils import convert_epoch_to_strftime


@module.ui
def dataframe_ui():
    """
    資料框 ui

    """
    return container(
        ui.navset_tab_card(
            ui.nav(
                "室內",
                ui.output_data_frame(id="indoor_df")
            ),
            ui.nav(
                "室外",
                ui.output_data_frame(id="outdoor_df")
            )
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


@module.server
def dataframe_server(
    input: Inputs,
    output: Outputs,
    Session: Session,
    indoor_sheet: Value,
    outdoor_sheet: Value,
):
    """
    資料框 server
    
    """

    # @output
    # @render.text
    # def sheet_info():
    #     buffer = io.StringIO()
    #     sheet.get().info(buf=buffer)
    #     return buffer.getvalue()

    @output
    @render.data_frame
    def indoor_df():
        return convert_epoch_to_strftime(indoor_sheet.get())

    @output
    @render.data_frame
    def outdoor_df():
        return convert_epoch_to_strftime(outdoor_sheet.get())
