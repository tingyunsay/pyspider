#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Binux<i@binux.me>
#         http://binux.me
# Created on 2014-02-23 00:19:06


import sys
import time
import socket
import inspect
import datetime
import traceback
import re
from flask import render_template, request, json

try:
    import flask_login as login
except ImportError:
    from flask.ext import login

#查看建立代码的模板
from pyspider.libs import utils, sample_handler, dataurl
from pyspider.libs.response import rebuild_response
from pyspider.processor.project_module import ProjectManager, ProjectFinder
from .app import app
spidermanager_fields = ['name', 'role', 'group' , 'info']
groupinfo_fields = ['gname','creater','projects','createtime','updatetime']

default_task = {
    'taskid': 'data:,on_start',
    'project': '',
    'url': 'data:,on_start',
    'process': {
        'callback': 'on_start',
    },
}
default_script = inspect.getsource(sample_handler)


@app.route('/debug/<project>', methods=['GET', 'POST'])
def debug(project):
    cas_info = request.form.to_dict()
    project_name = request.args.to_dict()
    cas_info.update(project_name)
    must_info = eval(cas_info.get('project_info')) if cas_info.get('project_info') else None
    projectdb = app.config['projectdb']
    if not projectdb.verify_project_name(project):
        return 'project name is not allowed!', 400
    info = projectdb.get(project, fields=['name', 'script'])
    if info:
        script = info['script']
    else:
        script = (default_script
                  .replace('__DATE__', datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                  .replace('__PROJECT_NAME__', project)
                  .replace('__START_URL__', request.values.get('start-urls') or '__START_URL__')
                  .replace('__Group__', request.values.get('group') or '__START_URL__'))

    taskid = request.args.get('taskid')
    if taskid:
        taskdb = app.config['taskdb']
        task = taskdb.get_task(
            project, taskid, ['taskid', 'project', 'url', 'fetch', 'process'])
    else:
        task = default_task

    default_task['project'] = project
    return render_template("debug.html", task=task, script=script,cas_info = cas_info, project_name=project,cas_user_name = cas_info.get('user_name'),must_info=must_info)


@app.before_first_request
def enable_projects_import():
    sys.meta_path.append(ProjectFinder(app.config['projectdb']))


@app.route('/debug/<project>/run', methods=['POST', ])
def run(project):
    start_time = time.time()
    try:
        task = utils.decode_unicode_obj(json.loads(request.form['task']))
    except Exception:
        result = {
            'fetch_result': "",
            'logs': u'task json error',
            'follows': [],
            'messages': [],
            'result': None,
            'time': time.time() - start_time,
        }
        return json.dumps(utils.unicode_obj(result)), \
            200, {'Content-Type': 'application/json'}

    project_info = {
        'name': project,
        'status': 'DEBUG',
        'script': request.form['script'],
    }

    if request.form.get('webdav_mode') == 'true':
        projectdb = app.config['projectdb']
        info = projectdb.get(project, fields=['name', 'script'])
        if not info:
            result = {
                'fetch_result': "",
                'logs': u' in wevdav mode, cannot load script',
                'follows': [],
                'messages': [],
                'result': None,
                'time': time.time() - start_time,
            }
            return json.dumps(utils.unicode_obj(result)), \
                200, {'Content-Type': 'application/json'}
        project_info['script'] = info['script']

    fetch_result = {}
    try:
        module = ProjectManager.build_module(project_info, {
            'debugger': True,
            'process_time_limit': app.config['process_time_limit'],
        })

        # The code below is to mock the behavior that crawl_config been joined when selected by scheduler.
        # but to have a better view of joined tasks, it has been done in BaseHandler.crawl when `is_debugger is True`
        # crawl_config = module['instance'].crawl_config
        # task = module['instance'].task_join_crawl_config(task, crawl_config)

        fetch_result = app.config['fetch'](task)
        response = rebuild_response(fetch_result)

        ret = module['instance'].run_task(module['module'], task, response)
    except Exception:
        type, value, tb = sys.exc_info()
        tb = utils.hide_me(tb, globals())
        logs = ''.join(traceback.format_exception(type, value, tb))
        result = {
            'fetch_result': fetch_result,
            'logs': logs,
            'follows': [],
            'messages': [],
            'result': None,
            'time': time.time() - start_time,
        }
    else:
        result = {
            'fetch_result': fetch_result,
            'logs': ret.logstr(),
            'follows': ret.follows,
            'messages': ret.messages,
            'result': ret.result,
            'time': time.time() - start_time,
        }
        result['fetch_result']['content'] = response.text
        if (response.headers.get('content-type', '').startswith('image')):
            result['fetch_result']['dataurl'] = dataurl.encode(
                response.content, response.headers['content-type'])

    try:
        # binary data can't encode to JSON, encode result as unicode obj
        # before send it to frontend
        return json.dumps(utils.unicode_obj(result)), 200, {'Content-Type': 'application/json'}
    except Exception:
        type, value, tb = sys.exc_info()
        tb = utils.hide_me(tb, globals())
        logs = ''.join(traceback.format_exception(type, value, tb))
        result = {
            'fetch_result': "",
            'logs': logs,
            'follows': [],
            'messages': [],
            'result': None,
            'time': time.time() - start_time,
        }
        return json.dumps(utils.unicode_obj(result)), 200, {'Content-Type': 'application/json'}


@app.route('/debug/<project>/save', methods=['POST', ])
def save(project):
    group_info = eval(request.form.to_dict().get('group_info'))
    projectdb = app.config['projectdb']
    groupinfodb = app.config['groupinfodb']
    if not projectdb.verify_project_name(project):
        return 'project name is not allowed!', 400
    script = request.form['script']
    project_info = projectdb.get(project, fields=['name', 'status', 'group'])
    if project_info and 'lock' in projectdb.split_group(project_info.get('group')) \
            and not login.current_user.is_active():
        return app.login_response
    gname = group_info.get('group')
    project_name = group_info.get('project-name')
    belong = group_info.get('belong')
    #查询组，若这个组之前不存在，说明是新建的组（若存在，则只更新组包含的项目信息，不会更新创建者和创建时间）
    exists = groupinfodb.get(gname,groupinfo_fields) if groupinfodb.get(gname,groupinfo_fields) else None
    if exists:
        #更新修改时间和projects（先取出，再附加成一个值）
        projects = eval(exists.get('projects'))
        projects.append(project_name) if isinstance(projects,list) and project_name not in projects else None
        info = {
            'projects':str(projects),
        }
        groupinfodb.update(gname,info)
    else:
        #初始化
        projects = []
        projects.append(project_name)
        info = {
            'gname':gname,
            'creater':group_info.get('user_name'),
            'projects':str(projects),
            'createtime':time.time(),
        }
        groupinfodb.insert(gname,info)

        #点击save，当组为新的组时候，更新spidermanagerdb，将新的组加到创建人所拥有的组中 update （其他人必须在管理台被加入才能看到group中的可见项）
        spidermanagerdb = app.config['spidermanagerdb']
        name = group_info.get('user_name')
        person_info = spidermanagerdb.get(name,spidermanager_fields)
        in_group = eval(person_info.get('group')) if person_info.get('group') else None
        in_group.append(gname)
        manager_info = {
            'group':str(in_group)
        }
        spidermanagerdb.update(name,manager_info)

    #belong初始化，只有在创建的时候才会存在，之后只能由 创建者/管理员 在权限管理中添加，之后的编辑项目，不会更改belong
    if belong:
        if project_info:
            info = {
                'script': script,
                'group': gname,
                'belong': belong,
            }
            if project_info.get('status') in ('DEBUG', 'RUNNING', ):
                info['status'] = 'CHECKING'
            projectdb.update(project, info)
        else:
            info = {
                'name': project,
                'script': script,
                'status': 'TODO',
                'rate': app.config.get('max_rate', 1),
                'burst': app.config.get('max_burst', 3),
                'group': gname,
                'belong': belong,
            }
            projectdb.insert(project, info)
    else:
        if project_info:
            info = {
                'script': script,
                'group': gname,
            }
            if project_info.get('status') in ('DEBUG', 'RUNNING', ):
                info['status'] = 'CHECKING'
            projectdb.update(project, info)
        else:
            info = {
                'name': project,
                'script': script,
                'status': 'TODO',
                'rate': app.config.get('max_rate', 1),
                'burst': app.config.get('max_burst', 3),
                'group': gname,
            }
            projectdb.insert(project, info)

    rpc = app.config['scheduler_rpc']
    if rpc is not None:
        try:
            rpc.update_project()
        except socket.error as e:
            app.logger.warning('connect to scheduler rpc error: %r', e)
            return 'rpc error', 200

    return 'ok', 200


@app.route('/debug/<project>/get')
def get_script(project):
    projectdb = app.config['projectdb']
    if not projectdb.verify_project_name(project):
        return 'project name is not allowed!', 400
    info = projectdb.get(project, fields=['name', 'script'])
    return json.dumps(utils.unicode_obj(info)), \
        200, {'Content-Type': 'application/json'}


@app.route('/blank.html')
def blank_html():
    return ""
