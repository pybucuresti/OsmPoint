import unittest2
import osm_point


class UserPageTest(unittest2.TestCase):

    def setUp(self):
        self._db = osm_point.db
        self._db.create_all()

    def tearDown(self):
        self._db.drop_all()

    def test_page_renders(self):
        app = osm_point.app.test_client()
        self.assertEqual(app.get('/').status_code, 200)

    def test_point_is_stored(self):
        point = osm_point.Point(46.06, 24.10, "Eau de Web")
        self._db.session.add(point)
        self._db.session.commit()

        points = osm_point.Point.query.all()
        self.assertEquals(len(points), 1)

        point = points[0]
        self.assertEquals(point.latitude, 46.06)
        self.assertEquals(point.longitude, 24.10)
        self.assertEquals(point.name, "Eau de Web")

    def test_save_poi(self):
        app = osm_point.app.test_client()

        response = app.post('/save_poi', data={
            'lat': 46.06, 'lon': 24.10,
            'name': 'bau'})

        self.assertEquals(response.data, 'ok')

        point = osm_point.Point.query.all()[0]
        self.assertEquals(point.latitude, 46.06)
        self.assertEquals(point.longitude, 24.10)
        self.assertEquals(point.name, 'bau')

