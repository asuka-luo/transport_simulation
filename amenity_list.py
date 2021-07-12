"""
Created on Fri Dec 16 23:01:13 2016

@author: denglu_wzz
"""

import osmium as o
import shapely.wkb as wkblib

from util import convert_amenity_into_geojson
from util import read_pickle_file
from util import store_geojson
from util import store_pickle_file

wkbfab = o.geom.WKBFactory()
OSM_FILE = "data/hessen-latest.osm.pbf"


class ShopListHandler(o.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.results = []

    def print_amenity(self, amenity, tags, lon, lat):
        name = tags['name'] if 'name' in tags else ''
        self.results.append([lon, lat, tags['shop'], name])

    def node(self, n):
        if 'shop' in n.tags and n.tags['shop'] != 'no':
            self.print_amenity(n.tags, n.location.lon, n.location.lat)

    def area(self, a):
        if 'shop' in a.tags and a.tags['shop'] != 'no':
            wkb = wkbfab.create_multipolygon(a)
            poly = wkblib.loads(wkb, hex=True)
            centroid = poly.representative_point()
            self.print_amenity(a.tags, centroid.x, centroid.y)


class UniListHandler(o.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.results = []

    def print_amenity(self, amenity, tags, lon, lat):
        name = tags['name'] if 'name' in tags else ''
        self.results.append([lon, lat, 'university', name])

    def node(self, n):
        if ('amenity' in n.tags and n.tags['amenity'] == 'university') \
                or ('building' in n.tags and n.tags['building'] == 'university'):
            self.print_amenity(n.tags, n.location.lon, n.location.lat)

    def area(self, a):
        if ('amenity' in a.tags and a.tags['amenity'] == 'university') \
                or ('building' in a.tags and a.tags['building'] == 'university'):
            wkb = wkbfab.create_multipolygon(a)
            poly = wkblib.loads(wkb, hex=True)
            centroid = poly.representative_point()
            self.print_amenity(a.tags, centroid.x, centroid.y)


class LeisureListHandler(o.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.results = []

    def print_amenity(self, amenity, tags, lon, lat):
        name = tags['name'] if 'name' in tags else ''
        # print("%f %f %-15s %s" % (lon, lat, tags, name))
        self.results.append([lon, lat, tags['leisure'], name])

    def node(self, n):
        if 'leisure' in n.tags:
            self.print_amenity(n.tags, n.location.lon, n.location.lat)

    def area(self, a):
        if 'leisure' in a.tags:
            wkb = wkbfab.create_multipolygon(a)
            poly = wkblib.loads(wkb, hex=True)
            centroid = poly.representative_point()
            self.print_amenity(a.tags, centroid.x, centroid.y)


def store_and_convert(filename, result_list, read_only=False):
    # if read_only it'll ignore result and read pickle file,
    # otherwise store result in pickle file and convert to geojson
    if not read_only:
        store_pickle_file(filename, result_list)
    loaded_result = read_pickle_file(filename)
    file = convert_amenity_into_geojson(loaded_result)
    store_geojson(file, filename)


if __name__ == '__main__':
    shop_handler = ShopListHandler()
    shop_handler.apply_file(OSM_FILE)
    store_and_convert('shops', shop_handler.results, True)

    uni_handler = UniListHandler()
    uni_handler.apply_file(OSM_FILE)
    store_and_convert('uni', uni_handler.results, True)

    leisure_handler = LeisureListHandler()
    leisure_handler.apply_file(OSM_FILE)
    store_and_convert('leisure', leisure_handler.results, True)
