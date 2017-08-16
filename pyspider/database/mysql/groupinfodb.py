#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2017-08-15 10:47 by tingyun

import time
import mysql.connector

from pyspider.database.base.groupinfodb import GroupinfoDB as BaseGroupinfoDB
from pyspider.database.basedb import BaseDB
from .mysqlbase import MySQLMixin


class GroupinfoDB(MySQLMixin, BaseGroupinfoDB, BaseDB):
    __tablename__ = 'groupinfodb'

    def __init__(self, host='localhost', port=3306, database='groupinfodb',
                 user='root', passwd=None):
        self.database_name = database
        self.conn = mysql.connector.connect(user=user, password=passwd,
                                            host=host, port=port, autocommit=True)
        if database not in [x[0] for x in self._execute('show databases')]:
            self._execute('CREATE DATABASE %s' % self.escape(database))
        self.conn.database = database

        self._execute('''CREATE TABLE IF NOT EXISTS %s (
            `gname` varchar(64) PRIMARY KEY,
            `creater` varchar(64),
            `projects` TEXT,
            `createtime` double(16, 4),
            `updatetime` double(16, 4)
            ) ENGINE=InnoDB CHARSET=utf8''' % self.escape(self.__tablename__))

    def insert(self, gname, obj={}):
        obj = dict(obj)
        obj['gname'] = gname
        obj['updatetime'] = time.time()
        return self._insert(**obj)

    def update(self, gname, obj={}, **kwargs):
        obj = dict(obj)
        obj.update(kwargs)
        obj['updatetime'] = time.time()
        ret = self._update(where="`gname` = %s" % self.placeholder, where_values=(gname, ), **obj)
        return ret.rowcount

    def get_all(self, fields=None):
        return self._select2dic(what=fields)

    #查询主键，返回单条记录
    def get(self,gname, fields=None):
        where = "`gname` = %s" % self.placeholder
        for each in self._select2dic(what=fields, where=where, where_values=(gname, )):
            return each
        return None

    def drop(self, gname):
        where = "`gname` = %s" % self.placeholder
        return self._delete(where=where, where_values=(gname, ))

    def check_update(self, timestamp, fields=None):
        where = "`updatetime` >= %f" % timestamp
        return self._select2dic(what=fields, where=where)
