import uuid


def is_valid_uuid(val: str) -> bool:
    """Checks if a string represents a valid UUID4."""
    try:
        uuid.UUID(val, version=4)
        return True
    except ValueError:
        return False
