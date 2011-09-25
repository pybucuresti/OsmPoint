import unittest
import subprocess
import py.path
import logging
import string

log = logging.getLogger(__name__)

redis_config = string.Template("""\
port 0
unixsocket ${sock}
logfile /dev/null
""")

class RedisDataTest(unittest.TestCase):

    def setUp(self):
        tmp = py.path.local.mkdtemp()
        log.info("temp folder %r", tmp)
        self.addCleanup(tmp.remove)

        self.redis_socket_path = '%s/redis.sock' % tmp
        p = subprocess.Popen(['redis-server', '-'], stdin=subprocess.PIPE)
        p.stdin.write(redis_config.substitute(sock=self.redis_socket_path))
        p.stdin.close()
        log.info("started redis with pid %d", p.pid)
        def shut_down_redis():
            log.info("asking redis to shut down")
            p.terminate()
            p.wait()
            log.info("redis has stopped with return code %d", p.returncode)
        self.addCleanup(shut_down_redis)

    def test_add_get_point(self):
        from osmpoint.database import RedisDb
        rdb = RedisDb(self.redis_socket_path)
        p_id = rdb.add_point(lat=13, lon=22)
        p = rdb.get_point(p_id)
        self.assertEqual(p['lat'], 13)
        self.assertEqual(p['lon'], 22)
