from opulent.hasher import (
    base62_encode,
    compute_content_hash,
    generate_doc_id,
    normalize_content,
)


def test_base62_encode():
    assert base62_encode(0) == "00000000"
    assert len(base62_encode(123456789, min_length=8)) >= 8
    # Test reversibility character set
    encoded = base62_encode(999999999)
    assert all(c.isalnum() for c in encoded)


def test_normalize_content():
    text_windows = "Hello World\r\nLine 2\r\n"
    text_unix = "Hello World\nLine 2\n"
    assert normalize_content(text_windows) == "Hello World\nLine 2"
    assert normalize_content(text_unix) == "Hello World\nLine 2"


def test_compute_content_hash_deterministic():
    hash1 = compute_content_hash("My Doc", "markdown", "Some content here")
    hash2 = compute_content_hash("My Doc", "markdown", "Some content here")
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex length


def test_compute_content_hash_whitespace_insensitivity():
    # Outer whitespace or carriage return differences should produce identical hash
    hash1 = compute_content_hash("Doc", "markdown", "Content\r\n")
    hash2 = compute_content_hash("Doc", "markdown", "  Content\n\n  ")
    assert hash1 == hash2


def test_compute_content_hash_differs_on_content_change():
    hash1 = compute_content_hash("Doc", "markdown", "Content 1")
    hash2 = compute_content_hash("Doc", "markdown", "Content 2")
    assert hash1 != hash2


def test_generate_doc_id():
    h = compute_content_hash("Doc", "python", "print('hello')")
    id1 = generate_doc_id(h, attempt=0)
    id2 = generate_doc_id(h, attempt=0)

    assert id1 == id2
    assert 8 <= len(id1) <= 10
    assert id1.isalnum()

    # Attempt > 0 produces an alternative unique doc_id
    id_alt = generate_doc_id(h, attempt=1)
    assert id_alt != id1
    assert id_alt.isalnum()
