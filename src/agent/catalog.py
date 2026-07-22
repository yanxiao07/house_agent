import json
import os
from decimal import Decimal

import pymysql
from dotenv import load_dotenv

load_dotenv(override=True)

COLUMNS = "id, title, rent_type, rooms, position, area, price, intro, city_name, region_name, community_name, detail_address, head_image, images"


def _text(value, default=""):
    return str(value).strip() if value is not None and str(value).strip() else default


def _number_or(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"], port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"], charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor,
    )


def _number(value):
    return float(value) if isinstance(value, Decimal) else value


def as_card(row: dict) -> dict:
    image = row.get("head_image") if str(row.get("head_image", "")).startswith(("http://", "https://")) else None
    if not image:
        try:
            image = next((item for item in json.loads(row.get("images") or "[]") if str(item).startswith(("http://", "https://"))), None)
        except json.JSONDecodeError:
            image = None
    return {
        "id": str(row["id"]), "title": row["title"], "city": row["city_name"], "district": row["region_name"],
        "location": " · ".join(filter(None, [row["community_name"], row["detail_address"]])),
        "price": _number(row["price"]), "rooms": row["rooms"], "size": f"{_number(row['area']):g} m²",
        "metro": row["rent_type"], "score": 0, "image": image,
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


def _location_ids(cursor, city_name: str, region_name: str) -> tuple[int, int]:
    cursor.execute(
        "SELECT city_id, region_id FROM house WHERE city_name = %s AND region_name = %s LIMIT 1",
        (city_name, region_name),
    )
    location = cursor.fetchone()
    return (location or {}).get("city_id", 0), (location or {}).get("region_id", 0)


def create_listing(payload: dict) -> str:
    title = _text(payload.get("title"))
    if not title:
        raise ValueError("A listing title is required")
    city_name = _text(payload.get("city"), "Unknown")
    region_name = _text(payload.get("district"), "Unknown")
    rooms = _text(payload.get("rooms"), "one")
    with _connection() as connection, connection.cursor() as cursor:
        city_id, region_id = _location_ids(cursor, city_name, region_name)
        cursor.execute(
            """INSERT INTO house (
                user_id, title, rent_type, floor, all_floor, house_type, rooms,
                position, area, price, intro, devices, head_image, images, city_id,
                city_name, region_id, region_name, community_name, detail_address,
                longitude, latitude
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, %s, %s)""",
            (
                1, title[:50], _text(payload.get("rent_type"), "whole_rent"), 1, 1,
                _text(payload.get("house_type"), rooms), rooms,
                _text(payload.get("position"), "south"), _number_or(payload.get("area"), 0),
                _number_or(payload.get("price"), 0), _text(payload.get("intro")),
                _text(payload.get("devices")), _text(payload.get("image")), "[]", city_id,
                city_name[:40], region_id, region_name[:40],
                _text(payload.get("community"), title)[:40], _text(payload.get("address"))[:255],
                _number_or(payload.get("longitude"), 0), _number_or(payload.get("latitude"), 0),
            ),
        )
        connection.commit()
        return str(cursor.lastrowid)


def update_listing(listing_id: str, payload: dict) -> None:
    title = _text(payload.get("title"))
    if not title:
        raise ValueError("A listing title is required")
    city_name = _text(payload.get("city"), "Unknown")
    region_name = _text(payload.get("district"), "Unknown")
    rooms = _text(payload.get("rooms"), "one")
    with _connection() as connection, connection.cursor() as cursor:
        city_id, region_id = _location_ids(cursor, city_name, region_name)
        cursor.execute(
            """UPDATE house SET title = %s, rent_type = %s, house_type = %s, rooms = %s,
                position = %s, area = %s, price = %s, intro = %s, head_image = %s,
                city_id = %s, city_name = %s, region_id = %s, region_name = %s,
                community_name = %s, detail_address = %s
                WHERE id = %s""",
            (
                title[:50], _text(payload.get("rent_type"), "whole_rent"),
                _text(payload.get("house_type"), rooms), rooms,
                _text(payload.get("position"), "south"), _number_or(payload.get("area"), 0),
                _number_or(payload.get("price"), 0), _text(payload.get("intro")),
                _text(payload.get("image")), city_id, city_name[:40], region_id, region_name[:40],
                _text(payload.get("community"), title)[:40], _text(payload.get("address"))[:255],
                int(listing_id),
            ),
        )
        connection.commit()


def delete_listing(listing_id: str) -> None:
    with _connection() as connection, connection.cursor() as cursor:
        cursor.execute("DELETE FROM house WHERE id = %s", (int(listing_id),))
        connection.commit()
