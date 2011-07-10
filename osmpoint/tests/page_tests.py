import flask
import unittest2
import osm_point
from osmpoint import database
import py

from mock import patch

class SetUpTests(unittest2.TestCase):

    def setUp(self):
        self._tmp_dir = py.path.local.mkdtemp()
        self._tmp_dir.join('secret').write('my-secret-key')
        self.addCleanup(self._tmp_dir.remove)
        self.app = osm_point.create_app(str(self._tmp_dir))
        self.db = database.db
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        self.addCleanup(self._ctx.pop)

        @self.app.route('/test_login', methods=['POST'])
        def test_login():
            flask.session['openid'] = flask.request.form['user_id']
            return "ok"

    def tearDown(self):
        self.db.session.remove()

    def add_point(self, *args, **kwargs):
        point = database.Point(*args, **kwargs)
        self.db.session.add(point)
        self.db.session.commit()
        return point

    def get_all_points(self):
        return database.Point.query.all()

    def create_url(self, point_id):
        return '/points/' + str(point_id)

class SavePointTest(SetUpTests):

    def test_save_poi(self):
        client = self.app.test_client()
        point_data = {'lat': 46.06, 'lon': 24.10, 'name': 'bau',
                      'url': 'none', 'amenity': 'bar'}

        response = client.post('/save_poi', data=dict(point_data))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'],
                         'http://localhost/login')

        client.post('/test_login', data={'user_id': 'my-open-id'})

        response = client.post('/save_poi', data=dict(point_data))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'],
                         'http://localhost/thank_you')

        point = self.get_all_points()[0]
        self.assertEquals(point.latitude, point_data['lat'])
        self.assertEquals(point.longitude, point_data['lon'])
        self.assertEquals(point.name, point_data['name'])
        self.assertEquals(point.url, point_data['url'])
        self.assertEquals(point.amenity, point_data['amenity'])
        self.assertEquals(point.user_open_id, 'my-open-id')

    def test_point_is_stored(self):
        self.add_point(46.06, 24.10, 'Eau de Web',
                       'website', 'business', 'my-open-id')

        points = self.get_all_points()
        self.assertEquals(len(points), 1)

        point = points[0]
        self.assertEquals(point.latitude, 46.06)
        self.assertEquals(point.longitude, 24.10)
        self.assertEquals(point.name, 'Eau de Web')
        self.assertEquals(point.url, 'website')
        self.assertEquals(point.amenity, 'business')
        self.assertEquals(point.user_open_id, 'my-open-id')

    def test_amenity_is_mandatory(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client.post('/test_login', data={'user_id': 'admin-user'})

        point = {'lat': 45, 'lon': 20, 'name': 'no-type',
                 'url': 'link', 'amenity': 'none'}
        response = client.post('/save_poi', data=point)
        self.assertEqual(len(self.get_all_points()), 0)

    def test_name_is_mandatory(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client.post('/test_login', data={'user_id': 'admin-user'})

        point = {'lat': 45, 'lon': 20, 'name': '',
                 'url': 'link', 'amenity': 'pub'}
        response = client.post('/save_poi', data=point)
        self.assertEqual(len(self.get_all_points()), 0)

    def test_valid_coordinates1(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'my-open-id'})

        point = {'lat': -91, 'lon': 181, 'name': 'wrong',
                 'url': 'link', 'amenity': 'pub'}
        response = client.post('/save_poi', data=point)
        self.assertEqual(len(self.get_all_points()), 0)

    def test_valid_coordinates2(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'my-open-id'})

        point = {'lat': 45, 'lon': 181, 'name': 'wrong',
                 'url': 'link', 'amenity': 'pub'}
        response = client.post('/save_poi', data=point)
        self.assertEqual(len(self.get_all_points()), 0)

    def test_valid_coordinates3(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'my-open-id'})

        point = {'lat': -91, 'lon': 20, 'name': 'wrong',
                 'url': 'link', 'amenity': 'pub'}
        response = client.post('/save_poi', data=point)
        self.assertEqual(len(self.get_all_points()), 0)



