from pathlib import Path
from tomlkit import loads

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

sensor_info = config.get("info")