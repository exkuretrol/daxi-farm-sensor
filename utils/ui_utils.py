from htmltools import Tag, TagChild
from shiny import ui

def panel_box(*args, **kwargs):
    return ui.div(
        {"class": "card mb-3 h-100"},
        ui.div(
            {"class": "card-body d-flex flex-column"},
            *args
        ),
        **kwargs
    )

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