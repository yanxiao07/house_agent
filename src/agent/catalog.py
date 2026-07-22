import json
import os
from decimal import Decimal

import pymysql
from dotenv import load_dotenv

load_dotenv(override=True)

COLUMNS = "id, title, rent_type, rooms, position, area, price, intro, city_name, region_name, community_name, detail_address, head_image, images"


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
