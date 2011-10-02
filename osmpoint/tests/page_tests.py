import flask
import unittest2
from osmpoint import database

from mock import patch, Mock


class SetUpTests(unittest2.TestCase):

    def setUp(self):
        from osmpoint.testing import app_for_testing
        self.app = app_for_testing(self.addCleanup)
        self.db = database.db
        self._ctx = self.app.test_request_context()
        self._ctx.push()
        self.addCleanup(self._ctx.pop)
        self.app.config['OSMPOINT_ADMINS'] = ['admin-user']

        @self.app.route('/test_login', methods=['POST'])
        def test_login():
            flask.session['openid'] = flask.request.form['user_id']
            return "ok"

    def tearDown(self):
        self.db.session.remove()

    def get_all_points(self):
        return [point for p_id, point in database.get_all_points()]


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
        self.assertEqual(response.status_code, 200)

        point = self.get_all_points()[0]
        self.assertEquals(point['lat'], point_data['lat'])
        self.assertEquals(point['lon'], point_data['lon'])
        self.assertEquals(point['name'], point_data['name'])
        self.assertEquals(point['url'], point_data['url'])
        self.assertEquals(point['amenity'], point_data['amenity'])
        self.assertEquals(point['user_open_id'], 'my-open-id')

    def test_point_is_stored(self):
        database.add_point(46.06, 24.10, 'Eau de Web',
                           'website', 'business', 'my-open-id')

        points = self.get_all_points()
        self.assertEquals(len(points), 1)

        point = points[0]
        self.assertEquals(point['lat'], 46.06)
        self.assertEquals(point['lon'], 24.10)
        self.assertEquals(point['name'], 'Eau de Web')
        self.assertEquals(point['url'], 'website')
        self.assertEquals(point['amenity'], 'business')
        self.assertEquals(point['user_open_id'], 'my-open-id')

    def test_amenity_is_mandatory(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        point = {'lat': 45, 'lon': 20, 'name': 'no-type',
                 'url': 'link', 'amenity': 'none', 'new_amenity': ''}
        response = client.post('/save_poi', data=point)
        self.assertEqual(len(self.get_all_points()), 0)

    def test_enter_new_amenity(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        point = {'lat': 45, 'lon': 20, 'name': 'no-type',
                 'url': 'link', 'amenity': '_other', 'new_amenity': 'new_type'}
        response = client.post('/save_poi', data=point)

        all_points = self.get_all_points()
        self.assertEqual(len(all_points), 1)

        point = all_points[0]
        self.assertEqual(point['name'], 'no-type')
        self.assertEqual(point['amenity'], '#new_type')

    def test_name_is_mandatory(self):
        client = self.app.test_client()
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
        p_id = database.add_point(1, 2, 'X', 'Y', 'Z', 'W')

        database.del_point(p_id)

        points = self.get_all_points()
        self.assertEquals(len(points), 0)

    def test_delete_by_non_admin(self):
        client = self.app.test_client()

        client.post('/test_login', data={'user_id': 'non-admin'})

        p_id = database.add_point(45, 25, 'name', 'url', 'type', 'non-admin')

        address = flask.url_for('.delete_point', point_id=p_id)
        response = client.post(address, data={'confirm': 'true'})
        points = self.get_all_points()
        self.assertEqual(len(points), 1)
        self.assertEqual(response.status_code, 403)

    def test_confirm_delete_point(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        p_id = database.add_point(45, 25, 'name', 'url', 'type', 'admin-user')

        address = flask.url_for('.delete_point', point_id=p_id)
        response = client.post(address, data={'confirm': 'true'})

        self.assertEqual(response.status_code, 200)
        points = self.get_all_points()
        self.assertEqual(len(points), 0)

    def test_delete_nonexistent_point(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        address = flask.url_for('.delete_point', point_id=10)
        response = client.post(address, data={'confirm': 'true'})
        self.assertEqual(response.status_code, 404)

    def test_cancel_deletion(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        p_id = database.add_point(45, 25, 'name', 'url', 'type', 'admin-user')

        address = flask.url_for('.delete_point', point_id=p_id)
        response = client.post(address)

        points = self.get_all_points()
        self.assertEqual(len(points), 1)


class SubmitPointTest(SetUpTests):

    @patch('OsmApi.OsmApi')
    def test_api_url_and_login(self, mock_osm_api):
        self.app.config['OSM_PASSWORD_PATH'] = 'some-path'
        self.app.config['OSM_API'] = 'the-api-url'
        api = database.get_osm_api()
        mock_osm_api.assert_called_once_with(passwordfile='some-path',
                                             api='the-api-url')

    @patch('osmpoint.database.get_osm_api')
    def test_changesets(self, mock_get_osm_api):
        mock_osm = mock_get_osm_api.return_value
        client = self.app.test_client()
        p1_id = database.add_point(46.06, 24.10, 'Eau de Web',
                                   'link1', 'pub', 'my-open-id')
        p2_id = database.add_point(46.07, 24.11, 'blabla',
                                   '', 'bar', 'my-open-id')
        values = [13, 45]
        mock_osm.ChangesetCreate.return_value = 13
        mock_osm.NodeCreate.side_effect = lambda *args, **kwargs: {'id': values.pop(0)}

        database.submit_points_to_osm([p1_id, p2_id])
        self.db.session.commit()

        rdb = flask.current_app.rdb
        p1 = rdb.get_object('point', p1_id)
        p2 = rdb.get_object('point', p2_id)
        self.assertEquals(p1['osm_id'], 13)
        self.assertEquals(p2['osm_id'], 45)
        self.assertEquals(mock_osm.ChangesetCreate.call_count, 1)
        tags1 = {'name': 'Eau de Web', 'website': 'link1',
                 'amenity': 'pub', 'source': 'poi.grep.ro'}
        tags2 = {'name': 'blabla', 'amenity': 'bar', 'source': 'poi.grep.ro'}
        self.assertEquals(mock_osm.NodeCreate.call_args_list, [
            (({u'lat': 46.06, u'lon': 24.1, u'tag': tags1},), {}),
            (({u'lat': 46.07, u'lon': 24.11, u'tag': tags2},), {})])
        self.assertEquals(mock_osm.ChangesetClose.call_count, 1)

    @patch('osmpoint.database.get_osm_api')
    def test_submit_points_to_osm(self, mock_get_osm_api):
        mock_osm = mock_get_osm_api.return_value

        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        p_id = database.add_point(46.06, 24.10, 'Eau de Web',
                                  'link1', 'pub', 'admin-user')

        mock_osm.ChangesetCreate.return_value = 13
        mock_osm.NodeCreate.return_value = {'id': 50}

        address = flask.url_for('.send_point', point_id=p_id)
        response = client.post(address)

        self.assertEqual(response.status_code, 200)

        tags = {'name': 'Eau de Web',
                'website': 'link1',
                'amenity': 'pub',
                'source': 'poi.grep.ro'}
        ok_data = {u'lat': 46.06, u'lon': 24.1, u'tag': tags}
        mock_osm.NodeCreate.assert_called_once_with(ok_data)

    @patch('osmpoint.database.get_osm_api')
    def test_submit_by_non_admin(self, mock_get_osm_api):
        self.app.config['OSMPOINT_ADMINS'] = []
        client = self.app.test_client()

        client.post('/test_login', data={'user_id': 'non-admin'})

        p_id = database.add_point(45, 25, 'name', 'url', 'type', 'non-admin')

        address = flask.url_for('.send_point', point_id=p_id)
        response = client.post(address)

        self.assertFalse(mock_get_osm_api.called)
        points = self.get_all_points()
        self.assertEqual(points[0]['osm_id'], None)
        self.assertEqual(response.status_code, 403)

    @patch('osmpoint.database.get_osm_api')
    def test_submit_already_submitted_point(self, mock_get_osm_api):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        p_id = database.add_point(45, 25, 'name', 'url', 'type', 'admin-user')
        database.set_point_field(p_id, 'osm_id', 100)

        address = flask.url_for('.send_point', point_id=p_id)
        response = client.post(address)

        self.assertFalse(mock_get_osm_api.called)
        self.assertEqual(response.status_code, 400)

    @patch('osmpoint.database.get_osm_api')
    def test_submit_nonexistent_point(self, mock_get_osm_api):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        response = client.post('/points/500/send')

        self.assertFalse(mock_get_osm_api.called)
        self.assertEqual(response.status_code, 404)

    @patch('osmpoint.database.get_osm_api')
    def test_submit_points_log_records(self, mock_get_osm_api):
        import logging
        self.log_records = log_records = []
        class TestingHandler(logging.Handler):
            def emit(self, record):
                log_records.append(self.format(record))
        self.log_handler = TestingHandler()
        self.db_logger = logging.getLogger('osmpoint.database.osm')
        self.db_logger.addHandler(self.log_handler)
        self.addCleanup(self.db_logger.removeHandler, self.log_handler)

        mock_osm = mock_get_osm_api.return_value
        mock_osm.ChangesetCreate.return_value = 999
        mock_osm.NodeCreate.return_value = {'a': 'b', 'id': 13}

        client = self.app.test_client()
        p_id = database.add_point(46.06, 24.10, 'Eau de Web',
                                  'link1', 'pub', 'my-open-id')
        log_records[:] = []

        database.submit_points_to_osm([p_id])

        self.assertEqual(self.log_records, [
            "Begin OSM changeset 999",
            "OSM point: {'a': 'b', 'id': 13}",
            "OSM changeset committed",
        ])

    def test_submitted_point_url(self):
        self.app.config['OSM_API'] = 'fake.api.example.com'

        p_id = database.add_point(46.06, 24.10, 'EdW', '', 'pub', 'my-open-id')
        database.set_point_field(p_id, 'osm_id', 1234)

        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})
        response = client.get('/points/%d' % p_id)
        url = 'http://fake.api.example.com/browse/node/1234'
        self.assertIn('<a href="%s">' % url, response.data)


class ModerationPageTest(SetUpTests):

    def setUp(self):
        super(ModerationPageTest, self).setUp()
        self.p1_id = database.add_point(10., 10., 'NameOne', '', 'pub', 'user1')
        self.p2_id = database.add_point(20., 20., 'NameTwo', '', 'pub', 'user2')
        self.client = self.app.test_client()
        self.client.post('/test_login', data={'user_id': 'admin-user'})

    def _mock_osm_api(self):
        mock_osm = Mock()

        mock_osm.ChangesetCreate.return_value = 13

        self.osm_nodes = []
        def mock_create_node(data):
            self.osm_nodes.append(data);
            return {'id': len(self.osm_nodes)}

        mock_osm.NodeCreate.side_effect = mock_create_node

        return mock_osm

    def test_view(self):
        response = self.client.get('/moderate')
        self.assertEqual(response.status_code, 200)
        self.assertIn('NameOne', response.data)

    @patch('osmpoint.database.get_osm_api')
    def test_upload_to_osm(self, mock_get_osm_api):
        mock_get_osm_api.return_value = self._mock_osm_api()

        response = self.client.post('/moderate', data={
            'point_id': [self.p1_id, self.p2_id]})
        self.assertEqual(response.status_code, 200)
        self.assertIn("2 points uploaded to OSM", response.data)
        self.assertEqual(len(self.osm_nodes), 2)


class EditPointTest(SetUpTests):

    def test_edit_point(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        p_id = database.add_point(45, 25, 'name', 'url', 'type', 'admin-user')

        point_data = {'lat': 40, 'lon': 20, 'name': 'new_name',
                      'url': 'new_url', 'amenity': 'pub', 'id': p_id}
        address = flask.url_for('.edit_point', point_id=p_id)
        response = client.post(address, data=point_data)
        point = self.get_all_points()[0]
        self.assertEqual(point['lat'], 40)
        self.assertEqual(point['lon'], 20)
        self.assertEqual(point['name'], 'new_name')
        self.assertEqual(point['url'], 'new_url')
        self.assertEqual(point['amenity'], 'pub')

    def test_edit_nonexistent_point(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        point_data = {'lat': 40, 'lon': 20, 'name': 'wrong', 'id': 500}
        response = client.post('/points/500/edit', data=point_data)
        self.assertEqual(response.status_code, 404)

    def test_edit_point_by_non_admin(self):
        client = self.app.test_client()
        self.app.config['OSMPOINT_ADMINS'] = []
        client.post('/test_login', data={'user_id': 'non-admin-user'})

        p_id = database.add_point(45, 25, 'name', 'url',
                                  'type', 'non-admin-user')

        point_data = {'lat': 40, 'lon': 20, 'name': 'wrong',
                      'url': 'url', 'type': 'type', 'id': p_id}
        address = flask.url_for('.edit_point', point_id=p_id)
        response = client.post(address, data=point_data)
        self.assertEqual(response.status_code, 403)

    def test_edit_point_with_wrong_coords(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        p_id = database.add_point(45, 25, 'name', 'url', 'type', 'admin-user')

        point_data = {'lat': 91, 'lon': 181, 'name': 'wrong',
                      'url': 'url', 'type': 'pub', 'id': p_id}
        address = flask.url_for('.edit_point', point_id=p_id)
        response = client.post(address, data=point_data)
        point = self.get_all_points()[0]
        self.assertEqual(point['lat'], 45)
        self.assertEqual(point['lon'], 25)

    def test_edit_point_with_no_amenity(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        p_id = database.add_point(45, 25, 'name', 'url', 'old_type', 'admin-user')

        point_data = {'lat': 45, 'lon': 25, 'name': 'wrong', 'new_amenity': '',
                      'amenity': 'none', 'url': 'url', 'id': p_id}
        address = flask.url_for('.edit_point', point_id=p_id)
        response = client.post(address, data=point_data)
        point = self.get_all_points()[0]
        self.assertEqual(point['amenity'], 'old_type')

    def test_edit_point_with_another_amenity(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        p_id = database.add_point(45, 25, 'name', 'url', 'old_type', 'admin-user')

        point_data = {'lat': 45, 'lon': 25, 'name': 'wrong', 'new_amenity': 'new',
                      'amenity': '_other', 'url': 'url', 'id': p_id}
        address = flask.url_for('.edit_point', point_id=p_id)
        response = client.post(address, data=point_data)
        point = self.get_all_points()[0]
        self.assertEqual(point['amenity'], 'new')

    def test_edit_point_with_no_name(self):
        client = self.app.test_client()
        client.post('/test_login', data={'user_id': 'admin-user'})

        p_id = database.add_point(45, 25, 'old_name', 'url', 'type', 'admin-user')

        point_data = {'lat': 45, 'lon': 25, 'amenity': 'new_type',
                      'name': '', 'url': 'url', 'id': p_id}
        address = flask.url_for('.edit_point', point_id=p_id)
        response = client.post(address, data=point_data)
        point = self.get_all_points()[0]
        self.assertEqual(point['name'], 'old_name')

class UserPageTest(SetUpTests):

    def test_page_renders(self):
        client = self.app.test_client()
        self.assertEqual(client.get('/').status_code, 200)

    def test_show_points(self):
        point_id = database.add_point(1, 2, 'location_name',
                                      'link', 'bar', 'user_name')

        client = self.app.test_client()

        response = client.get('/points')
        self.assertEquals(response.status_code, 200)
        self.assertIn('location_name', response.data)

        database.del_point(point_id)

        response = client.get('/points')
        self.assertNotIn('location_name', response.data)

    def test_show_map(self):
        client = self.app.test_client()

        database.add_point(45, 25, 'name', 'url', 'type', 'admin-user')

        response = client.get('/points/1')
        self.assertEqual(response.status_code, 200)

    def test_view_nonexistent_point(self):
        client = self.app.test_client()

        response = client.get('/points/500')
        self.assertEqual(response.status_code,404)
