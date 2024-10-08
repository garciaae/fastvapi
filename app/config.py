from __future__ import annotations

import os


def get_config(key: str, default: str = '') -> str:
    """
    Retrieves a configuration value from the .env file
    If the key does not exist, it returns the default value

    Args:
        key (str): The key for the configuration value.

    Returns:
        str: The configuration value or the default value if the key does not exist.
    """
    return os.getenv(key, default)