"""
Event Dispatcher — publishes domain events.

No listeners are registered yet. Future modules subscribe here
without touching any router or service that publishes.
"""
import logging
from app.core.events.types import EventType

logger = logging.getLogger(__name__)


class EventDispatcher:
    def publish(self, event_type: EventType, payload: dict) -> None:
        """
        Publish a domain event.
        Currently logs the event. Future: fan-out to registered handlers.
        """
        logger.info(
            "EVENT published",
            extra={"event_type": event_type.value, "payload": payload},
        )
        # TODO: iterate registered async handlers in Sprint 004+


dispatcher = EventDispatcher()

