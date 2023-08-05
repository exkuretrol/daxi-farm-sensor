from htmltools import Tag, TagChild
from shiny import ui


def container(*args: TagChild, _class=""):
    """
    容器 class

    """

    return ui.div(
        {"class": "container" + " " + _class},
        *args,
    )


def faicon(_class="") -> Tag:
    """
    fontawesome 圖示

    """

    return ui.tags.i(
        {"class": _class}
    )


def spacer():
    """
    元素間空格
    """
    return ui.div({"class": "mt-2 mb-2"})


def card(*args, **kwargs):
    """
    bootstrap card 樣式

    """
    return ui.div(
        {"class": "mb-3 d-flex card h-100"},
        ui.div(
            {"class": "card-body d-flex flex-column"},
            *args
        ),
        **kwargs
    ),
