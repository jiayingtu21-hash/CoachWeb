"""
Agent 服务 - Mock 实现
未来接 LLM 时只需替换 process_message() 的内部实现
"""
from typing import Optional
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func
from db.models import Session, Action, TrainingRun


class AgentResponse:
    """Agent 标准返回"""
    def __init__(self, content: str, tool_calls: Optional[list] = None):
        self.content = content
        self.tool_calls = tool_calls or []


def process_message(db: DBSession, user_message: str, conversation_history: list[dict]) -> AgentResponse:
    """
    处理用户消息，返回 Agent 回复。

    *** 未来接 LangGraph 时，只需替换这个函数的内部实现 ***

    Args:
        db: 数据库 session
        user_message: 用户消息
        conversation_history: 历史消息 [{"role": "...", "content": "..."}]

    Returns:
        AgentResponse(content, tool_calls)
    """
    msg = user_message.lower().strip()

    # Intent 1: 数据概览
    if _match(msg, ["data", "数据", "how much", "how many", "sessions", "多少", "总数", "overview", "summary"]):
        return _data_summary(db)

    # Intent 2: 训练/模型
    if _match(msg, ["model", "模型", "train", "训练", "accuracy", "准确", "best", "最好", "compare", "对比", "performance"]):
        return _training_stats(db)

    # Intent 3: 质量分布
    if _match(msg, ["quality", "质量", "distribution", "分布", "good bad", "breakdown", "标注"]):
        return _quality_breakdown(db)

    # Intent 4: 教练建议
    if _match(msg, ["improve", "提高", "suggest", "建议", "advice", "tips", "help me", "帮我", "怎么", "如何"]):
        return _coaching_suggestion(db)

    # Intent 5: 帮助
    if _match(msg, ["help", "帮助", "hello", "hi", "你好", "what can", "能做什么", "功能"]):
        return _help()

    # 兜底
    return _fallback(user_message)


