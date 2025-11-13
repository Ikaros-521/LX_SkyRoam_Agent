"""Basic connection example.
"""

import redis

r = redis.Redis(
    host='redis-13085.c302.asia-northeast1-1.gce.cloud.redislabs.com',
    port=13085,
    decode_responses=True,
    username="default",
    password="xxx",
)

success = r.set('foo', 'bar')
# True

result = r.get('foo')
print(result)
# >>> bar

