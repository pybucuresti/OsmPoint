from imposm.parser import OSMParser
import yaml
import sys

# remove unwanted points
class AmenityFilter(object):
    types = ['pub', 'cafe', 'bar', 'nightclub', 'restaurant',
             'fuel', 'cinema', 'theatre']
    def amenity_filter(self, tags):
        if 'name' not in tags.keys() or 'amenity' not in tags.keys():
           for key in tags.keys():
               del tags[key]
        try: 
            if tags['amenity'] not in self.types:
                for key in tags.keys():
                    del tags[key]
        except KeyError:
            for key in tags.keys():
                del tags[key]

# extract points only from Bucharest
class NodesCoords(object):
    points = []
    def nodes_callback(self, nodes):
        for osm_id, tags, coords in nodes:
            if 44.35 <= coords[1] <= 44.5 and 25.94 <= coords[0] <= 26.24 :
                p = {
                    'osm_id': osm_id,
                    'lon': coords[0],
                    'lat': coords[1],
                    'name': tags['name'],
                    'amenity': tags['amenity'],
                }
                self.points.append(p)


def main():

    file_name = sys.argv[1]
    filter = AmenityFilter()
    nodes = NodesCoords()
    p = OSMParser(nodes_callback=nodes.nodes_callback,
                  nodes_tag_filter=filter.amenity_filter)
    p.parse_pbf_file(file_name)
    print yaml.dump(nodes.points)

if __name__ == '__main__':
    main()
