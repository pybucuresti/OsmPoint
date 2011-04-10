import unittest2
import osm_point


class UserPageTest(unittest2.TestCase):
    def test_page_renders(self):
        app = osm_point.app.test_client()
        self.assertEqual(app.get('/').status_code, 200)

    def test_point_is_stored(self):
        db = osm_point.db
        db.create_all()

        point = osm_point.Point(46.06, 24.10, "Eau de Web")
        db.session.add(point)
        db.session.commit()

        points = osm_point.Point.query.all()
        self.assertEquals(len(points), 1)

        point = points[0]
        self.assertEquals(point.latitude, 46.06)
        self.assertEquals(point.longitude, 24.10)
        self.assertEquals(point.name, "Eau de Web")




        
