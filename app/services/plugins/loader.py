import importlib.util
import json
import os
from typing import Any

from app.core.logging import logger


class BasePlugin:
    """Standard base class for AI system plugins.

    Custom plugins must subclass this class.
    """

    def __init__(self, manifest: dict[str, Any]) -> None:
        self.manifest = manifest
        self.name = manifest.get("name")
        self.version = manifest.get("version", "1.0.0")

    def on_load(self) -> None:
        """Triggered when the plugin is first scanned and loaded into memory."""
        pass

    def on_enable(self) -> None:
        """Triggered when the plugin is enabled and active in the system."""
        pass

    def on_disable(self) -> None:
        """Triggered when the plugin is disabled or during clean system shutdown."""
        pass


class PluginLoader:
    """Dynamic scan and loader for plugin extensions in the local filesystem."""

    def __init__(self, plugins_dir: str = "plugins") -> None:
        self.plugins_dir = plugins_dir
        self.loaded_plugins: dict[str, BasePlugin] = {}

    def load_all_plugins(self) -> None:
        """Scans plugins directory, reads manifests, and imports files dynamically."""
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            logger.info("Created empty plugins folder for future extensions", directory=self.plugins_dir)
            return

        for folder_name in os.listdir(self.plugins_dir):
            folder_path = os.path.join(self.plugins_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue

            manifest_path = os.path.join(folder_path, "manifest.json")
            if not os.path.exists(manifest_path):
                continue

            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)

                plugin_name = manifest.get("name")
                entry_point = manifest.get("entry_point", "main.py")
                entry_path = os.path.join(folder_path, entry_point)

                if not os.path.exists(entry_path):
                    logger.warn("Plugin entry point file missing", plugin=plugin_name, path=entry_path)
                    continue

                # Dynamically load the python module
                module_name = f"plugins.{plugin_name.lower()}"
                spec = importlib.util.spec_from_file_location(module_name, entry_path)
                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find subclasses of BasePlugin
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BasePlugin)
                        and attr is not BasePlugin
                    ):
                        plugin_instance = attr(manifest=manifest)
                        plugin_instance.on_load()
                        plugin_instance.on_enable()

                        self.loaded_plugins[plugin_name] = plugin_instance
                        logger.info("Successfully loaded extension plugin", plugin=plugin_name, version=plugin_instance.version)
                        break

            except Exception as e:
                logger.error("Failed to dynamically load plugin folder", folder=folder_name, error=str(e))
