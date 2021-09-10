# SHUASR
Shanghai University Auto SelfReport

Ver.21.09.10

上海大学健康之路自动上报（卷王专用）

项目地址：<https://github.com/panghaibin/shuasr>


## 特色
- 支持多种消息发送接口，适合一人为多人上报的情况，上报结果仅发送给一人。使用前请前往对应官网申请 Token。
  
- 自动获取上次填报信息进行上报

[comment]: <> (- 兼容每日两报，健康之路页显示两报的视为在校，需设置所在校区。（未充分测试）)

- 支持 ~~卷王~~ 抢排名模式：

    ![抢排名](./img/rank.jpg)

## 使用
### 下载/更新
```shell
git clone https://github.com/panghaibin/shuasr.git
cd shuasr
# 更新
git pull
```

### 安装依赖
```shell
pip3 install -r requirements.txt
```

### 添加用户，设置消息发送API

目前支持以下消息推送服务：

方糖气球 https://sct.ftqq.com/

推送加 https://pushplus.hxtrip.com/

#### 方法一：命令行下添加
```shell
# 添加用户
# 如需修改已添加用户的密码，再次执行并输入相同学号即可
python3 main.py add
# 设置消息发送API
python3 main.py send
```

[comment]: <> (**请注意已离校每日一报的，校区一项务必录入0** ，仍在校每日两报的须指定校区（见运行时提示）。)

#### 方法二：手动修改配置文件 
修改目录下`config.bak.yaml`文件名为`config.yaml`，按照文件所写格式修改填写。

### 启动
添加设置完毕用户及消息发送API后，建议先执行以下命令测试

```shell
python3 main.py test
```

该命令会将所有用户立即上报一次，如控制台无异常输出且能收到消息推送，说明设置无误。若出现异常报错有可能是健康之路已改版，等待更新或向我提PR。

运行以下命令，程序将自行检查是否在上报时间内，并自动进行上报
```shell
python3 main.py
```

### 进程守护
启动程序后若关闭控制台程序会自动退出，因此需要进程守护。进程守护的方式有多种，如使用`nohup`命令：

```shell
nohup /usr/bin/python3 /root/shuasr/main.py > /root/shuasr/output.log 2>&1 &
```

另外也可以用`screen`，下面以`screen`为例介绍用法。

安装`screen`（部分系统已安装）

```shell
# CentOS
yum install screen
# Debian/Ubuntu
apt-get install screen
```

创建一个名为`shu`的screen会话

```shell
screen -L -S shu
```

默认情况下会生成一`screenlog.0`文件，控制台输出将会保存到该文件中，如有错误信息方便查看。

执行`python3 main.py`，按下`Ctrl`+`a`，然后按`d`，离开当前screen会话。

如需恢复，执行

```shell
screen -r shu
```

即可

### 抢排名模式
该模式默认开启，每天24点前会向填报系统重复提交次日的日报信息直到提交成功，以提升排名。如需关闭，修改`config.yaml`中的`grab_mode`值为`False`即可。

关闭后每天7:30填报一次。

## TODO
- [ ] 自动补报功能
  
- [ ] GitHub Actions

[comment]: <> (- [ ] 优化两报改为自动获取地址)
  
- [x] ~~自动判断是否为上报时间上报~~

- [x] ~~增加多线程支持，以便抢排名(?)~~

- [x] ~~完善在校每日两报的上报~~

- [x] ~~使用命令行添加用户~~

## 说明

本项目在 2020 年初用 PHP 编写 ~~（为了抢排名第一）~~ ，返校后为了帮室友上报把源代码改得面目全非 ~~（传说中的屎山）（又不是不能用）~~ 。寒假离校后受下列开源项目启发，用 Python3 对 PHP 编写的源代码进行了重写重构。

本项目仅供学习交流之用，请勿用于非法用途。请遵守当地防疫守则。

**Take care of yourself, and be well!**

## Thanks
[BlueFisher/SHU-selfreport](https://github.com/BlueFisher/SHU-selfreport)
