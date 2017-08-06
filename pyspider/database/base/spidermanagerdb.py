#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-09 11:28:52

import re

# NOTE: When get/get_all/check_update from database with default fields,
#       all following fields should be included in output dict.

#modify 2017.08.06 by tingyun 
{
    'spidermanager': {
        'name': str,
        'role': str,
        'info': str,
        'group': str,
    }
}


class SpidermanagerDB(object):

    def insert(self, name, obj={}):
        raise NotImplementedError

    def update(self, name, obj={}, **kwargs):
        raise NotImplementedError

    def get_all(self, fields=None):
        raise NotImplementedError

    def get(self, name, fields):
        raise NotImplementedError

    def drop(self, name):
        raise NotImplementedError

    def verify_project_name(self, name):
        if len(name) > 64:
            return False
        if re.search(r"[^\w]", name):
            return False
        return True

    def copy(self):
        '''
        database should be able to copy itself to create new connection

        it's implemented automatically by pyspider.database.connect_database
        if you are not create database connection via connect_database method,
        you should implement this
        '''
        raise NotImplementedError
