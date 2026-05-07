import logging
from typing import Dict, Any

# Use the app's shared RedisClient which:
#  - already handles orjson+LZ4 serialization internally
#  - already falls back to None (not an exception) when Redis is down
# This avoids a second raw connection with no error handling.
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


async def get_revenue_summary(
    property_id: str,
    tenant_id: str,
    month: int = None,
    year: int = None,
) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing caching to improve performance.
    Falls back gracefully to a live calculation when Redis is unavailable.
    Pass month+year for a specific month, omit for all-time total.
    """
    # tenant_id is included in the key to prevent cross-tenant cache collisions
    if month and year:
        cache_key = f"revenue:{tenant_id}:{property_id}:{year}:{month}"
    else:
        cache_key = f"revenue:{tenant_id}:{property_id}"

    cached = await redis_client.get(cache_key)
    if cached:
        return cached

    if month and year:
        from app.services.reservations import calculate_monthly_revenue
        result = await calculate_monthly_revenue(property_id, tenant_id, month, year)
    else:
        from app.services.reservations import calculate_total_revenue
        result = await calculate_total_revenue(property_id, tenant_id)

    await redis_client.set(cache_key, result, ttl=300)

    return result
