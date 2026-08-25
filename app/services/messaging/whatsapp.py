from typing import Any

import httpx

from app.core.logging import logger
from app.services.messaging.base import BaseMessagingProvider


class WhatsAppMessagingProvider(BaseMessagingProvider):
    """WhatsApp Cloud API implementation of the messaging provider contract."""

    def __init__(self, phone_number_id: str, access_token: str) -> None:
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.base_url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"

    async def _send_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Performs async HTTP post requests to Meta API."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, json=payload, headers=headers)
                response_data = response.json()

                if response.status_code >= 400:
                    logger.error(
                        "WhatsApp API call returned error status",
                        status_code=response.status_code,
                        response=response_data,
                    )
                    response.raise_for_status()

                return response_data  # type: ignore
            except httpx.HTTPError as e:
                logger.error("HTTP request to Meta WhatsApp API failed", error=str(e))
                raise

    async def send_text(self, to: str, text: str, **kwargs: Any) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
        return await self._send_payload(payload)

    async def send_image(
        self, to: str, image_url: str, caption: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "image",
            "image": {"link": image_url},
        }
        if caption:
            payload["image"]["caption"] = caption  # type: ignore
        return await self._send_payload(payload)

    async def send_document(
        self, to: str, document_url: str, filename: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "document",
            "document": {"link": document_url},
        }
        if filename:
            payload["document"]["filename"] = filename  # type: ignore
        return await self._send_payload(payload)

    async def send_interactive_buttons(
        self, to: str, body_text: str, buttons: list[dict[str, str]], **kwargs: Any
    ) -> dict[str, Any]:
        formatted_buttons = []
        for btn in buttons:
            formatted_buttons.append(
                {
                    "type": "reply",
                    "reply": {"id": btn.get("id", ""), "title": btn.get("title", "")},
                }
            )

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body_text},
                "action": {"buttons": formatted_buttons},
            },
        }
        return await self._send_payload(payload)

    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str,
        components: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }
        if components:
            payload["template"]["components"] = components  # type: ignore
        return await self._send_payload(payload)
