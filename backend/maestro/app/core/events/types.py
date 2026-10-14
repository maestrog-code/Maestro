from enum import Enum


class EventType(str, Enum):
    # User events
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"

    # Organization events
    ORGANIZATION_CREATED = "ORGANIZATION_CREATED"

    # Membership events
    MEMBER_INVITED = "MEMBER_INVITED"
    MEMBER_REMOVED = "MEMBER_REMOVED"
    MEMBER_ROLE_CHANGED = "MEMBER_ROLE_CHANGED"

