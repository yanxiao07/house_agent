"""Rental-contract retrieval and deterministic risk analysis.

The module intentionally keeps retrieval local and deterministic: contract text can
contain sensitive identity and payment information, so a useful first-pass warning
should not depend on an external model call. LangChain ``Document`` objects keep the
knowledge base compatible with a future vector-store replacement.
"""

import re
from collections import Counter
from typing import Any

from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langgraph.constants import END, START
from langgraph.graph import MessagesState, StateGraph

KNOWLEDGE_BASE = [
    Document(
        page_content="押金应明确金额、保管方式、退还条件与退还期限。不得以未列明的清洁、折旧或维修项目无限期扣留押金。",
        metadata={"topic": "押金", "source": "租赁合同审查要点"},
    ),
    Document(
        page_content="租金条款应写明金额、支付周期、收款账户、逾期宽限期和涨租规则。模糊的单方调价权会增加承租人风险。",
        metadata={"topic": "租金", "source": "租赁合同审查要点"},
    ),
    Document(
        page_content="违约金应与实际损失相匹配。过高的固定违约金、任意没收已付租金或没有补救期限的解除权需要重点协商。",
        metadata={"topic": "违约与解除", "source": "租赁合同审查要点"},
    ),
    Document(
        page_content="维修责任应区分自然损耗、房屋主体故障和承租人故意或过失造成的损坏，并约定报修与修复时限。",
        metadata={"topic": "维修", "source": "租赁合同审查要点"},
    ),
    Document(
        page_content="房东入户、转租、续租和提前解约应当具有书面通知或双方同意条件，避免单方改变租赁关系。",
        metadata={"topic": "居住权与续租", "source": "租赁合同审查要点"},
    ),
]

RISK_RULES = [
    {
        "category": "押金",
        "keywords": ("押金", "保证金"),
        "high_risk": ("不退", "没收", "概不退还"),
        "suggestion": "明确押金退还时间、可扣除事项和费用凭证，并约定验房交接单。",
    },
    {
        "category": "租金与涨租",
        "keywords": ("租金", "房租", "涨租"),
        "high_risk": ("单方调整", "随时调整", "任意上调"),
        "suggestion": "写明租金金额、支付日、收款账户和续租或涨租的计算规则。",
    },
    {
        "category": "违约与解除",
        "keywords": ("违约金", "解除", "解约"),
        "high_risk": ("全部租金", "双倍", "三倍", "立即解除"),
        "suggestion": "约定合理的补救期和违约金上限，避免与实际损失明显不匹配的责任。",
    },
    {
        "category": "维修责任",
        "keywords": ("维修", "修理", "损坏"),
        "high_risk": ("全部承担", "任何损坏"),
        "suggestion": "区分自然损耗、房屋主体问题和人为损坏，并约定报修响应时限。",
    },
    {
        "category": "居住权与隐私",
        "keywords": ("进入房屋", "入户", "看房"),
        "high_risk": ("随时", "无需通知"),
        "suggestion": "约定除紧急情况外，入户或带看需要提前书面通知并取得同意。",
    },
]


def _sentences(text: str) -> list[str]:
    """Split text into readable clauses while retaining Chinese contract punctuation."""
    return [item.strip() for item in re.split(r"[。；;\n]+", text) if item.strip()]


def retrieve_contract_knowledge(query: str, top_k: int = 3) -> list[dict[str, str]]:
    """Return keyword-ranked knowledge chunks for the supplied contract content."""
    terms = Counter(re.findall(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}", query.lower()))
    ranked: list[tuple[int, Document]] = []
    for document in KNOWLEDGE_BASE:
        score = sum(
            count * document.page_content.lower().count(term)
            for term, count in terms.items()
        )
        ranked.append((score, document))
    return [
        {
            "topic": document.metadata["topic"],
            "content": document.page_content,
            "source": document.metadata["source"],
        }
        for _, document in sorted(ranked, key=lambda item: item[0], reverse=True)[
            :top_k
        ]
    ]


def analyze_contract(text: str) -> dict[str, Any]:
    """Extract high-signal rental risks and attach retrieved review guidance.

    This is an assistive review, not legal advice. Deterministic matching makes the
    response testable and lets a future LLM summarizer consume the same evidence.
    """
    clauses = _sentences(text)
    risks: list[dict[str, str]] = []
    for rule in RISK_RULES:
        matched = [
            clause
            for clause in clauses
            if any(word in clause for word in rule["keywords"])
        ]
        for clause in matched:
            level = (
                "high"
                if any(token in clause for token in rule["high_risk"])
                else "medium"
            )
            risks.append(
                {
                    "category": rule["category"],
                    "level": level,
                    "clause": clause,
                    "suggestion": rule["suggestion"],
                }
            )
    risks.sort(key=lambda item: 0 if item["level"] == "high" else 1)
    return {
        "summary": f"已识别 {len(risks)} 项需要关注的租赁条款。"
        if risks
        else "未识别出预设高风险关键词，仍建议逐条核对金额、期限和签约主体。",
        "risks": risks,
        "knowledge": retrieve_contract_knowledge(text),
        "disclaimer": "本结果用于合同初步审查，不构成法律意见。重要合同请咨询专业人士。",
    }


def _render_analysis(analysis: dict[str, Any]) -> str:
    """Create a compact chat response while preserving structured data in state."""
    lines = [analysis["summary"]]
    for risk in analysis["risks"][:5]:
        lines.append(
            f"- [{risk['level'].upper()}] {risk['category']}：{risk['clause']}\n  建议：{risk['suggestion']}"
        )
    lines.append(analysis["disclaimer"])
    return "\n".join(lines)


class ContractState(MessagesState):
    contract_analysis: dict[str, Any]


def analyze_contract_node(state: ContractState):
    """Analyze the latest user-provided contract text and expose structured evidence."""
    analysis = analyze_contract(str(state["messages"][-1].content))
    return {
        "contract_analysis": analysis,
        "messages": [AIMessage(content=_render_analysis(analysis))],
    }


builder = StateGraph(ContractState)
builder.add_node("analyze_contract", analyze_contract_node)
builder.add_edge(START, "analyze_contract")
builder.add_edge("analyze_contract", END)
contracts_graph = builder.compile()
