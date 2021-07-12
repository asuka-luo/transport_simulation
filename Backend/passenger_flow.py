"""
Created on Fri Dec 16 10:09:15 2016

@author: martin
"""

import datetime

import numpy as np
from shapely.geometry import Point

import config
import util


class Route:
    """Route seen as a whole path without transfer"""

    def __init__(self, path, starttime, duration, category, remark, section=None):
        """
        __init__(self, [[]], datetime.datetime, datetime.timedelta, str, str, [dict{'startpoint','endpoint','d_time',
        'name','direction','trip_id'}])
        path contains list of coordinates
        """
        self.path = path
        self.starttime = starttime
        self.endtime = self.starttime + duration
        self.duration = duration
        self.category = category
        self.remark = remark
        self.section = section

    def __repr__(self):
        return 'Category:{},\nRemark:{},\nstarts_at:{},\nends_at:{}\n'.format(
            self.category, self.remark, self.starttime, self.endtime)

    def output_list(self, show_location):
        if show_location:
            return [self.category, self.remark, self.starttime.time(),
                    self.endtime.time(), self.path]
        else:
            return [self.category, self.remark,
                    self.starttime.time(), self.endtime.time()]


class Activity:
    def __init__(self, location, starttime, duration, category, remark=None):
        """
        __init__(self, Point, datetime.datetime, datetime.timedelta, str, str)
        remerk exits if act takes in advance
        """
        self.location = location
        self.starttime = starttime
        self.endtime = self.starttime + duration
        self.duration = duration
        self.category = category
        self.remark = remark if remark else ""

    def execute_activity_in_advance(self, changed_starttime):
        # if execute in advance shift the starttime
        # if execute later keep the duration
        advance_time = self.starttime - changed_starttime

        self.starttime = changed_starttime

        if advance_time > datetime.timedelta(0):
            self.duration += advance_time
            self.remark = str(advance_time) + ' in advance'
        else:
            self.remark = str(-advance_time) + ' later'

    def __repr__(self):
        return 'Category:{},\nremark:{},\nstarts_at:{},\n\
        ends_at:{},\nlocation:{}\n'.format(
            self.category, self.remark,
            self.starttime, self.endtime,
            list(self.location.coords[0]))

    def output_list(self, show_location):
        if show_location:
            return [self.category, self.remark, self.starttime.time(),
                    self.endtime.time(), self.location.coords[0]]
        else:
            return [self.category, self.remark, self.starttime.time(),
                    self.endtime.time()]


class AreaPoint:
    def __init__(self, area_type, current_point=None):

        self.area_type = area_type
        self.location = self.get_random_point_given_regiontype(
            area_type, current_point)

    def get_random_point_given_regiontype(self, giventype, current_point):
        if giventype == config.SLEEP:
            squares = util.get_residence_population('residence')
            probability = squares[:, 2] / sum(squares[:, 2])
            index = np.random.choice(range(len(squares)), p=probability)

            lon, lat = util.etrs_to_wgs84(squares[index][0], squares[index][1])
            return Point(lon, lat)

        elif giventype == config.WORK or giventype == config.ATTEND_CLASS:
            normalized_probs, neighbors = util.k_nearest_point(giventype, current_point)

            most_likely_point = neighbors[
                np.random.choice(range(len(neighbors)), p=normalized_probs)]

            return most_likely_point

        else:
            raise RuntimeError('Wrong Area Type!')


class TransportationTool:
    def __init__(self, category, location):
        """__init__(self, str, Point)"""
        self.category = category
        self.location = location

    def is_available(self, person_location):
        """
        is_available(self, Point)
        Point in form (long,lat)
        """
        if util.calculate_distance(person_location, self.location) > 0:
            return False
        else:
            return True
