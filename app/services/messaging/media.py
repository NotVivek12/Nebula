import os

import httpx

from app.core.logging import logger


class MediaDownloadService:
    """Service class executing download actions for incoming WhatsApp media messages."""

    def __init__(self, access_token: str) -> None:
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def download_media(self, media_id: str, save_dir: str = "storage/media") -> str | None:
        """Downloads a binary media file from Meta using its media ID, saving it locally.

        Returns:
            The resolved local file path or None if the download failed.
        """
        detail_url = f"https://graph.facebook.com/v20.0/{media_id}"

        async with httpx.AsyncClient() as client:
            try:
                # 1. Fetch download URL and metadata
                response = await client.get(detail_url, headers=self.headers)
                if response.status_code >= 400:
                    logger.error(
                        "Failed to retrieve media metadata from Meta",
                        media_id=media_id,
                        status_code=response.status_code,
                    )
                    return None

                media_meta = response.json()
                download_url = media_meta.get("url")
                mime_type = media_meta.get("mime_type", "application/octet-stream")

                if not download_url:
                    logger.error("Meta media metadata missing download URL", media_id=media_id)
                    return None

                # 2. Download binary payload
                file_response = await client.get(download_url, headers=self.headers)
                if file_response.status_code >= 400:
                    logger.error(
                        "Failed to stream media binary payload",
                        media_id=media_id,
                        status_code=file_response.status_code,
                    )
                    return None

                # 3. Save to storage
                os.makedirs(save_dir, exist_ok=True)
                ext = mime_type.split("/")[-1] if "/" in mime_type else "bin"
                # Strip additional encoding tokens (e.g. video/mp4; codecs="avc1...")
                ext = ext.split(";")[0].strip()

                filename = f"{media_id}.{ext}"
                filepath = os.path.join(save_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(file_response.content)

                logger.info(
                    "WhatsApp media downloaded and saved locally",
                    media_id=media_id,
                    filepath=filepath,
                )
                return filepath
            except Exception as e:
                logger.error(
                    "Exception during Meta media download process",
                    media_id=media_id,
                    error=str(e),
                )
                return None
