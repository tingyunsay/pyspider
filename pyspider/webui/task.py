#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-07-16 15:30:57

import socket
from flask import abort, render_template, request, json

from pyspider.libs import utils
from .app import app
from six import iteritems, itervalues
from flask import session, redirect, url_for


task_fields = ['taskid','project','url','status','schedule','fetch','process','track','lastcrawltime','updatetime']

#其url格式为：127.0.0.1:5000/task/wangyiyun_album:9e1fb2475efc3237e31ef733cf29f179 ， 使用:分隔
#这使得不同项目（以名字为主键）中可以使用相同的id值，后续看它是如何生成id值的
@app.route('/task/<taskid>')
def task(taskid):
    if ':' not in taskid:
        abort(400)
    project, taskid = taskid.split(':', 1)

    taskdb = app.config['taskdb']
    task = taskdb.get_task(project, taskid)

    if not task:
        abort(404)
    resultdb = app.config['resultdb']
    result = {}
    if resultdb:
        result = resultdb.get(project, taskid)

    return render_template("task.html", task=task, json=json, result=result,
                           status_to_string=app.config['taskdb'].status_to_string)


@app.route('/task/<taskid>.json')
def task_in_json(taskid):
    if ':' not in taskid:
        return json.jsonify({'code': 400, 'error': 'bad project:task_id format'})
    project, taskid = taskid.split(':', 1)

    taskdb = app.config['taskdb']
    task = taskdb.get_task(project, taskid)

    if not task:
        return json.jsonify({'code': 404, 'error': 'not found'})
    task['status_string'] = app.config['taskdb'].status_to_string(task['status'])
    return json.jsonify(task)


@app.route('/tasks')
def tasks():
    rpc = app.config['scheduler_rpc']
    taskdb = app.config['taskdb']
    project = request.args.get('project', "")
    limit = int(request.args.get('limit', 100))

    try:
        updatetime_tasks = rpc.get_active_tasks(project, limit)
    except socket.error as e:
        app.logger.warning('connect to scheduler rpc error: %r', e)
        return 'connect to scheduler error', 502
    tasks = {}
    result = []
    for updatetime, task in sorted(updatetime_tasks, key=lambda x: x[0]):
        key = '%(project)s:%(taskid)s' % task
        task['updatetime'] = updatetime
        if key in tasks and tasks[key].get('status', None) != taskdb.ACTIVE:
            result.append(tasks[key])
        tasks[key] = task
    result.extend(tasks.values())

    return render_template(
        "tasks.html",
        tasks=result,
        status_to_string=taskdb.status_to_string
    )

@app.route('/diff_tasks')
def diff_tasks():
    rpc = app.config['scheduler_rpc']
    taskdb = app.config['taskdb']
    project = request.args.get('project', "")
    status = request.args.get('status', "").encode('utf8')  #接受为unicode，encode后为一个str
    limit = int(request.args.get('limit', 100))

    Failed_tasks = taskdb.load_tasks_limit(status,project,task_fields,limit)
    Failed_tasks = tasks_format(Failed_tasks)
    tasks = {}
    result = []
    for updatetime, task in sorted(Failed_tasks, key=lambda x: x[0]):
        key = '%(project)s:%(taskid)s' % task
        task['updatetime'] = updatetime
        if key in tasks and tasks[key].get('status', None) == status:
            result.append(tasks[key])
        tasks[key] = task
    result.extend(tasks.values())

    if status == "3":
        return render_template(
            "faileds.html",
            tasks=result,
            status_to_string=taskdb.status_to_string
        )
    else:
        return render_template(
            "tasks.html",
            tasks=result,
            status_to_string=taskdb.status_to_string
        )

@app.route('/retry/<project>')
def retry(project):
    rpc = app.config['scheduler_rpc']
    taskdb = app.config['taskdb']
    project = project
    taskid = request.args.get('taskid',"").encode('utf8')
    #单条taskid
    if isinstance(taskid,str):
        task = taskdb.get_task(project,taskid)
        task['status'] = 1
        if task['schedule'].has_key('retried'):
            if task['schedule']['retried'] == 3:
                task['schedule']['retried'] = 2
        rpc.retry_task(task)    #数据中将其状态更改，status改为1（ACTIVE）；重试次数改成2（若再失败即又变成3）,即不会违背原先的规则
                                #并且同时将taskid强制put到当前project的task_queue中，强制更新调度状态
        task = taskdb.get_task(project, taskid, task_fields)
        if not task:
            abort(404)
        resultdb = app.config['resultdb']
        result = {}
        if resultdb:
            result = resultdb.get(project, taskid)
        taskid = "%s:%s"%(project,taskid)
        return redirect(url_for('task',taskid = taskid))
        #return render_template("task.html", task=task, json=json, result=result,
        #                       status_to_string=app.config['taskdb'].status_to_string)

@app.route('/retry_all/<project>')
def retry_all(project):
    rpc = app.config['scheduler_rpc']
    taskdb = app.config['taskdb']
    project = project
    status = 3
    failed_tasks = taskdb.load_tasks(status,project,task_fields)
    for task in failed_tasks:
        task['status'] = 1
        if task['schedule'].has_key('retried'):
            if task['schedule']['retried'] == 3:
                task['schedule']['retried'] = 2
        ret = rpc.retry_task(task)
    return json.jsonify({'code': 200, 'msg': 'Total retry tasks are %s'%str(len(list(failed_tasks)))})


@app.route('/active_tasks')
def active_tasks():
    rpc = app.config['scheduler_rpc']
    taskdb = app.config['taskdb']
    project = request.args.get('project', "")
    limit = int(request.args.get('limit', 100))

    try:
        tasks = rpc.get_active_tasks(project, limit)
    except socket.error as e:
        app.logger.warning('connect to scheduler rpc error: %r', e)
        return '{}', 502, {'Content-Type': 'application/json'}

    result = []
    for updatetime, task in tasks:
        task['updatetime'] = updatetime
        task['updatetime_text'] = utils.format_date(updatetime)
        if 'status' in task:
            task['status_text'] = taskdb.status_to_string(task['status'])
        result.append(task)

    return json.dumps(result), 200, {'Content-Type': 'application/json'}

app.template_filter('format_date')(utils.format_date)

def tasks_format(failed_tasks = None):
    Failed_tasks = []
    for task in failed_tasks:
        temp = []
        temp.append(task.get('updatetime'))
        temp.append(task)
        Failed_tasks.append(temp)
    return json.loads(json.dumps(Failed_tasks))