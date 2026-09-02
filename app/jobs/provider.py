import asyncio
import random
import uuid
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    pass


async def process_payment(payload: Dict[str, Any], timeout: float = 5.0) -> Dict[str, Any]:
    """
    Simulate a payment provider call.

    Behavior:
    - small random delay to simulate network/API latency
    - 75% chance of success
    - 15% chance of a soft failure
    - 10% chance of timeout (raise asyncio.TimeoutError)

    Returns a dict with provider transaction reference and raw response.
    """
    # simulate network latency
    await asyncio.sleep(random.uniform(0.2, 1.2))

    r = random.random()
    if r < 0.75:
        # success
        provider_ref = str(uuid.uuid4())
        resp = {
            "status": "success",
            "provider_txn_id": provider_ref,
            "raw": {"accepted": True}
        }
        logger.debug("Provider success for payload=%s -> %s", payload, resp)
        return resp
    elif r < 0.9:
        # soft failure
        resp = {
            "status": "failed",
            "error": "provider_rejected",
            "raw": {"accepted": False}
        }
        logger.debug("Provider failure for payload=%s -> %s", payload, resp)
        return resp
    else:
        # timeout
        logger.debug("Provider timeout for payload=%s", payload)
        raise asyncio.TimeoutError("simulated provider timeout")
