from __future__ import annotations
import pickle
from typing import Any
from redis import Redis

from app.config import get_config


def get_cache() -> Client:
    """
    Establishes a connection to the Redis server using the host and port specified in the environment variables.
    If these variables are not set, it defaults to 'localhost' and 6379 respectively.

    Returns:
        Redis: The Redis connection object.
    """
    host = get_config('REDIS_HOST', default='localhost')
    port = int(get_config('REDIS_PORT', default='6379'))

    return Client(
        host=host,
        port=int(port),
    )


class Client:

    def __init__(self, host: str, port: int) -> None:
        self.client = Redis(
            host=host,
            port=int(port),
        )

    def get(self, name: str) -> Any:
        value = self.client.get(name)
        if value:
            value = pickle.loads(value)
        return value

    def set(self, name: str, value: dict) -> None:
        pickled_value = pickle.dumps(value)
        return self.client.set(name, pickled_value)
