def chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> list[str]:
    """Splits a document text content into overlapping text chunks."""
    if not text:
        return []

    # Clean spacing
    clean_text = " ".join(text.split())
    chunks = []
    start = 0
    text_length = len(clean_text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = clean_text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start += chunk_size - chunk_overlap
        # Avoid infinite loop scenarios if overlap is larger than chunk size
        if chunk_size <= chunk_overlap:
            start += chunk_size

    return chunks
