import redis, json

conn = redis.Redis(host='redis', port=6379, db=1)

def set_cache(key,value):
    write = json.dumps(value)
    conn.set(key,write)
    return True

def get_cache(key):
    read = conn.get(key)
    cache = {}
    if read:
        cache = json.loads(read)
    return cache