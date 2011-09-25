import unittest
import py.path
import logging
import string

log = logging.getLogger(__name__)

redis_config = string.Template("""\
port 0
unixsocket ${sock}
logfile /dev/null
""")

def set_up_redis(tmp, addCleanup):
    import time
    import subprocess
    redis_socket_path = tmp/'redis.sock'
    p = subprocess.Popen(['redis-server', '-'], stdin=subprocess.PIPE)
    p.stdin.write(redis_config.substitute(sock=redis_socket_path))
    p.stdin.close()
    log.info("started redis with pid %d", p.pid)
    def shut_down_redis():
        log.info("asking redis to shut down")
        p.terminate()
        p.wait()
        log.info("redis has stopped with return code %d", p.returncode)
    addCleanup(shut_down_redis)

    for c in xrange(500):
        if redis_socket_path.check():
            break
        time.sleep(.01)
    else:
        raise RuntimeError("Redis socket did not show up")

    return redis_socket_path


class RedisDataTest(unittest.TestCase):

    def setUp(self):
        tmp = py.path.local.mkdtemp()
        log.info("temp folder %r", tmp)
        self.addCleanup(tmp.remove)
        self.redis_socket_path = set_up_redis(tmp, self.addCleanup)

    def test_add_get_point(self):
        from osmpoint.database import RedisDb
        rdb = RedisDb(str(self.redis_socket_path))
        p_id = rdb.add_point(lat=13, lon=22)
        p = rdb.get_point(p_id)
        self.assertEqual(p['lat'], 13)
        self.assertEqual(p['lon'], 22)

    def test_autoincrement(self):
        from osmpoint.database import RedisDb
        rdb = RedisDb(str(self.redis_socket_path))
        p_id_1 = rdb.add_point(lat=13, lon=22)
        p_id_2 = rdb.add_point(lat=31, lon=14)
        self.assertEqual(p_id_1, 1)
        self.assertEqual(p_id_2, 2)
