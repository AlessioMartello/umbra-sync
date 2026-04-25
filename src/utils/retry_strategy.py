import logging

import httpx
from groq import RateLimitError, APIConnectionError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    wait_exponential_jitter,
    before_sleep_log,
    retry_if_exception_type,
    retry_if_exception,
)

from utils.logger import get_logger

logger = get_logger(__name__)


def _is_retryable_status(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return False


api_retry_strategy = retry(
    retry=(
        retry_if_exception_type(
            (
                httpx.ConnectError,
                httpx.TimeoutException,
                httpx.ReadError,
            )
        )
        | retry_if_exception(_is_retryable_status)
    ),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)

groq_retry_strategy = retry(
    retry=(
        retry_if_exception_type(
            (
                RateLimitError,
                APIConnectionError,
                APITimeoutError,
            )
        )
    ),
    stop=stop_after_attempt(4),
    wait=wait_exponential_jitter(initial=60, max=600, exp_base=2, jitter=15),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
