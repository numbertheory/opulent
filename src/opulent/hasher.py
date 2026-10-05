import hashlib

BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def base62_encode(num: int, min_length: int = 8) -> str:
    """Encode an integer into a base62 string with optional minimum length padding."""
    if num == 0:
        return BASE62_ALPHABET[0] * min_length

    chars = []
    base = len(BASE62_ALPHABET)
    while num > 0:
        num, rem = divmod(num, base)
        chars.append(BASE62_ALPHABET[rem])

    chars.reverse()
    result = "".join(chars)
    if len(result) < min_length:
        result = result.rjust(min_length, BASE62_ALPHABET[0])
    return result


def normalize_content(content: str) -> str:
    """Normalize line endings and outer whitespace."""
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.strip()


def compute_content_hash(title: str, format_type: str, content: str) -> str:
    """
    Compute a deterministic SHA-256 hash of the normalized document contents.
    Identical documents with the same title, format, and content produce the exact same hash.
    """
    norm_title = (title or "").strip()
    norm_format = (format_type or "markdown").strip().lower()
    norm_content = normalize_content(content or "")

    payload = f"{norm_format}\x00{norm_title}\x00{norm_content}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def generate_doc_id(content_hash: str, attempt: int = 0) -> str:
    """
    Generate a URL-safe, compact doc-id deterministically from the content hash.
    If an attempt offset is provided (in case of a collision with different content),
    a salted hash is used to generate the next unique doc-id.
    """
    if attempt == 0:
        hash_bytes = bytes.fromhex(content_hash)
    else:
        salt = f"{content_hash}:{attempt}".encode("utf-8")
        salted_hash = hashlib.sha256(salt).hexdigest()
        hash_bytes = bytes.fromhex(salted_hash)

    # Use first 7 bytes (56 bits of entropy) -> ~10 base62 characters
    num = int.from_bytes(hash_bytes[:7], byteorder="big")
    doc_id = base62_encode(num, min_length=8)
    return doc_id[:10]
