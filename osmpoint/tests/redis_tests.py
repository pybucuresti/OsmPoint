# encoding: utf-8
import unittest
import py.path
import logging
import string

log = logging.getLogger(__name__)


class RedisDataTest(unittest.TestCase):

    def setUp(self):
        from osmpoint.testing import redis_for_testing
        tmp = py.path.local.mkdtemp()
        log.info("temp folder %r", tmp)
        self.addCleanup(tmp.remove)
        redis_socket_path = redis_for_testing(tmp, self.addCleanup)
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

    def test_delete(self):
        p_id = self.rdb.put_object('point', None, {'lat': 13, 'lon': 22})
        self.rdb.del_object('point', p_id)
        p = self.rdb.get_object('point', p_id)
        self.assertEqual(p['lat'], None)

    def test_object_ids(self):
        self.assertItemsEqual(self.rdb.object_ids('point'), [])

        p1 = self.rdb.put_object('point', None, {'lat': 13, 'lon': 22})
        self.assertItemsEqual(self.rdb.object_ids('point'), [p1])

        p2 = self.rdb.put_object('point', None, {'lat': 13, 'lon': 22})
        self.assertItemsEqual(self.rdb.object_ids('point'), [p1, p2])

        self.rdb.del_object('point', p1)
        self.assertItemsEqual(self.rdb.object_ids('point'), [p2])

        self.rdb.del_object('point', p2)
        self.assertItemsEqual(self.rdb.object_ids('point'), [])

    def test_unicode(self):
        p_id = self.rdb.put_object('point', None, {'name': u"♣"})
        p = self.rdb.get_object('point', p_id)
        self.assertEqual(p['name'], u"♣")

    def test_empty_fields(self):
        p_id = self.rdb.put_object('point', None, {'name': 'X', 'lat': None})
        p = self.rdb.get_object('point', p_id)
        self.assertEqual(p['lat'], None)
        self.assertEqual(p['lon'], None)
