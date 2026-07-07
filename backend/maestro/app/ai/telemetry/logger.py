import logging
from typing import Optional, Dict, Any
from uuid import UUID

logger = logging.getLogger("ai_telemetry")

class AITelemetryLogger:
    @staticmethod
    def log_execution(
        request_id: str,
        organization_id: UUID,
        conversation_id: UUID,
        agent: str,
        provider: str,
        model: str,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        estimated_cost: float = 0.0,
        cache_hit: bool = False,
        tool_calls: int = 0,
        failures: int = 0,
        retries: int = 0,
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Logs AI execution metrics for observability.
        These logs can later be aggregated into a time-series DB or analytics dashboard.
        """
        payload = {
            "event": "AI_EXECUTION",
            "request_id": request_id,
            "organization_id": str(organization_id),
            "conversation_id": str(conversation_id),
            "agent": agent,
            "provider": provider,
            "model": model,
            "latency_ms": latency_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": estimated_cost,
            "cache_hit": cache_hit,
            "tool_calls": tool_calls,
            "failures": failures,
            "retries": retries
        }
        if extra:
            payload.update(extra)
        
        logger.info(str(payload))

telemetry = AITelemetryLogger()
