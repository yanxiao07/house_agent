import json
import os
from decimal import Decimal

import pymysql
from dotenv import load_dotenv

load_dotenv(override=True)

COLUMNS = "id, title, rent_type, rooms, position, area, price, intro, city_name, region_name, community_name, detail_address, head_image, images"

# The current data export stores object keys such as ``bitehouse/<file>.jpg``.
# A deployment can point this prefix at its CDN/object-storage domain. The local
# preview images only prevent empty cards when that asset service is unavailable.
FALLBACK_IMAGES = (
    "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1200&q=80",
)


def _connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )


def _number(value):
    return float(value) if isinstance(value, Decimal) else value


def _image_url(value: str | None, listing_id: int | str) -> tuple[str, bool]:
    """Resolve a DB image key to a browser URL and flag non-listing previews."""
    image = str(value or "").strip()
    if image.startswith(("http://", "https://")):
        return image, False
    base_url = os.getenv("PROPERTY_IMAGE_BASE_URL", "").rstrip("/")
    if image and base_url:
        return f"{base_url}/{image.lstrip('/')}", False
    return FALLBACK_IMAGES[int(listing_id) % len(FALLBACK_IMAGES)], True


def as_card(row: dict) -> dict:
    image_key = row.get("head_image")
    if not image_key:
        try:
            image_key = next(iter(json.loads(row.get("images") or "[]")), None)
        except json.JSONDecodeError:
            image_key = None
    image, preview_image = _image_url(image_key, row["id"])
    return {
        "id": str(row["id"]), "title": row["title"], "city": row["city_name"], "district": row["region_name"],
        "location": " · ".join(filter(None, [row["community_name"], row["detail_address"]])),
        "price": _number(row["price"]), "rooms": row["rooms"], "size": f"{_number(row['area']):g} m²",
        "metro": row["rent_type"], "score": 0, "image": image, "preview_image": preview_image,
        "tags": [row["rent_type"], row["position"], row["city_name"]], "intro": row["intro"],
    }


def list_all(limit: int = 24) -> list[dict]:
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(f"SELECT {COLUMNS} FROM house ORDER BY id DESC LIMIT %s", (limit,))
        return [as_card(row) for row in cursor.fetchall()]


def list_for_query(query: str) -> list[dict]:
    if not query.lstrip().upper().startswith("SELECT"):
        return []
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        if not rows or "id" not in rows[0]:
            return []

        # The SQL agent deliberately selects only the columns it needs to reason
        # about a recommendation. Fetch complete records for the presentation API.
        ids = [row["id"] for row in rows]
        placeholders = ", ".join(["%s"] * len(ids))
        cursor.execute(f"SELECT {COLUMNS} FROM house WHERE id IN ({placeholders})", ids)
        records = {row["id"]: row for row in cursor.fetchall()}
    return [as_card(records[house_id]) for house_id in ids if house_id in records]
