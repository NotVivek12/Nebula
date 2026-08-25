from app.services.plugins.loader import BasePlugin
from app.core.logging import logger


class SlackAlertPlugin(BasePlugin):
    """Example plugin implementing lifecycle hooks to dispatch slack messages on events."""

    def on_load(self) -> None:
        logger.info("SlackAlertPlugin: Loaded successfully.")

    def on_enable(self) -> None:
        logger.info("SlackAlertPlugin: Enabled successfully.")

    def on_disable(self) -> None:
        logger.info("SlackAlertPlugin: Disabled successfully.")
