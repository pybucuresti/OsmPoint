import unittest
import flask
from osmpoint import database

class DataTest(unittest.TestCase):

    def setUp(self):
        from page_tests import _app_for_testing
        self.app = _app_for_testing(self.addCleanup)
        self.db = database.db
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        self.addCleanup(self._ctx.pop)

    def tearDown(self):
        self.db.session.remove()

    def test_homepage_points(self):
        database.add_point(13, 22, 'zebar', '', 'bar', 'contrib')
        from osmpoint.frontend import points_for_homepage
        for p in points_for_homepage():
            if p['name'] == 'zebar':
                break
        else:
            self.fail('point "zebar" not found')
        self.assertEqual(p['latitude'], 13)
        self.assertEqual(p['longitude'], 22)
