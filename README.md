# USTC 评课社区

USTC 评课社区是使用 Python 3 + Flask + SQLAlchemy 开发的 Web 系统。

## 安装

安装此系统前，请首先安装：

1. Python 3
2. MySQL 5.5+
3. Nginx

### 配置和创建数据库

在 MySQL 配置文件（如 ```/etc/mysql/my.cnf```）末尾加入如下几行，重启数据库（如 ```service mysql restart```）。这几行是设置数据库使用 UTF-8 作为默认连接字符集和存储字符集，以免出现乱码。

```
[client]
default-character-set=utf8
[mysql]
default-character-set=utf8
[mysqld]
collation-server = utf8_unicode_ci
init-connect='SET NAMES utf8'
character-set-server = utf8
```

然后创建数据库：```mysql -u root -p``` 进入 mysql 控制台。

```CREATE DATABASE icourse;```
创建数据库成功的话，会提示 Query OK...

```GRANT ALL ON icourse.* to 'ustc_course'@'localhost' identified by 'ustc_course';```
这一步是创建数据库用户 ustc_course 并授予访问 icourse 数据库的权限。该用户密码是 ustc_course，生产环境上请换用强密码。

### Python 依赖及系统设置

安装 Python 依赖库：```pip3 install -r requirements.txt```。其中 ```requirements.txt``` 是版本库根目录下的文件。

如果 pip3 过程中出现错误，可能是缺少编译这些 Python 库所需的依赖。在 Ubuntu/Debian 系统上，可以 ```apt-get install python3-dev libxslt1-dev libxml2-dev libmysqlclient-dev```

修改系统配置文件 ```config/default.py```。

* ```DEBUG``` 开关用于标识是否启用调试模式。
* ```SERVER_NAME``` 设置服务器域名，若域名未确定则可设为 None。
* ```SECRET_KEY``` 是用于验证 cookie 的加密密钥，填入一个随机字符串。
* ```SQLALCHEMY_DATABASE_URI``` 是数据库连接信息，格式为 ```mysql+mysqldb://用户名:密码@数据库地址/数据库名?charset=utf8```
* ```MAIL_*``` 是外发邮件的发件人信息。
* ```UPLOAD_FOLDER``` 是头像、用户上传的附件等存储的地方。在生产服务器上需要有足够大的剩余空间，并定期备份。
* ```MAX_CONTENT_LENGTH``` 是上传文件的最大大小。

初始化数据库：```./tests/init_db.py``` 如果没有报错就初始化成功了。

### 配置 Nginx

如果您已经安装了其他 Web 服务器（如 Apache）或者已经有 Nginx 配置，请参考 ```tests/conf/nginx-config``` 来修改。

如果是刚刚安装的 nginx，可以直接使用如下配置文件：

1. ```cp tests/conf/nginx-config /etc/nginx/sites-available/default```
2. ```sudo service mysql restart```

运行 ```./run.py```，访问 ```http://localhost``` 即可以 debug 模式开始运行此系统。

如果出现问题，请首先看 ```./run.py``` 的终端有无输出，如果没有，则是 nginx 的问题，可以访问 ```http://localhost:8080``` 来测试；如果 Python 有报异常，则可根据异常信息排查。

在生产服务器上，需要把 nginx 配置文件（```/etc/nginx/sites-available/default```）中的 8080 替换成 3000，把 ```config/default.py``` 和 ```run.py``` 中的 ```DEBUG=True``` 改为 ```DEBUG=False```。

## 开发

请首先学习 Flask + SQLAlchemy 的 Web 开发。系统的主要文件在 app 目录下，

* forms 是表单验证
* models 是 ORM 类
* static 是静态文件，由 nginx 直接返回给用户
* templates 是页面模板
* views 是各种功能的业务逻辑
* utils.py 是工具函数

## License

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
