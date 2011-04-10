import unittest2
import osm_point
from mock import patch


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

    @patch("osm_point.osm")
    def test_submit_points_to_osm(self, mock_osm):
        app = osm_point.app.test_client()
        p1 = osm_point.Point(46.06, 24.10, "Eau de Web")
        p2 = osm_point.Point(46.07, 24.11, "blabla")
        self._db.session.commit()
        values = [13, 45]
        mock_osm.NodeCreate.side_effect = lambda *args, **kwargs: {'id': values.pop(0)}

        osm_point.submit_points_to_osm([p1, p2])

        self.assertEquals(p1.osm_id, 13)
        self.assertEquals(p2.osm_id, 45)
        self.assertEquals(mock_osm.ChangesetCreate.call_count, 1)
        self.assertEquals(mock_osm.NodeCreate.call_args_list, [
            (({u'lat': 46.06, u'lon': 24.1, u'tag': {'name': 'Eau de Web'}},),
             {}),
            (({u'lat': 46.07, u'lon': 24.11, u'tag': {'name': 'blabla'}},),
             {})])
        self.assertEquals(mock_osm.ChangesetClose.call_count, 1)
