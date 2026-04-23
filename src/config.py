import os
import tomllib

_config_path = os.path.join(os.path.dirname(__file__), "..", "config.toml")
with open(_config_path, "rb") as _f:
    _config = tomllib.load(_f)

RAILWAY_GRAPHQL_URL: str = _config["railway"]["graphql_url"]
