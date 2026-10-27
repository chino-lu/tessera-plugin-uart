"""Test shim: load the integration's modules without executing its package __init__
(which needs Home Assistant and voluptuous, not installed in the sandbox)."""

import importlib.util
import os
import sys
import types

PKG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "custom_components", "home_wallet")
PKG_DIR = os.path.abspath(PKG_DIR)

pkg = types.ModuleType("home_wallet")
pkg.__path__ = [PKG_DIR]
sys.modules.setdefault("home_wallet", pkg)


def _load(name: str):
    path = os.path.join(PKG_DIR, name + ".py")
    spec = importlib.util.spec_from_file_location(f"home_wallet.{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[f"home_wallet.{name}"] = module
    spec.loader.exec_module(module)
    return module


for _name in ("const", "models", "tokens", "manager"):
    if f"home_wallet.{_name}" not in sys.modules:
        try:
            _load(_name)
        except ModuleNotFoundError:
            # manager.py imports homeassistant lazily inside async_load; a hard
            # failure here means a real problem, so re-raise.
            raise
