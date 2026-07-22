"""A replaceable property catalog used by the rental workflow.

The seed inventory keeps local development and the demo UI deterministic. Replace
``search_listings`` with a database repository in production without changing the
LangGraph state contract or the web client.
"""

from collections.abc import Iterable

LISTINGS: tuple[dict[str, object], ...] = (
    {
        "id": "xuhui-anfu-218",
        "title": "衡复风貌区 · 安福路公寓",
        "city": "上海",
        "district": "徐汇",
        "location": "安福路 218 弄",
        "price": 8200,
        "rooms": "1 室 1 厅",
        "size": "58 m²",
        "metro": "步行 6 分钟",
        "score": 96,
        "image": "https://images.unsplash.com/photo-1600210492486-724fe5c67fb0?auto=format&fit=crop&w=920&q=85",
        "tags": ["整租", "近地铁", "朝南"],
    },
    {
        "id": "jingan-daning-288",
        "title": "大宁国际 · 高区两居",
        "city": "上海",
        "district": "静安",
        "location": "广中西路 288 弄",
        "price": 9300,
        "rooms": "2 室 1 厅",
        "size": "73 m²",
        "metro": "步行 8 分钟",
        "score": 92,
        "image": "https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=920&q=85",
        "tags": ["电梯", "可做饭", "采光好"],
    },
    {
        "id": "changning-gubei-96",
        "title": "古北新城 · 品质一居",
        "city": "上海",
        "district": "长宁",
        "location": "荣华东道 96 弄",
        "price": 7600,
        "rooms": "1 室 1 厅",
        "size": "52 m²",
        "metro": "步行 9 分钟",
        "score": 89,
        "image": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=920&q=85",
        "tags": ["独立阳台", "有车位", "精装"],
    },
    {
        "id": "pudong-qiantan-255",
        "title": "前滩 · 江景次新房",
        "city": "上海",
        "district": "浦东",
        "location": "东育路 255 弄",
        "price": 9800,
        "rooms": "1 室 1 厅",
        "size": "61 m²",
        "metro": "步行 5 分钟",
        "score": 87,
        "image": "https://images.unsplash.com/photo-1600573472591-ee6b68d14c68?auto=format&fit=crop&w=920&q=85",
        "tags": ["新房源", "近商圈", "智能门锁"],
    },
)


def search_listings(
    *,
    city: str | None = None,
    districts: Iterable[str] = (),
    budget_min: int | None = None,
    budget_max: int | None = None,
    keyword: str = "",
) -> list[dict[str, object]]:
    """Return catalog entries that satisfy the normalized search criteria."""
    requested_districts = {district for district in districts if district}
    keyword = keyword.strip().lower()
    matches: list[dict[str, object]] = []
    for listing in LISTINGS:
        price = int(listing["price"])
        searchable = " ".join(
            str(listing[field]) for field in ("title", "district", "location", "city")
        ).lower()
        if city and listing["city"] != city:
            continue
        if requested_districts and listing["district"] not in requested_districts:
            continue
        if budget_min is not None and price < budget_min:
            continue
        if budget_max is not None and price > budget_max:
            continue
        if keyword and keyword not in searchable:
            continue
        matches.append(dict(listing))
    return sorted(matches, key=lambda listing: int(listing["score"]), reverse=True)
