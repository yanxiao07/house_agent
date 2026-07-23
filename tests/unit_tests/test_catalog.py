from agent.catalog import FALLBACK_IMAGES, as_card


def _listing_row(**overrides):
    """Build the smallest database-shaped row required by the card mapper."""
    row = {
        "id": 11,
        "title": "Sample apartment",
        "rent_type": "whole",
        "rooms": "two",
        "position": "south",
        "area": 72,
        "price": 3200,
        "intro": "Light-filled apartment",
        "city_name": "Yinchuan",
        "region_name": "Jinfeng",
        "community_name": "Sample community",
        "detail_address": "Building 1",
        "head_image": "bitehouse/cover.jpg",
        "images": "[]",
    }
    row.update(overrides)
    return row


def test_card_uses_configured_property_image_base_url(monkeypatch) -> None:
    """Relative image keys must become browser-accessible CDN URLs."""
    monkeypatch.setenv("PROPERTY_IMAGE_BASE_URL", "https://assets.example.com/")

    card = as_card(_listing_row())

    assert card["image"] == "https://assets.example.com/bitehouse/cover.jpg"
    assert card["preview_image"] is False


def test_card_uses_original_absolute_image_url(monkeypatch) -> None:
    """Already-resolved image URLs should not be rewritten by deployment config."""
    monkeypatch.setenv("PROPERTY_IMAGE_BASE_URL", "https://assets.example.com")

    card = as_card(_listing_row(head_image="https://cdn.example.com/cover.jpg"))

    assert card["image"] == "https://cdn.example.com/cover.jpg"
    assert card["preview_image"] is False


def test_card_marks_fallback_photo_when_asset_service_is_unconfigured(monkeypatch) -> None:
    """An unavailable object-store mapping must not leave the listing card blank."""
    monkeypatch.delenv("PROPERTY_IMAGE_BASE_URL", raising=False)

    card = as_card(_listing_row(id=12, head_image=None, images='["bitehouse/gallery.jpg"]'))

    assert card["image"] == FALLBACK_IMAGES[12 % len(FALLBACK_IMAGES)]
    assert card["preview_image"] is True
