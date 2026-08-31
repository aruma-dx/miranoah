from enum import StrEnum


class WorkspaceRole(StrEnum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    PLAYER = "PLAYER"


class TeamRole(StrEnum):
    MANAGER = "MANAGER"
    PLAYER = "PLAYER"


class ProjectRole(StrEnum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class PermissionEffect(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class ProjectStatus(StrEnum):
    PLANNING = "PLANNING"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ARCHIVED = "ARCHIVED"


class ProjectHealth(StrEnum):
    HEALTHY = "HEALTHY"
    ATTENTION = "ATTENTION"
    AT_RISK = "AT_RISK"
    CRITICAL = "CRITICAL"
    BLOCKED = "BLOCKED"


class TaskStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_REVIEW = "WAITING_REVIEW"
    WAITING_INTERNAL = "WAITING_INTERNAL"
    WAITING_EXTERNAL = "WAITING_EXTERNAL"
    BLOCKED = "BLOCKED"
    ON_HOLD = "ON_HOLD"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class TodoStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    SKIPPED = "SKIPPED"


class Priority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DeadlineType(StrEnum):
    EXPLICIT = "EXPLICIT"
    RELATIVE = "RELATIVE"
    CALENDAR_BASED = "CALENDAR_BASED"
    AI_INFERRED = "AI_INFERRED"
    MANUAL = "MANUAL"


class MonitoringPolicy(StrEnum):
    MONITOR_FULL = "MONITOR_FULL"
    MONITOR_TASK_ONLY = "MONITOR_TASK_ONLY"
    MONITOR_ON_MENTION = "MONITOR_ON_MENTION"
    STORE_ONLY = "STORE_ONLY"
    IGNORE = "IGNORE"
