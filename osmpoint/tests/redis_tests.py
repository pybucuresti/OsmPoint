import unittest
import py.path
import logging
import string

log = logging.getLogger(__name__)


def set_up_redis(tmp, addCleanup):
    from osmpoint.testing import redis_sock_path
    if redis_sock_path is not None:
        return redis_sock_path

    from osmpoint.database import redis_server_process
    sock_path = tmp/'redis.sock'
    data_path = tmp/'redis.db'
    p = redis_server_process(str(sock_path), str(data_path), persist=False)
    p.__enter__()
    addCleanup(lambda: p.__exit__(None, None, None))
    return sock_path


class RedisDataTest(unittest.TestCase):

    def setUp(self):
        tmp = py.path.local.mkdtemp()
        log.info("temp folder %r", tmp)
        self.addCleanup(tmp.remove)
        redis_socket_path = set_up_redis(tmp, self.addCleanup)
        from osmpoint.database import open_redis_db
        self.rdb = open_redis_db(str(redis_socket_path))

    def test_add_get_point(self):
        p_id = self.rdb.put_object('point', None, {'lat': 13, 'lon': 22})
        p = self.rdb.get_object('point', p_id)
        self.assertEqual(p['lat'], 13)
        self.assertEqual(p['lon'], 22)
        self.assertEqual(p['name'], None)

    def test_autoincrement(self):
        p_id_1 = self.rdb.put_object('point', None, {'lat': 13, 'lon': 22})
        p_id_2 = self.rdb.put_object('point', None, {'lat': 31, 'lon': 14})
        self.assertEqual(p_id_1, 1)
        self.assertEqual(p_id_2, 2)

    def test_update(self):
        p_id = self.rdb.put_object('point', None, {'lat': 13, 'lon': 22})
        self.rdb.put_object('point', p_id, {'lat': 15, 'lon': 44})
        p = self.rdb.get_object('point', p_id)
        self.assertEqual(p['lat'], 15)
        self.assertEqual(p['lon'], 44)

    def test_unknown_field(self):
        data = {'no_such_key': 13}
        self.assertRaises(KeyError, self.rdb.put_object, 'point', None, data)