def _match(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def _data_summary(db: DBSession) -> AgentResponse:
    session_count = db.query(func.count(Session.id)).scalar() or 0
    action_count = db.query(func.count(Action.id)).filter(Action.is_deleted == False).scalar() or 0
    good = db.query(func.count(Action.id)).filter(Action.is_deleted == False, Action.manual_quality == "good").scalar() or 0
    bad = db.query(func.count(Action.id)).filter(Action.is_deleted == False, Action.manual_quality == "bad").scalar() or 0
    unlabeled = action_count - good - bad

    content = (
        f"📊 **Data Summary**\n\n"
        f"| Metric | Count |\n|--------|-------|\n"
        f"| Sessions | {session_count} |\n"
        f"| Total Actions | {action_count} |\n"
        f"| Good | {good} |\n"
        f"| Bad | {bad} |\n"
        f"| Unlabeled | {unlabeled} |\n"
    )

    if action_count > 0:
        content += f"\nGood rate: **{good/(good+bad)*100:.0f}%**" if (good + bad) > 0 else ""

    return AgentResponse(
        content=content,
        tool_calls=[{"tool": "query_data_summary", "result": {
            "sessions": session_count, "actions": action_count, "good": good, "bad": bad
        }}],
    )


def _training_stats(db: DBSession) -> AgentResponse:
    runs = (
        db.query(TrainingRun)
        .filter(TrainingRun.status == "completed")
        .order_by(TrainingRun.accuracy.desc())
        .limit(5)
        .all()
    )

    if not runs:
        return AgentResponse(content="No training runs found yet. Go to the **🤖 Train** page to train your first model!")

    best = runs[0]
    content = (
        f"🏆 **Training Results**\n\n"
        f"Best model: **{best.model_type}** with **{best.accuracy:.1%}** accuracy\n\n"
        f"| # | Model | Accuracy | F1 | Samples |\n"
        f"|---|-------|----------|----|---------|\n"
    )
    for i, r in enumerate(runs, 1):
        content += f"| {i} | {r.model_type} | {r.accuracy:.1%} | {r.f1_score:.1%} | {r.sample_count} |\n"

    return AgentResponse(
        content=content,
        tool_calls=[{"tool": "query_training_runs", "result": {
            "count": len(runs), "best_accuracy": best.accuracy, "best_model": best.model_type
        }}],
    )


def _quality_breakdown(db: DBSession) -> AgentResponse:
    sessions = db.query(Session).all()
    if not sessions:
        return AgentResponse(content="No sessions found. Upload some data first!")

    content = (
        f"📋 **Quality Breakdown**\n\n"
        f"| Session | Good | Bad | Unlabeled | Total |\n"
        f"|---------|------|-----|-----------|-------|\n"
    )
    total_g, total_b, total_u = 0, 0, 0
    for s in sessions:
        g, b, u = s.good_count or 0, s.bad_count or 0, s.unlabeled_count or 0
        total_g += g
        total_b += b
        total_u += u
        content += f"| {s.name} | {g} | {b} | {u} | {g+b+u} |\n"

    content += f"| **Total** | **{total_g}** | **{total_b}** | **{total_u}** | **{total_g+total_b+total_u}** |\n"

    return AgentResponse(
        content=content,
        tool_calls=[{"tool": "query_quality_breakdown", "result": {
            "sessions": len(sessions), "good": total_g, "bad": total_b
        }}],
    )


def _coaching_suggestion(db: DBSession) -> AgentResponse:
    good = db.query(func.count(Action.id)).filter(Action.is_deleted == False, Action.manual_quality == "good").scalar() or 0
    bad = db.query(func.count(Action.id)).filter(Action.is_deleted == False, Action.manual_quality == "bad").scalar() or 0

    if good + bad == 0:
        return AgentResponse(content="I need some labeled data to give advice. Upload and label your sessions first!")

    ratio = good / (good + bad)

    if ratio >= 0.8:
        advice = "Your technique looks excellent! Focus on consistency and try increasing practice difficulty."
    elif ratio >= 0.5:
        advice = "Good progress! Review your bad swings to identify patterns. Try recording more sessions for better analysis."
    else:
        advice = "Keep practicing! Focus on fundamentals. Try shorter, focused sessions and review each action carefully."

    content = (
        f"🎾 **Coaching Advice**\n\n"
        f"Based on your data — Good: {good}, Bad: {bad} (good rate: {ratio:.0%})\n\n"
        f"**{advice}**\n\n"
        f"_In the future, I will analyze your IMU feature patterns to give more specific technique advice._"
    )

    return AgentResponse(
        content=content,
        tool_calls=[{"tool": "coaching_analysis", "result": {"good": good, "bad": bad, "ratio": round(ratio, 2)}}],
    )


def _help() -> AgentResponse:
    content = (
        "👋 Hello! I'm your **Tennis Coach AI Assistant**.\n\n"
        "Here's what I can help with:\n\n"
        "| Command | Example |\n|---------|--------|\n"
        "| 📊 Data summary | \"How much data do I have?\" |\n"
        "| 🏆 Training results | \"What was my best model?\" |\n"
        "| 📋 Quality breakdown | \"Show quality distribution\" |\n"
        "| 🎾 Coaching advice | \"How can I improve?\" |\n\n"
        "_I'm currently in demo mode. Soon I'll be powered by a full LLM agent "
        "with deep analytics capabilities._"
    )
    return AgentResponse(content=content)


def _fallback(user_message: str) -> AgentResponse:
    content = (
        f"I'm not sure how to handle that yet.\n\n"
        f"Try asking me about:\n"
        f"- 📊 Data summary\n"
        f"- 🏆 Training results\n"
        f"- 📋 Quality distribution\n"
        f"- 🎾 Coaching suggestions\n\n"
        f"Type **help** to see all my capabilities."
    )
    return AgentResponse(content=content)
