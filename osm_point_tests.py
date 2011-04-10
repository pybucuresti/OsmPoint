import unittest2
import osm_point

class UserPageTest(unittest2.TestCase):
    def test_page_renders(self):
        app = osm_point.app.test_client()
        self.assertEqual(app.get('/').status_code, 200)
