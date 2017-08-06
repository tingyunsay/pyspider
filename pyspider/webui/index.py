#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-22 23:20:39

import socket

from six import iteritems, itervalues
from flask import render_template, request, json

try:
    import flask_login as login
except ImportError:
    from flask.ext import login

from .app import app
from flask import Flask
from flask_cas import CAS, login_required
#from flask.ext.cas import login
#from flask.ext.cas import logout
from flask_cas import login
from flask_cas import logout
#app = Flask("hong")
cas = CAS(app)
app.config['CAS_SERVER'] = 'http://127.0.0.1:8080/cas-server-webapp-4.0.0/'
#app.config['CAS_SERVER'] = 'http://cas.taihenw.com/'
app.config['CAS_AFTER_LOGIN'] = '/'
app.config['SECRET_KEY'] = 'guess'
#设定logout默认指向页面
app.config['CAS_AFTER_LOGOUT'] = "http://localhost:5000"


index_fields = ['name', 'group', 'status', 'comments', 'rate', 'burst', 'updatetime']


@app.route('/old_index')
@login_required
def index2():
    projectdb = app.config['projectdb']
    projects = sorted(projectdb.get_all(fields=index_fields),
                      key=lambda k: (0 if k['group'] else 1, k['group'] or '', k['name']))
    return render_template("index.html", projects=projects , info = cas)


@app.route('/')
@login_required
def index():
    return render_template("control.html", info = cas)


@app.route('/check_cas')
@login_required
def check_cas():
    spidermanagerdb = app.config['spidermanagerdb']
    #get_all只需要选择提取的字段，返回一个生成器，较为简单
    #person_info = spidermanagerdb.get_all(fields=('name', 'group'))
    person_info = spidermanagerdb.get("liaohong" , fields=('name', 'group'))
    return json.dumps(person_info), 200, {'Content-Type': 'application/json'}

    

@app.route('/queues')
@login_required
def get_queues():
    def try_get_qsize(queue):
        if queue is None:
            return 'None'
        try:
            return queue.qsize()
        except Exception as e:
            return "%r" % e

    result = {}
    queues = app.config.get('queues', {})
    for key in queues:
        result[key] = try_get_qsize(queues[key])
    return json.dumps(result), 200, {'Content-Type': 'application/json'}

@app.route('/update', methods=['POST', ])
@login_required
def project_update():
    projectdb = app.config['projectdb']
    project = request.form['pk']
    name = request.form['name']
    value = request.form['value']

    project_info = projectdb.get(project, fields=('name', 'group'))
    if not project_info:
        return "no such project.", 404
    if 'lock' in projectdb.split_group(project_info.get('group')) \
            and not login.current_user.is_active():
        return app.login_response

    if name not in ('group', 'status', 'rate'):
        return 'unknown field: %s' % name, 400
    if name == 'rate':
        value = value.split('/')
        if len(value) != 2:
            return 'format error: rate/burst', 400
        rate = float(value[0])
        burst = float(value[1])
        update = {
            'rate': min(rate, app.config.get('max_rate', rate)),
            'burst': min(burst, app.config.get('max_burst', burst)),
        }
    else:
        update = {
            name: value
        }

    ret = projectdb.update(project, update)
    if ret:
        rpc = app.config['scheduler_rpc']
        if rpc is not None:
            try:
                rpc.update_project()
            except socket.error as e:
                app.logger.warning('connect to scheduler rpc error: %r', e)
                return 'rpc error', 200
        return 'ok', 200
    else:
        return 'update error', 500


@app.route('/counter')
@login_required
def counter():
    rpc = app.config['scheduler_rpc']
    if rpc is None:
        return json.dumps({})

    result = {}
    try:
        data = rpc.webui_update()
        for type, counters in iteritems(data['counter']):
            for project, counter in iteritems(counters):
                result.setdefault(project, {})[type] = counter
        for project, paused in iteritems(data['pause_status']):
            result.setdefault(project, {})['paused'] = paused
    except socket.error as e:
        app.logger.warning('connect to scheduler rpc error: %r', e)
        return json.dumps({}), 200, {'Content-Type': 'application/json'}

    return json.dumps(result), 200, {'Content-Type': 'application/json'}


@app.route('/run', methods=['POST', ])
@login_required
def runtask():
    rpc = app.config['scheduler_rpc']
    if rpc is None:
        return json.dumps({})

    projectdb = app.config['projectdb']
    project = request.form['project']
    project_info = projectdb.get(project, fields=('name', 'group'))
    if not project_info:
        return "no such project.", 404
    if 'lock' in projectdb.split_group(project_info.get('group')) \
            and not login.current_user.is_active():
        return app.login_response

    newtask = {
        "project": project,
        "taskid": "on_start",
        "url": "data:,on_start",
        "process": {
            "callback": "on_start",
        },
        "schedule": {
            "age": 0,
            "priority": 9,
            "force_update": True,
        },
    }

    try:
        ret = rpc.newtask(newtask)
    except socket.error as e:
        app.logger.warning('connect to scheduler rpc error: %r', e)
        return json.dumps({"result": False}), 200, {'Content-Type': 'application/json'}
    return json.dumps({"result": ret}), 200, {'Content-Type': 'application/json'}


@app.route('/robots.txt')
@login_required
def robots():
    return """User-agent: *
Disallow: /
Allow: /$
Allow: /debug
Disallow: /debug/*?taskid=*
""", 200, {'Content-Type': 'text/plain'}
