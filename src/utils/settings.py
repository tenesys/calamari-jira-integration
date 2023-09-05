import os
from functools import cache

import boto3

ssm = boto3.client("ssm")

@cache
def get(key: str, default: str|None = None) -> str|None:
    if os.getenv("SETTINGS_STORE") == "ssm_parameters":
        return _get_ssm_parameter(key, default)

    return os.getenv(key.upper(), default)


@cache
def _get_ssm_parameter(name: str, default: str|None) -> str|None:
    try:
        return ssm.get_parameter(Name=name, WithDecryption=True)["Parameter"]["Value"]
    except ssm.exceptions.ParameterNotFound:
        return default
