pyspider的基本使用请移步:https://github.com/binux/pyspider/blob/master/README.md

## 添加部分自定义功能
1.需要接入cas，添加用户管理功能
2.任务分组，权限管理
3.单个任务重试功能（暂时不支持批量）
4.修改页面ui显示，能显示成功/失败/调度中 三种情况的任务
5.添加简单的检索

## 需要自定义安装的环境

### 安装cas相关环境
1.安装依赖库
```python
git clone https://github.com/cameronbwhite/Flask-CAS.git

cd Flask-CAS/

python setup.py install
```

2.安装tomcat并设定账号密码
下载：https://tomcat.apache.org/download-80.cgi
随便下个版本，解压

1).修改tomcat管理员账号密码
```python
vi  ./home/cas_wocking/Tomcat/tomcat-8.5.16/conf/tomcat-users.xml

#找到如下格式的一行，修改管理员账号密码
<user username="tingyun" password="tingyun" roles="manager-gui,admin-gui"/>
```
2).修改用户账号密码
```python
#以下是允许登录的用户账号密码，可配置多个
vi /home/cas_docking/Tomcat/tomcat-8.5.16/webapps/cas/WEB-INF/deployerConfigContext.xml

#找到其中<property name="users">这一部分，可添加多个
<map>
     <entry key="tingyun" value="tingyun"/>
</map>
```
3).启动tomcat
```python
sh  /home/cas_docking/Tomcat/tomcat-8.5.16/bin/startup.sh
```

### 启动依赖配置
1.启动redis
```python
vi /etc/redis.conf

#将bind 127.0.0.1注释掉，换成如下
bind 0.0.0.0

#启动
redis-server /etc/redis.conf
```

2.mysql设定远程访问
```python
grant all PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'tingyun' WITH GRANT OPTION;

flush privileges;
```

### 使用本项目代码
```python
git clone https://github.com/tingyunsay/pyspider.git
```
配置好config.json文件

运行
```python
./runc.py -c config.json
```

