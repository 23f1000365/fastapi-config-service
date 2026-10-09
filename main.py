import os
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

app = FastAPI()

@app.get("/")
async def home():
    return {"message": "FastAPI config service is running"}

@app.get("/debug-routes")
async def debug_routes():
    return {
        "file": __file__,
        "routes": [route.path for route in app.routes]
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


@app.get("/effective-config")
async def effective_config(request: Request):
    config = DEFAULTS.copy()

    # Layer 2: YAML configuration
    yaml_file = BASE_DIR / "config.development.yaml"
    if yaml_file.exists():
        with open(yaml_file, "r") as file:
            config.update(yaml.safe_load(file) or {})

    # Layer 3: .env file
    load_dotenv(BASE_DIR / ".env", override=False)

    env_values = {
        "APP_PORT": "port",
        "NUM_WORKERS": "workers",
    }

    for env_key, config_key in env_values.items():
        value = os.getenv(env_key)
        if value is not None:
            config[config_key] = value

    # Layer 4: OS environment variables
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            config_key = key[4:].lower()
            if config_key in config:
                config[config_key] = value

    # Layer 5: query parameter overrides
    for value in request.query_params.getlist("set"):
        if "=" not in value:
            continue
        key, raw_value = value.split("=", 1)
        config[key.strip()] = raw_value.strip()

    # Convert types
    for key in ("port", "workers"):
        if key in config:
            config[key] = int(config[key])

    if "debug" in config:
        config["debug"] = str(config["debug"]).lower() in (
            "true", "1", "yes", "on"
        )

    # Never reveal the actual API key
    config["api_key"] = "*****"

    return config
