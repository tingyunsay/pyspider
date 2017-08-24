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
from flask import session, redirect, url_for
from flask_cas import CAS, login_required
#from flask.ext.cas import login
#from flask.ext.cas import logout
from flask_cas import login
from flask_cas import logout
#app = Flask("hong")
cas = CAS(app)
#app.config['CAS_SERVER'] = 'http://127.0.0.1:8080/cas-server-webapp-4.0.0/'
app.config['CAS_SERVER'] = 'http://cas.taihenw.com/'
app.config['CAS_AFTER_LOGIN'] = '/'
app.config['SECRET_KEY'] = 'guess'
#设定logout默认指向页面
app.config['CAS_AFTER_LOGOUT'] = "http://localhost:5000"


index_fields = ['name', 'group', 'status', 'comments', 'rate', 'burst', 'updatetime','belong']
spidermanager_fields = ['name', 'role', 'group' , 'info']
groupinfo_fields = ['gname','creater','projects','createtime','updatetime']

@app.route('/old_index/<user_name>', methods=['POST','GET'])
@login_required
def old_index(user_name):
    target = request.args.to_dict()
    #获取需要传递的数据
    person_info = eval(target.get('group-info').encode('utf8')) if target.get('group-info') else None
    must_info = person_info
    role_info = person_info.get('role') if person_info else None
    #获取需要显示的 -- 相关group的数据
    name = user_name
    spidermanagerdb = app.config['spidermanagerdb']
    person_info = spidermanagerdb.get(name , fields=spidermanager_fields)
    group_info = person_info.get('group')
    total_group = eval(group_info)
    #查询所有人可见的项目，后续update到所属的group的项目中
    # (若没有所属group，只显示all
    # {并且对非创建者，剔除了为private的项目，除非cas name和creater相同才显示})
    projectdb = app.config['projectdb']
    belong_all_project = projectdb.get_belong('all',index_fields)
    if belong_all_project:
        if role_info in ["Admin","RD"] and target.get('target') == "project":
            all_projects = []
            #过滤掉private类型的项目，需要去groupinfodb中查询creater信息
            if total_group:
                add_cas_info = []       #最终的数据
                own_group = []          #对所属group全部显示
                for group in total_group:
                    groupinfodb = app.config['groupinfodb']
                    craeter_name = groupinfodb.get(group).get('creater') if groupinfodb.get(group) else None
                    if craeter_name == cas.username:
                        own_group.append(group)
                other_group = list(set(total_group) - set(own_group))           #对其他group，只显示分类为group的项目（剔除private）
                if own_group:
                    for group in own_group:
                        group_project = list(projectdb.get_group(group))
                        add_cas_info += group_project
                if other_group:
                    for group in other_group:
                        group_private = []
                        #获取组内为private的项目名字 A
                        for i in projectdb.get_group_private(group):
                            group_private.append(i.get('name'))
                        group_project = []
                        #获取组内所有的项目名字
                        for i in projectdb.get_group(group):
                            group_project.append(i.get('name'))
                        #取得两个list的差集 B ， 即在B中有，但在A中没有的
                        group_diff = list(set(group_project) - set(group_private))
                        for project in group_diff:
                            add_cas_info.append(projectdb.get(project))     #get返回的是单条dict数据，不能相加
                #加上所属为all的项目
                #对结果数据，附加cas信息，需要使用
                add_cas_info += list(belong_all_project)
                for info in add_cas_info:
                    if info:
                        info['cas_user_name'] = cas.username
                        info['must'] = str(must_info)
                        all_projects.append(info)
                    else:
                        pass
                projects = sorted(all_projects,key=lambda k: (0 if k['group'] else 1, k['group'] or '', k['name']))
                #projects = sorted(projectdb.get_all(fields=index_fields),
                #                  key=lambda k: (0 if k['group'] else 1, k['group'] or '', k['name']))
                return render_template("index.html", projects=projects , info = cas ,group = eval(person_info.get('group')),must_info=must_info)
            else:
                all_projects = []
                for info in belong_all_project:
                    if info:
                        # 附加cas信息
                        info['cas_user_name'] = cas.username
                        info['must'] = str(must_info)
                        all_projects.append(info)
                    else:
                        pass
                projects = sorted(all_projects, key=lambda k: (0 if k['group'] else 1, k['group'] or '', k['name']))
                return render_template("index.html", projects=projects, info=cas,group=None,must_info=must_info)
        elif role_info in ["Admin","PM"] and target.get('target') == "export":
            #PM所在组的所有表单
            all_projects = []
            for group in total_group:
                # 取出来的值是一个generator
                all_info = projectdb.get_group(group)
                for info in all_info:
                    all_projects.append([info.get('group'),info.get('name')]) if info else None
            #检索出可导出的数据表
            resultdb = app.config['resultdb']
            #所有--- [组,项目,结果条目数]，超过一定部分的限定导出，较少的可以导出
            all_form = []
            for project in all_projects:
                all_form.append([project[0],project[1],resultdb.count(project[1])])
            return render_template("export.html",all_form = all_form)
        else:
            return "invalid error，please connect Administer！",404
    else:
        all_projects = []
        warning = "It looks like you did not join any group OR there is't any project belongs to all user!"
        projects = projects = sorted(all_projects,key=lambda k: (0 if k['group'] else 1, k['group'] or '', k['name']))
        return render_template("index.html", projects=projects , info = cas , warning = warning)

