"""Who can speak, chat messages, handoffs and agent actions (ADR-0009)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

__all__ = [
    "AGENT_PROFILES",
    "AgentAction",
    "AgentId",
    "AgentProfile",
    "BuildWebsite",
    "ChatMessage",
    "ChooseName",
    "DeployWebsite",
    "DraftDocuments",
    "LockFacts",
    "MessageKind",
    "MessageRole",
    "OpenView",
    "SuggestedReply",
    "agent_message",
    "handoff_message",
]


class AgentId(str, Enum):
    MANAGER = "manager"
    LAW = "law"
    NAME = "name"
    WEBSITE = "website"
    QA = "qa"
    GUIDE = "guide"
    CAP_TABLE = "cap_table"
    SIGNOFF = "signoff"


class AgentProfile(BaseModel):
    id: AgentId
    display_name: str
    short_name: str
    kind: Literal["llm", "deterministic"]
    icon: str  # lucide icon name
    accent: str  # design token name (ADR-0019)
    routable: bool  # can the Manager hand the chat to it?


def _profile(id: AgentId, display: str, short: str, kind: str, icon: str, routable: bool) -> AgentProfile:
    return AgentProfile(
        id=id,
        display_name=display,
        short_name=short,
        kind=kind,  # type: ignore[arg-type]
        icon=icon,
        accent=f"agent-{id.value.replace('_', '-')}",
        routable=routable,
    )


# Binding values (ADR-0009). The Manager is always present and is not a handover target.
AGENT_PROFILES: dict[AgentId, AgentProfile] = {
    p.id: p
    for p in (
        _profile(AgentId.MANAGER, "Manager", "Manager", "llm", "briefcase", False),
        _profile(AgentId.LAW, "Law Agent", "Law", "llm", "scale", True),
        _profile(AgentId.NAME, "Name Agent", "Names", "llm", "tag", True),
        _profile(AgentId.WEBSITE, "Website Agent", "Website", "llm", "globe", True),
        _profile(AgentId.QA, "QA Agent", "QA", "llm", "shield-check", False),
        _profile(AgentId.GUIDE, "Registration Guide Agent", "Guide", "llm", "list-checks", True),
        _profile(AgentId.CAP_TABLE, "Cap Table Builder", "Cap table", "deterministic", "pie-chart", False),
        _profile(AgentId.SIGNOFF, "Sign-off", "Sign-off", "deterministic", "pen-line", False),
    )
}


class MessageRole(str, Enum):
    FOUNDER = "founder"
    AGENT = "agent"
    SYSTEM = "system"


class MessageKind(str, Enum):
    TEXT = "text"
    HANDOFF = "handoff"
    NOTICE = "notice"
    VALIDATION = "validation"
    NAME_OPTIONS = "name_options"
    DOCUMENTS_READY = "documents_ready"
    CAP_TABLE_READY = "cap_table_ready"
    SITE_PREVIEW = "site_preview"
    QA_REPORT = "qa_report"
    DEPLOY_STATUS = "deploy_status"
    GUIDE_READY = "guide_ready"


class SuggestedReply(BaseModel):
    label: str
    text: str


class ChatMessage(BaseModel):
    id: str | None = None  # set by the repository
    case_id: str | None = None
    seq: int | None = None  # 1, 2, 3 ... per case, set by the repository
    role: MessageRole
    agent: AgentId | None = None  # REQUIRED when role == AGENT; None otherwise
    founder_id: str | None = None  # who typed it, when role == FOUNDER
    kind: MessageKind = MessageKind.TEXT
    content: str  # plain text with light markdown (**bold**, lists, links)
    payload: dict[str, Any] = {}  # kind-specific (ADR-0009 payload table)
    suggested_replies: list[SuggestedReply] = []
    created_at: datetime | None = None

    @model_validator(mode="after")
    def _agent_matches_role(self) -> "ChatMessage":
        if self.role == MessageRole.AGENT and self.agent is None:
            raise ValueError("an agent message must say which agent is speaking")
        if self.role != MessageRole.AGENT and self.agent is not None:
            raise ValueError("only agent messages carry an agent")
        return self


def agent_message(
    agent: AgentId,
    content: str,
    *,
    kind: MessageKind = MessageKind.TEXT,
    payload: dict | None = None,
    suggested_replies: list[SuggestedReply] | None = None,
) -> ChatMessage:
    """A new message spoken by ``agent`` (not yet stored: no id, seq or timestamp)."""
    return ChatMessage(
        role=MessageRole.AGENT,
        agent=agent,
        kind=kind,
        content=content,
        payload=dict(payload or {}),
        suggested_replies=list(suggested_replies or []),
    )


def handoff_message(
    frm: AgentId, to: AgentId, *, direction: Literal["handover", "return"], reason: str
) -> ChatMessage:
    """The fixed-wording handoff message, spoken by ``frm`` with kind ``handoff`` (ADR-0009).

    handover: ``"Manager brought in the Law Agent"``;
    return:   ``"Law Agent handed the conversation back to the Manager"``.
    """
    src = AGENT_PROFILES[frm].display_name
    dst = AGENT_PROFILES[to].display_name
    if direction == "handover":
        content = f"{src} brought in the {dst}"
    elif direction == "return":
        content = f"{src} handed the conversation back to the {dst}"
    else:  # pragma: no cover - guarded by the Literal type
        raise ValueError(f"unknown handoff direction {direction!r}")
    return agent_message(
        frm,
        content,
        kind=MessageKind.HANDOFF,
        payload={"from": frm.value, "to": to.value, "direction": direction, "reason": reason},
    )


# Actions: side effects agents request; CaseService executes them (ADR-0009, ADR-0032).
class LockFacts(BaseModel):
    type: Literal["lock_facts"] = "lock_facts"


class ChooseName(BaseModel):
    type: Literal["choose_name"] = "choose_name"
    name: str
    domain: str | None = None


class DraftDocuments(BaseModel):
    type: Literal["draft_documents"] = "draft_documents"


class BuildWebsite(BaseModel):
    type: Literal["build_website"] = "build_website"
    change_request: str | None = None


class DeployWebsite(BaseModel):
    type: Literal["deploy_website"] = "deploy_website"
    override_qa: bool = False


class OpenView(BaseModel):
    type: Literal["open_view"] = "open_view"
    view: Literal["overview", "names", "legal", "cap_table", "website", "guide", "audit"]


AgentAction = Annotated[
    LockFacts | ChooseName | DraftDocuments | BuildWebsite | DeployWebsite | OpenView,
    Field(discriminator="type"),
]