class DeletePointTest(SetUpTests):

    def test_del_point(self):
        point = self.add_point(1, 2, 'X', 'Y', 'Z', 'W')

        database.del_point(point)

        points = self.get_all_points()
        self.assertEquals(len(points), 0)

    def test_delete_by_non_admin(self):
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client = self.app.test_client()

        client.post('/test_login', data={'user_id': 'non-admin'})

        point = self.add_point(45, 25, 'name', 'url', 'type', 'non-admin')

        address = self.create_url(point.id) + '/delete'
        response = client.post(address, data={'id': point.id})
        points = self.get_all_points()
        self.assertEqual(len(points), 1)
        self.assertEqual(response.status_code, 404)

    def test_delete_point(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client.post('/test_login', data={'user_id': 'admin-user'})

        point = self.add_point(45, 25, 'name', 'url', 'type', 'admin-user')

        address = self.create_url(point.id) + '/delete'
        response = client.post(address, data={'id': point.id})
        self.assertEqual(response.status_code, 200)
        points = self.get_all_points()
        self.assertEqual(len(points), 0)

    def test_delete_nonexistent_point(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client.post('/test_login', data={'user_id': 'admin-user'})

        response = client.post('/points/10/delete', data={'id': 10})
        self.assertEqual(response.status_code, 404)



class SubmitPointTest(SetUpTests):

    @patch('osmpoint.database.get_osm_api')
    def test_submit_points_to_osm(self, mock_get_osm_api):
        mock_osm = mock_get_osm_api.return_value
        client = self.app.test_client()
        p1 = self.add_point(46.06, 24.10, 'Eau de Web',
                             'link1', 'pub', 'my-open-id')
        p2 = self.add_point(46.07, 24.11, 'blabla',
                             'link2', 'bar', 'my-open-id')
        values = [13, 45]
        mock_osm.NodeCreate.side_effect = lambda *args, **kwargs: {'id': values.pop(0)}

        database.submit_points_to_osm([p1, p2])
        self.db.session.commit()

        self.assertEquals(p1.osm_id, 13)
        self.assertEquals(p2.osm_id, 45)
        self.assertEquals(mock_osm.ChangesetCreate.call_count, 1)
        self.assertEquals(mock_osm.NodeCreate.call_args_list, [
            (({u'lat': 46.06, u'lon': 24.1, u'tag': {'name': 'Eau de Web',
                                                     'website': 'link1',
                                                     'amenity': 'pub'}},),
             {}),
            (({u'lat': 46.07, u'lon': 24.11, u'tag': {'name': 'blabla',
                                                      'website': 'link2',
                                                      'amenity': 'bar'}},),
             {})])
        self.assertEquals(mock_osm.ChangesetClose.call_count, 1)

    def test_submit_by_non_admin(self):
        self.app.config['OSMPOINT_ADMINS'] = []
        client = self.app.test_client()

        client.post('/test_login', data={'user_id': 'non-admin'})

        point = self.add_point(45, 25, 'name', 'url', 'type', 'non-admin')

        address = self.create_url(point.id) + '/send'
        response = client.post(address, data={'id': point.id})

        points = self.get_all_points()
        self.assertEqual(points[0].osm_id, None)
        self.assertEqual(response.status_code, 404)

    def test_submit_already_submitted_point(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client.post('/test_login', data={'user_id': 'admin-user'})

        point = database.Point(45, 25, 'name', 'url', 'type', 'admin-user')
        point.osm_id = 100
        self.db.session.add(point)
        self.db.session.commit()

        address = self.create_url(point.id) + '/send'
        response = client.post(address, data={'id': point.id})
        self.assertEqual(response.status_code, 400)

    def test_submit_nonexistent_point(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client.post('/test_login', data={'user_id': 'admin-user'})

        response = client.post('/points/500/send', data={'id': 500})
        self.assertEqual(response.status_code, 404)



class EditPointTest(SetUpTests):

    def test_edit_point(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client.post('/test_login', data={'user_id': 'admin-user'})

        point = self.add_point(45, 25, 'name', 'url', 'type', 'admin-user')

        point_data = {'lat': 40, 'lon': 20, 'name': 'new_name',
                      'url': 'new_url', 'amenity': 'pub', 'id': point.id}
        address = self.create_url(point.id) + '/edit'
        response = client.post(address, data=point_data)
        point = self.get_all_points()[0]
        self.assertEqual(point.latitude, 40)
        self.assertEqual(point.longitude, 20)
        self.assertEqual(point.name, 'new_name')
        self.assertEqual(point.url, 'new_url')
        self.assertEqual(point.amenity, 'pub')

    def test_edit_nonexistent_point(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client.post('/test_login', data={'user_id': 'admin-user'})

        point_data = {'lat': 40, 'lon': 20, 'name': 'wrong', 'id': 500}
        response = client.post('/points/500/edit', data=point_data)
        self.assertEqual(response.status_code, 404)

    def test_edit_point_by_non_admin(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = []
        client.post('/test_login', data={'user_id': 'non-admin-user'})

        point = self.add_point(45, 25, 'name', 'url',
                                'type', 'non-admin-user')

        point_data = {'lat': 40, 'lon': 20, 'name': 'wrong',
                      'url': 'url', 'type': 'type', 'id': point.id}
        address = self.create_url(point.id) + '/edit'
        response = client.post(address, data=point_data)
        self.assertEqual(response.status_code, 404)

    def test_edit_point_with_wrong_coords(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client.post('/test_login', data={'user_id': 'admin-user'})

        point = self.add_point(45, 25, 'name', 'url', 'type', 'admin-user')

        point_data = {'lat': 91, 'lon': 181, 'name': 'wrong',
                      'url': 'url', 'type': 'pub', 'id': point.id}
        address = self.create_url(point.id) + '/edit'
        response = client.post(address, data=point_data)
        point = self.get_all_points()[0]
        self.assertEqual(point.latitude, 45)
        self.assertEqual(point.longitude, 25)

    def test_edit_point_with_no_amenity(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client.post('/test_login', data={'user_id': 'admin-user'})

        point = self.add_point(45, 25, 'name', 'url', 'old_type', 'admin-user')

        point_data = {'lat': 45, 'lon': 25, 'name': 'wrong',
                      'amenity': 'none', 'url': 'url', 'id': point.id}
        address = self.create_url(point.id) + '/edit'
        response = client.post(address, data=point_data)
        point = self.get_all_points()[0]
        self.assertEqual(point.amenity, 'old_type')

    def test_edit_point_with_no_name(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']
        client.post('/test_login', data={'user_id': 'admin-user'})

        point = self.add_point(45, 25, 'old_name', 'url', 'type', 'admin-user')

        point_data = {'lat': 45, 'lon': 25, 'amenity': 'new_type',
                      'name': '', 'url': 'url', 'id': point.id}
        address = self.create_url(point.id) + '/edit'
        response = client.post(address, data=point_data)
        point = self.get_all_points()[0]
        self.assertEqual(point.name, 'old_name')

class UserPageTest(SetUpTests):

    def test_page_renders(self):
        client = self.app.test_client()
        self.assertEqual(client.get('/').status_code, 200)

    def test_show_points(self):
        point = self.add_point(1, 2, 'location_name',
                                'link', 'bar', 'user_name')

        client = self.app.test_client()

        response = client.get('/points')
        self.assertEquals(response.status_code, 200)
        self.assertIn('location_name', response.data)

        database.del_point(point)

        response = client.get('/points')
        self.assertNotIn('location_name', response.data)

    def test_show_map(self):
        client = self.app.test_client()

        self.add_point(45, 25, 'name', 'url', 'type', 'admin-user')

        response = client.get('/points/1')
        self.assertEqual(response.status_code, 200)

    def test_view_nonexistent_point(self):
        client = self.app.test_client()

        response = client.get('/points/500')
        self.assertEqual(response.status_code,404)
