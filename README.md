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
启动完之后可以登录http://127.0.0.1:8080/manager/status 查看服务器的状态

2).修改用户账号密码
```python
#以下是允许登录的用户账号密码，可配置多个
vi /home/cas_docking/Tomcat/tomcat-8.5.16/webapps/cas/WEB-INF/deployerConfigContext.xml

#找到其中<property name="users">这一部分，可添加多个
<map>
     <entry key="tingyun" value="tingyun"/>
</map>
```
后续登录pyspider时候需要使用到当前位置设定的账号密码

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

3.设定phantomjs
```python
#安装依赖
apt-get install build-essential g++ flex bison gperf ruby perl libsqlite3-dev libfontconfig1-dev libicu-dev libfreetype6 libssl-dev libpng-dev libjpeg-dev python libx11-dev libxext-dev

#从镜像上下载最新版本的phantomjs，官网太慢了
http://npm.taobao.org/dist/phantomjs/

#解压安装
tar -jxvf phantomjs-2.1.1-linux-x86_64.tar.bz2
cd phantomjs-2.1.1-linux-x86_64
cp ./bin/phantomjs  /usr/local/bin/

#输入以下命令检测是否安装成功
phantomjs -v

#安装相关依赖包
pip install selenium
pip install logging
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