@app.route('/')
@login_required
def index():
    name = cas.username
    spidermanagerdb = app.config['spidermanagerdb']
    person_info = spidermanagerdb.get(name , fields=spidermanager_fields)
    role = person_info.get('role') if person_info else None
    return render_template("control.html", info = cas , role = role , person_info = person_info)


@app.route('/check_cas/<user_name>' , methods=['POST','GET'])
@login_required
def check_cas(user_name):
    name = user_name
    #name = request.form.to_dict()['name']
    spidermanagerdb = app.config['spidermanagerdb']
    #get_all只需要选择提取的字段，返回一个生成器，较为简单
    #person_info = spidermanagerdb.get_all(fields=('name', 'group'))
    person_info = spidermanagerdb.get(name , fields=spidermanager_fields)
    if person_info:
        if person_info['role'] == 'Admin':
            all_info = sorted(spidermanagerdb.get_all(fields=spidermanager_fields))
            #返回所有组的信息，供前台添加用户时选择
            groupinfodb = app.config['groupinfodb']
            all_group_info = groupinfodb.get_all(groupinfo_fields)
            group_names = []
            for i in all_group_info:
                group_names.append(i.get('gname')) if i.get('gname') else None
            return render_template("manager.html",all_info = all_info ,cas_user = name,group_names=group_names )
        elif person_info['role'] == "RD":
            right = person_info.get('role')
            return "Your authority is {right} , it's not allow!".format(right=right),400
        elif person_info['role'] == "PM":
            right = person_info.get('role')
            return "Your authority is {right} , it's not allow!".format(right=right), 400
        else:
            return "Unkonw Error，未知错误，请联系管理员！", 404, {'Content-Type': 'application/json'}
    else:
    	return "Invid Person，用户不存在，请注册！",403,{'Content-Type': 'application/json'}

@app.route('/group', methods=['POST','GET'])
@login_required
def group():
    target = request.args.to_dict()
    person_info = eval(target.get('group-info').encode('utf8')) if target.get('group-info') else None
    login_name = cas.username
    groupinfodb = app.config['groupinfodb']
    #查询你创建的组，创建者是根据cas接入的注册人name，在spidermanagerdb中是主键（不会重复）
    total_group = groupinfodb.get_group(login_name,fields=groupinfo_fields)
    own_group = []
    if total_group:
        for group in total_group:
            own_group.append(group.get('gname'))
    #找到所创建的组，去projectdb中查询所有的项目
    projectdb = app.config['projectdb']
    all_projects = []
    for group in own_group:
        all_projects += list(projectdb.get_group(group))
    projects = sorted(all_projects, key=lambda k: (0 if k['group'] else 1, k['group'] or '', k['name']))
    return render_template("group.html", projects=projects,info=cas)
    #return own_group

