# -*- encoding: utf8 -*-

import psycopg2
import argparse
import re
from polyline.codec import PolylineCodec
from typing import List, Tuple


polyline_codec = PolylineCodec()


def parse_polygon(polygon: str) -> List[List[Tuple[float, float]]]:
    p = re.compile('[(]([^()]*)[)]')
    result = []
    for s in p.findall(polygon):
        sub_result = []
        tokens = s.split(',')

        for t in tokens:
            lng, lat = t.split(' ')
            lat = float(lat)
            lng = float(lng)
            sub_result.append((lat, lng))
        result.append(sub_result)
    return result


def encode_polygon(polygon: str):
    return [polyline_codec.encode(x) for x in parse_polygon(polygon)]


def invert_lat_lng(polygon:str):
    return [','.join([(' '.join(map(str, x))) for x in p]) for p in parse_polygon(polygon)]


class GisProcessor(object):
    def __init__(self, output_polyline, output_all):
        self.connection = psycopg2.connect(host='127.0.0.1', port=5432, database="gis", user="admin")
        self.output_polyline = output_polyline
        self.output_all = output_all

    def find_polygons_for_single_osm_id(self, osm_id: int):
        cursor = self.connection.cursor()
        cursor.execute("select st_astext(way) from planet_osm_polygon where osm_id=%d;" % (osm_id))
        for polygon in cursor.fetchall():
            for s in encode_polygon(str(polygon)):
                print(s)

    def find_polygons_by_osm_id(self, osm_id: int, limit_admin_level: int):
        cursor = self.connection.cursor()
        cursor.execute("select name, admin_level from planet_osm_polygon where osm_id=%d;" % (osm_id))
        for name, admin_level in cursor.fetchall():
            if name is None:
                name = ''
            admin_level = int(admin_level)
            self.find_polygons_recursive(admin_level+1, limit_admin_level, osm_id, [name])


    def find_polygons(self, admin_level: int, limit_admin_level: int):
        cursor = self.connection.cursor()
        cursor.execute("select osm_id, name from planet_osm_polygon where admin_level ='%d';" % (admin_level))
        for osm_id, name in cursor.fetchall():
            if name is None:
                name = ''
            self.find_polygons_recursive(admin_level+1, limit_admin_level, osm_id, [name])


    def output_polygon(self, polygon, names):
        if self.output_polyline:
            for s in encode_polygon(polygon):
                print(s)
        else:
            for s in invert_lat_lng(polygon):
                print('|'.join(names) + '|' + s)

    def find_polygons_recursive(self, admin_level: int, limit_admin_level: int, osm_id: int, previous_names: List[str]):
        cursor = self.connection.cursor()

        if admin_level == limit_admin_level or self.output_all:
            cursor.execute("select b.osm_id, b.name, st_astext(b.way) from planet_osm_polygon a join planet_osm_polygon b on (a.osm_id = %d and b.admin_level='%d' and st_contains(a.way, b.way))" % (osm_id, admin_level))
            for current_osm_id, name, polygon in cursor.fetchall():
                if name is None:
                    name = ''
                if polygon is None:
                    print("polygon is none")
                else:
                    names = previous_names.copy()
                    names.append(name)
                    self.output_polygon(polygon, names)
                    if self.output_all:
                        self.find_polygons_recursive(admin_level + 1, limit_admin_level, current_osm_id, names)

        else:
            # polígono a contém polígono b
            cursor.execute("select b.osm_id, b.name from planet_osm_polygon a join planet_osm_polygon b on (a.osm_id = %d and b.admin_level='%d' and st_contains(a.way, b.way))" % (osm_id, admin_level))
            for osm_id, name in cursor.fetchall():
                if name is None:
                    name = ''
                names = previous_names.copy()
                names.append(name)
                self.find_polygons_recursive(admin_level+1, limit_admin_level, osm_id, names)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Polygon generator')
    parser.add_argument('--osm-id', type=int, help='OSM id')
    parser.add_argument('--single', action='store_true', help='Output only the polygon found by OSM id')
    parser.add_argument('--output-all', action='store_true', help='Output all polygons')
    parser.add_argument('-a', type=int, default=2, help='Minimum admin_level (default=2)')
    parser.add_argument('-A', type=int, default=10, help='Maximum admin_level (default=10)')
    parser.add_argument('--polyline', action='store_true', help='Output polyline encoded data')

    args = parser.parse_args()

    gis_processor = GisProcessor(output_polyline=args.polyline, output_all=args.output_all)

    if args.osm_id is None:
        gis_processor.find_polygons(args.a, args.A, args.polyline)
    else:
        if args.single:
            gis_processor.find_polygons_for_single_osm_id(args.osm_id)
        else:
            gis_processor.find_polygons_by_osm_id(args.osm_id, args.A)


