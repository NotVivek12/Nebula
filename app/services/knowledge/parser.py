import csv
import io
import re

import httpx

from app.core.logging import logger


async def parse_document(file_content: bytes, file_type: str) -> str:
    """Parses binary and text file contents to extract clean readable text."""
    file_type_clean = file_type.lower().strip(".")

    if file_type_clean == "txt" or file_type_clean == "md":
        return file_content.decode("utf-8", errors="ignore")

    elif file_type_clean == "csv":
        # Parse CSV lines and format as text strings
        text_stream = io.StringIO(file_content.decode("utf-8", errors="ignore"))
        reader = csv.reader(text_stream)
        rows = []
        for row in reader:
            rows.append(" | ".join(row))
        return "\n".join(rows)

    elif file_type_clean == "pdf":
        # Fallback PDF text parser extracting plain ASCII characters
        logger.info("Parsing PDF content via fallback reader")
        raw_text = file_content.decode("ascii", errors="ignore")
        # Extract text blocks
        blocks = re.findall(r"\((.*?)\)\s*TJ", raw_text)
        if not blocks:
            # Fallback to general text extraction
            blocks = re.findall(r"[\x20-\x7E]+", raw_text)
        text = " ".join(blocks)
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned if len(cleaned) > 20 else "Fallback PDF extracted content text placeholder."

    elif file_type_clean == "docx":
        # Fallback DOCX text parser extracting simple raw paragraphs from XML zip contents
        import zipfile
        logger.info("Parsing DOCX content via fallback XML reader")
        try:
            zip_stream = io.BytesIO(file_content)
            with zipfile.ZipFile(zip_stream) as docx_zip:
                xml_content = docx_zip.read("word/document.xml").decode("utf-8", errors="ignore")
                # Parse paragraph tags: <w:t>...</w:t>
                text_blocks = re.findall(r"<w:t.*?>(.*?)</w:t>", xml_content)
                return "\n".join(text_blocks)
        except Exception as e:
            logger.warn("DOCX zip fallback parsing failed, using general extraction", error=str(e))
            return file_content.decode("ascii", errors="ignore")

    else:
        # Fallback for unrecognized formats
        return file_content.decode("utf-8", errors="ignore")


async def parse_website(url: str) -> str:
    """Scrapes raw visible text body from a website URL, stripping HTML tags. (SSRF-protected)"""
    from app.utils.ssrf import validate_url
    
    validated_url = validate_url(url)
    
    logger.info("Scraping website content", url=validated_url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    async with httpx.AsyncClient(follow_redirects=False) as client:
        response = await client.get(validated_url, headers=headers, timeout=15.0)
        response.raise_for_status()
        html = response.text

        # Strip scripts and styling tags
        html_clean = re.sub(r"<(script|style).*?>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)

        # Strip html tags
        text = re.sub(r"<[^>]+>", " ", html_clean)

        # Clean spacing
        text_clean = re.sub(r"\s+", " ", text).strip()
        return text_clean
