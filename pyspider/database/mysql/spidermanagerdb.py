#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2017-08-04 17:06 by tingyun

import time
import mysql.connector

from pyspider.database.base.spidermanagerdb import SpidermanagerDB as BaseSpidermanagerDB
from pyspider.database.basedb import BaseDB
from .mysqlbase import MySQLMixin


class SpidermanagerDB(MySQLMixin, BaseSpidermanagerDB, BaseDB):
    __tablename__ = 'platform_info'

    def __init__(self, host='localhost', port=3306, database='SpiderManager',
                 user='root', passwd=None):
        self.database_name = database
        self.conn = mysql.connector.connect(user=user, password=passwd,
                                            host=host, port=port, autocommit=True)
        if database not in [x[0] for x in self._execute('show databases')]:
            self._execute('CREATE DATABASE %s' % self.escape(database))
        self.conn.database = database

        self._execute('''CREATE TABLE IF NOT EXISTS %s (
            `name` varchar(64) PRIMARY KEY,
            `role` varchar(64),
            `info` TEXT,
            `group` TEXT
            ) ENGINE=InnoDB CHARSET=utf8''' % self.escape(self.__tablename__))

    #def insert(self, name, obj={}):
    #project需要按照名字插入，用户不需要
    def insert(self, obj={}):
        obj = dict(obj)
        #obj['name'] = name
        return self._insert(**obj)

    def update(self, name, obj={}, **kwargs):
        obj = dict(obj)
        obj.update(kwargs)
        ret = self._update(where="`name` = %s" % self.placeholder, where_values=(name, ), **obj)
        return ret.rowcount

    def get_all(self, fields=None):
        return self._select2dic(what=fields)

    def get(self, name, fields=None):
        where = "`name` = %s" % self.placeholder
        for each in self._select2dic(what=fields, where=where, where_values=(name, )):
            return each
        return None

    def drop(self, name):
        where = "`name` = %s" % self.placeholder
        return self._delete(where=where, where_values=(name, ))

