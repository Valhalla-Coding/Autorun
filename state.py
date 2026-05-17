"""
AutoRun v2 - Shared Application State

Single source of truth for mutable runtime state accessed by all route modules.
"""

from pathlib import Path
from typing import Optional
import config
import logging

CONFIG_PATH = Path("autorun.yaml")
current_config: Optional[config.AutoRunConfig] = None

logger = logging.getLogger('autorun')


class AutoRunException(Exception):
    pass


def find_service(service_name: str) -> config.ServiceConfig:
    for svc in current_config.services:
        if svc.name == service_name:
            return svc
    raise AutoRunException(f"Service '{service_name}' not found")


def reload_config():
    global current_config
    current_config = config.load_config(CONFIG_PATH)
    logger.info("Configuration reloaded")