#限定使用post
@app.route('/update_right' , methods=['POST',])
@login_required
def update_right():
    right_info = request.form.to_dict()
    spidermanagerdb = app.config['spidermanagerdb']
    if not spidermanagerdb.verify_project_name(right_info.get('name')):
        return 'manager name is not allowed!', 400

    all_name = spidermanagerdb.get_all(fields=['name'])
    for i in all_name:
        if right_info.get('name') == i['name']:
            return '用户已存在，请编辑!', 400
        else:
            #将前台传过来的数据插入（验证后续再做）
            info = {
                'name': right_info.get('name'),
                'role': right_info.get('role'),
                'group': str([right_info.get('group')])
            }
            spidermanagerdb.insert(info)
            #res =  json.dumps({"res":['添加用户成功!',200]})
            return redirect(url_for('check_cas', user_name=right_info.get('cas_user') ))



#限定使用post
@app.route('/edit' , methods=['POST',])
@login_required
def edit():
    if request.method == 'POST':
        total_info = request.form.to_dict()
        edit_info = total_info.copy()
        #更改前端传递过来的group成list类型，再转换成str类型
        group_str = edit_info.get('group')
        edit_info['group'] = str(group_str[:-1].split(','))
        spidermanagerdb = app.config['spidermanagerdb']
        all_info = spidermanagerdb.get_all(fields=spidermanager_fields)
        all_name = []
        for x in all_info:
            all_name.append(x.get('name'))
        if edit_info.get('name') in all_name:
            spidermanagerdb.update(edit_info.get('name'),edit_info)
            return json.dumps({ 'status' : 302, 'location' : "/check_cas/"+cas.username })
            #return redirect(url_for('check_cas', user_name=cas.username))
        else:
            return '未知错误!', 400
    else:
        return '非法请求!', 400


@app.route('/edit_page' , methods=['POST',])
@login_required
def edit_page():
    if request.method == 'POST':
        edit_info = request.form.to_dict()
        edit_name = edit_info.get('edit_name')
        spidermanagerdb = app.config['spidermanagerdb']
        #查询用户现有信息，展示
        all_info = spidermanagerdb.get(edit_name , fields=spidermanager_fields)
        cas_name = cas.username
        all_info['cas_user_name'] = cas_name
        #查询还能添加的组信息（全部组信息，供添加）
        groupinfodb = app.config['groupinfodb']
        all_group = []
        for group in groupinfodb.get_all(groupinfo_fields):
            all_group.append(group.get('gname'))
        return render_template("edit_page.html",info = all_info,all_group=all_group)

    else:
        return '非法请求!', 400

#限定使用post
@app.route('/delete' , methods=['POST',])
@login_required
def delete():
    right_info = request.form.to_dict()
    spidermanagerdb = app.config['spidermanagerdb']
    cas_user_name = cas.username
    drop_name = right_info.get('delete_name')
    if drop_name:
        spidermanagerdb.drop(drop_name)
        #return redirect(url_for('check_cas', user_name=cas_user_name))
        return json.dumps({'status': 200, 'location': "/check_cas/" + cas.username})
    else:
        #return "未知错误，请联系管理员！", 404, {'Content-Type': 'application/json'}
        return json.dumps({'status': 400, 'location': "/check_cas/" + cas.username})


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

    if name not in ('group', 'status', 'rate' , 'belong'):
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


#添加jinja2过滤器，进行正则匹配
import re
@app.template_filter('get_int')
def get_int(l):
    return int(l)

