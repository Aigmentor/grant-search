import json
import logging
import os
import redis

from grant_search.common import get_mode

REDIS_URL = os.environ["REDISCLOUD_URL"]
connection = redis.from_url(REDIS_URL)

INSTANCE_PREFIX = f"REDIS_{get_mode()}"
logging.info(f"Using Redis instance prefix: {INSTANCE_PREFIX}")


def publish(channel: str, data: dict, type: str):
    msg_json = json.dumps(
        {
            "data": data,
            "type": type,
            "retry": None,
        }
    )
    return connection.publish(channel=f"{INSTANCE_PREFIX}:{channel}", message=msg_json)


def subscribe(channel: str):
    pubsub = connection.pubsub()
    pubsub.subscribe(f"{INSTANCE_PREFIX}:{channel}")
    return pubsub
