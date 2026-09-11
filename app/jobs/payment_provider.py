import time
import random
import uuid
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PaymentFailedError(Exception):
    """Provider explicitly rejected the payment."""
    pass


class PaymentTimeoutError(Exception):
    """Provider timed out."""
    pass


def process_payment(payload: Dict[str, Any], timeout: float = 5.0) -> Dict[str, Any]:
    """
    Simulate a payment provider call.

    - 75% success
    - 15% failure -> raises PaymentFailedError
    - 10% timeout -> raises PaymentTimeoutError
    """
    time.sleep(random.uniform(0.2, 1.2))

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

    if r < 0.9:
        # soft failure
        resp = {
            "status": "failed",
            "error": "provider_rejected",
            "raw": {"accepted": False}
        }
        logger.debug("Provider failure for payload=%s -> %s", payload, resp)
        raise PaymentFailedError(resp)

    logger.debug("Provider timeout for payload=%s", payload)
    raise PaymentTimeoutError("Simulated provider timeout")
