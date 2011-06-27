import flask
import unittest2
import osm_point

from mock import patch


class UserPageTest(unittest2.TestCase):

    def setUp(self):
        self._db = osm_point.db
        self._db.create_all()

        osm_point.app.config['SECRET_KEY'] = 'my-secret-key'
        @osm_point.app.route('/test_login', methods=['POST'])
        def test_login():
            flask.session['openid'] = flask.request.form['user_id']
            return "ok"

    def tearDown(self):
        self._db.drop_all()

    def test_page_renders(self):
        app = osm_point.app.test_client()
        self.assertEqual(app.get('/').status_code, 200)

    def test_point_is_stored(self):
        point = osm_point.Point(46.06, 24.10, 'Eau de Web', 'my-open-id')
        self._db.session.add(point)
        self._db.session.commit()

        points = osm_point.Point.query.all()
        self.assertEquals(len(points), 1)

        point = points[0]
        self.assertEquals(point.latitude, 46.06)
        self.assertEquals(point.longitude, 24.10)
        self.assertEquals(point.name, 'Eau de Web')
        self.assertEquals(point.user_open_id, 'my-open-id')

    def test_save_poi(self):
        app = osm_point.app.test_client()
        point_data = {'lat': 46.06, 'lon': 24.10, 'name': 'bau'}

        response = app.post('/save_poi', data=dict(point_data))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'],
                         'http://localhost/login')

        app.post('/test_login', data={'user_id': 'my-open-id'})

        response = app.post('/save_poi', data=dict(point_data))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'],
                         'http://localhost/thank_you')

        point = osm_point.Point.query.all()[0]
        self.assertEquals(point.latitude, point_data['lat'])
        self.assertEquals(point.longitude, point_data['lon'])
        self.assertEquals(point.name, point_data['name'])
        self.assertEquals(point.user_open_id, 'my-open-id')

    @patch('osm_point.osm')
    def test_submit_points_to_osm(self, mock_osm):
        app = osm_point.app.test_client()
        p1 = osm_point.Point(46.06, 24.10, 'Eau de Web', 'my-open-id')
        p2 = osm_point.Point(46.07, 24.11, 'blabla', 'my-open-id')
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

    def test_del_point(self):
        point = osm_point.Point(1, 2, 'X', 'Y')
        self._db.session.add(point)
        self._db.session.commit()

        osm_point.del_point(point)

        points = osm_point.Point.query.all()
        self.assertEquals(len(points), 0)

    def test_show_points(self):
        point = osm_point.Point(1, 2, 'location_name', 'user_name')
        self._db.session.add(point)
        self._db.session.commit()

        app = osm_point.app.test_client()

        response = app.get('/points')
        self.assertEquals(response.status_code, 200)
        self.assertIn('location_name', response.data)

        osm_point.del_point(point)

        response = app.get('/points')
        self.assertNotIn('location_name', response.data)

    def test_coords(self):
        app = osm_point.app.test_client()
        app.post('/test_login', data={'user_id': 'my-open-id'})

        point = {'lat': -91, 'lon': 181, 'name': 'wrong'}
        response = app.post('/save_poi', data=dict(point))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/')

        point = {'lat': 45, 'lon': 181, 'name': 'wrong'}
        response = app.post('/save_poi', data=dict(point))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/')

        point = {'lat': -91, 'lon': 20, 'name': 'wrong'}
        response = app.post('/save_poi', data=dict(point))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], 'http://localhost/')

        self.assertEqual(len(osm_point.Point.query.all()), 0)
