import numpy as np
import pandas as pd
from config import sheet_config, sheet_url
from shiny.reactive import Value
from shiny import ui

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

def reload_all(indoor_sheet: Value, outdoor_sheet: Value):
    """
    重新讀取所有表格

    """
    with ui.Progress() as p:
        p.set(message="讀取檔案", detail="這需要花一點時間...")
        indoor_sheet.set(load_sheet("indoor"))
        p.inc(amount=.5, detail="讀取中")
        outdoor_sheet.set(load_sheet("outdoor"))
        p.inc(amount=.5)
        p.set(message="完成！", detail="")
    


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

def convert_epoch_to_strftime(df: pd.DataFrame):
    df_ = df.copy()
    df_['時間'] = df['時間'].dt.strftime('%Y/%m/%d %H:%M:%S')
    return df_