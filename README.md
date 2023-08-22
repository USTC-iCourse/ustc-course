# XJ课评

XJ课评，fork自[USTC评课社区](https://github.com/USTC-iCourse/ustc-course)。

## 特色功能：
在USTC评课社区源码的基础上做了些许修改：
* 支持OAuth，也即只要你在xjtu.live登录，点击评课社区的登录键即可一键登录。
  
-> 为什么多此一举非要点一下登录按键呢？
  
-> 因为我本来是想开发Discourse插件，将本站的一个类别打造成评课社区。无奈 Ruby+Ember.js 的技术栈没有基于USTC评课社区代码 Python+Flask+Plotly 开发效率高。至于后面是否要切换成Discourse插件的方式还需要斟酌。

* 区间分数可视化，以及显示均分、最高分、最低分。
  
-> 当然，现在这个图表做得还是很粗糙的，后续需要改进配色、文字位置等等细节。
![Vis|690x472, 75%](https://xjtu.live/uploads/default/original/2X/4/4976829c6e9b1ad583c4f934b936c44c043a34dd.webp)

* (Ongoing) 使用 NLP 对现有评论数据进行情感分析和理解，以对“ 课程难度、作业多少、 给分好坏、收获大小”等 目前**空缺的**指标进行定性。
  
-> 不如把USTC评课社区的数据爬下来，训练一个情感/语义分析模型

更新：

* 完善课程的自身属性：课程编号、开课单位、任课教师、学分（学时）、选修课板块类别、课程简介。去除了一些无用评价。

-> 可以和现有的“导师信息”有机地结合起来。

* (Ongoing) 调`gpt-3.5-turbo-16k`接口summarize某个课程/教学班的评论
  
## 交大門上的相关话题
https://xjtu.live/t/topic/4919
https://xjtu.men/t/topic/4880/
https://xjtu.men/t/topic/4881/

## 安装

安装此系统前，请首先安装：

1. Python 3
2. MySQL 5.5+
3. Nginx


### 配置和创建数据库

在 MySQL 配置文件（如 ```/etc/mysql/my.cnf```）末尾加入如下几行，重启数据库（如 ```service mysql restart```）。这几行是设置数据库使用
utf8mb4 作为默认连接字符集和存储字符集，以免出现乱码，并且支持 emoji。

```
[client]
default-character-set=utf8mb4
[mysql]
default-character-set=utf8mb4
[mysqld]
collation-server = utf8mb4_unicode_ci

init-connect='SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci'
character-set-server = utf8mb4
```

然后创建数据库：```mysql -u root -p``` 进入 mysql 控制台。

```CREATE DATABASE icourse;```
创建数据库成功的话，会提示 Query OK...

对于 MySQL 版本 < 8.0:
```GRANT ALL ON icourse.* to 'ustc_course'@'localhost' identified by 'ustc_course';```

对于 MySQL 版本 >= 8.0:

```
CREATE USER 'ustc_course'@'localhost' identified by 'ustc_course';
GRANT ALL ON icourse.* to 'ustc_course'@'localhost';
```

这一步是创建数据库用户 ustc_course 并授予访问 icourse 数据库的权限。该用户密码是 ustc_course，生产环境上请换用强密码。

### Python 依赖及系统设置

安装 Python 依赖库：```pip3 install -r requirements.txt```。其中 ```requirements.txt``` 是版本库根目录下的文件。

如果 pip3 过程中出现错误，可能是缺少编译这些 Python 库所需的依赖。在 Ubuntu/Debian
系统上，可以 ```apt-get install python3-dev libxslt1-dev libxml2-dev libmysqlclient-dev```

修改系统配置文件 ```config/default.py```。

* ```DEBUG``` 开关用于标识是否启用调试模式。
* ```SERVER_NAME``` 设置服务器域名，若域名未确定则可设为 None。
* ```SECRET_KEY``` 是用于验证 cookie 的加密密钥，填入一个随机字符串。
* ```SQLALCHEMY_DATABASE_URI```
  是数据库连接信息，格式为 ```mysql+mysqldb://用户名:密码@数据库地址/数据库名?charset=utf8mb4```。
* ```MAIL_*``` 是外发邮件的发件人信息。
* ```UPLOAD_FOLDER``` 是头像、用户上传的附件等存储的地方。在生产服务器上需要有足够大的剩余空间，并定期备份。
* ```MAX_CONTENT_LENGTH``` 是上传文件的最大大小。

初始化数据库：```python -m tests.init_db```，如果没有报错就初始化成功了。

### 配置 Nginx

如果您已经安装了其他 Web 服务器（如 Apache）或者已经有 Nginx 配置，请参考 ```tests/conf/nginx-config``` 来修改。

如果是刚刚安装的 nginx，可以直接使用如下配置文件：

1. ```cp tests/conf/nginx-config /etc/nginx/sites-available/default```
2. ```sudo service mysql restart```

运行 ```./run.py```，访问 ```http://localhost``` 即可以 debug 模式开始运行此系统。

如果出现问题，请首先看 ```./run.py``` 的终端有无输出，如果没有，则是 nginx 的问题，可以访问 ```http://localhost:8080```
来测试；如果 Python 有报异常，则可根据异常信息排查。

在生产服务器上，需要把 nginx 配置文件（```/etc/nginx/sites-available/default```）中的 8080 替换成
3010，把 ```config/default.py``` 和 ```run.py``` 中的 ```DEBUG=True``` 改为 ```DEBUG=False```。

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
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
