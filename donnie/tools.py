#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    BTC: 13MXa7EdMYaXaQK6cDHqd4dwr2stBK3ESE
#    LTC: LfxwJHNCjDh2qyJdfu22rBFi2Eu8BjQdxj
#
#    https://github.com/s4w3d0ff/donnie
#
#    Copyright (C) 2018  https://github.com/s4w3d0ff
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# core
import sys
import logging
import json
from math import floor, ceil
from math import pi as PI
from time import time, gmtime, strftime, strptime, localtime, mktime, sleep
from calendar import timegm
from threading import Thread

# 3rd party
import numpy as np
import pandas as pd
import pymongo
from finta import TA
import tqdm

getLogger = logging.getLogger

logger = getLogger(__name__)

DB = pymongo.MongoClient()

MINUTE, HOUR, DAY = 60, 60 * 60, 60 * 60 * 24
WEEK, MONTH = DAY * 7, DAY * 30
YEAR = DAY * 365

PHI = (1 + 5 ** 0.5) / 2

# smallest coin fraction
SATOSHI = 0.00000001

# console colors ---------------------------------------------------------
WT = '\033[0m'  # white (normal)


def RD(text):
    """ Red """
    return '\033[31m%s%s' % (str(text), WT)


def GR(text):
    """ Green """
    return '\033[32m%s%s' % (str(text), WT)


def OR(text):
    """ Orange """
    return '\033[33m%s%s' % (str(text), WT)


def BL(text):
    """ Blue """
    return '\033[34m%s%s' % (str(text), WT)


def PR(text):
    """ Purple """
    return '\033[35m%s%s' % (str(text), WT)


def CY(text):
    """ Cyan """
    return '\033[36m%s%s' % (str(text), WT)


def GY(text):
    """ Gray """
    return '\033[37m%s%s' % (str(text), WT)


# convertions, misc ------------------------------------------------------
def getHomeDir():
    """
    returns string path to users home folder
    """
    try:
        from pathlib import Path
        return str(Path.home())
    except:
        from os.path import expanduser
        return expanduser("~user")


def isString(obj):
    """
    Checks if an object instance is a string
    """
    return isinstance(obj, str if sys.version_info[0] >= 3 else basestring)

def prepDataframe(df):
    """ Preps a dataframe for sklearn, removing infinity and droping nan """
    # make infinity nan and drop nan
    return df.replace([np.inf, -np.inf], np.nan).dropna()


def splitTrainTestData(df, size=1):
    """ Splits a dataframe by <size> starting from the rear """
    # split db
    return df.iloc[:-size], df.tail(size)

def shuffleDataFrame(df):
    """ Shuffles the rows of a dataframe """
    df.reset_index(inplace=True)
    del df['index']
    return df.reindex(np.random.permutation(df.index))

def addIndicators(df, **conf):
    """ Adds indicators to a ohlc df using 'finta.TA' """
    avail = dir(TA)
    for ind in conf:
        if ind in avail:
            df = pd.concat(
                [getattr(TA, ind)(ohlc=df, **conf[ind]), df],
                axis=1
                )
    return df

def zoomOHLC(df, zoom):
    """ Resamples a ohlc df """
    df.reset_index(inplace=True)
    df.set_index('date', inplace=True)
    df = df.resample(rule=zoom,
                     closed='left',
                     label='left').apply({'_id': 'first',
                                          'open': 'first',
                                          'high': 'max',
                                          'low': 'min',
                                          'close': 'last',
                                          'quoteVolume': 'sum',
                                          'volume': 'sum',
                                          'weightedAverage': 'mean'})
    df.reset_index(inplace=True)
    return df.set_index('_id')

def getDatabase(db):
    """ Returns a mongodb database """
    return DB[db]

def getLastEntry(db):
    """ Get the last entry of a collection """
    return db.find_one(sort=[('_id', pymongo.DESCENDING)])

def updateChartData(db, data):
    """ Upserts chart data into db with a tqdm wrapper. """
    for i in tqdm.trange(len(data)):
        db.update_one({'_id': data[i]['date']}, {
                      "$set": data[i]}, upsert=True)

def getChartDataFrame(db, start):
    """
    Gets the last collection entrys starting from 'start' and puts them in a df
    """
    try:
        df = pd.DataFrame(list(db.find({"_id": {"$gt": start}})))
        # set date column to datetime
        df['date'] = pd.to_datetime(df["_id"], unit='s')
        df.set_index('_id', inplace=True)
        return df
    except Exception as e:
        logger.exception(e)
        return False

def wait(i=10):
    """ Wraps 'time.sleep()' with logger output """
    logger.debug('Waiting %d sec... (%.2fmin)', i, i / 60.0)
    sleep(i)


def epoch2UTCstr(timestamp=False, fmat="%Y-%m-%d %H:%M:%S"):
    """
    - takes epoch timestamp
    - returns UTC formated string
    """
    if not timestamp:
        timestamp = time()
    return strftime(fmat, gmtime(timestamp))


def UTCstr2epoch(datestr=False, fmat="%Y-%m-%d %H:%M:%S"):
    """
    - takes UTC date string
    - returns epoch
    """
    if not datestr:
        datestr = epoch2UTCstr()
    return timegm(strptime(datestr, fmat))


def epoch2localstr(timestamp=False, fmat="%Y-%m-%d %H:%M:%S"):
    """
    - takes epoch timestamp
    - returns localtimezone formated string
    """
    if not timestamp:
        timestamp = time()
    return strftime(fmat, localtime(timestamp))


def localstr2epoch(datestr=False, fmat="%Y-%m-%d %H:%M:%S"):
    """
    - takes localtimezone date string,
    - returns epoch
    """
    if not datestr:
        datestr = epoch2localstr()
    return mktime(strptime(datestr, fmat))


def saveJSON(data, filename):
    """ Save data as json to a file """
    with open(filename, 'w') as f:
        return json.dump(data, f, indent=4)


def loadJSON(filename):
    """ Load json file """
    with open(filename, 'r') as f:
        return json.load(f)


def float2percent(n):
    """ n * 100 """
    return float(n) * 100


def percent2float(n):
    """ n / 100 """
    return float(n) / 100


def addPercent(n, p):
    """ Add a percentage of a number to itself.
    (n * (p/100)) + n
    >>> addPercent(8, 0.5)
    8.04
    """
    return (n * percent2float(p)) + n


def roundDown(n, d=8):
    """
    n :: float to be rounded
    d :: int number of decimals to round to
    """
    d = 10**d
    return floor(float(n) * d) / d


def roundUp(n, d=8):
    """
    n :: float to be rounded
    d :: int number of decimals to round to
    """
    d = 10**d
    return ceil(float(n) * d) / d


def getAverage(seq):
    """
    Finds the average of <seq>
    >>> getAverage(['3', 9.4, '0.8888', 5, 1.344444, '3', '5', 6, '7'])
    4.033320571428571
    """
    return sum(seq) / len(seq)


def geoProgress(n, r=PHI, size=5):
    """ Creates a Geometric Progression with the Geometric sum of <n>
    https://stackoverflow.com/questions/36959341
    >>> l = geoProgress(42)
    >>> l
    [2.5725461188664465, 4.162467057952537, 6.735013176818984,
    10.897480234771521, 17.63249341159051]
    >>> sum(l)
    42.0
    """
    return [(n * (1 - r) / (1 - r ** size)) * r ** i for i in range(size)]
