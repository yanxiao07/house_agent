from langgraph.graph import MessagesState


class RecommendState(MessagesState):
    user_preferences: dict
    city: str
    budget_min: float
    budget_max: float
    district: str
    room_type: str
    orientation: str
    room_count: int
    others: str


def get_recommend_info(state: dict) -> str:
    return """提取的租房筛选条件如下：
- 城市: {city}
- 区域: {district}
- 预算: {budget_min} - {budget_max} 元/月
- 房屋类型: {room_type}
- 朝向: {orientation}
- 特殊要求: {others}
- 推荐数量: {room_count}
未指定的条件请放宽处理。""".format(
        city=state.get("city", "未指定"),
        district=state.get("district", "未指定"),
        budget_min=state.get("budget_min", "未指定"),
        budget_max=state.get("budget_max", "未指定"),
        room_type=state.get("room_type", "未指定"),
        orientation=state.get("orientation", "未指定"),
        others=state.get("others", "无"),
        room_count=state.get("room_count", 5),
    )
