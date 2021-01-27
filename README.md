# SHUASR
Ver.21.01.27

Shanghai University Auto SelfReport

上海大学健康之路自动上报

## 特色
- 接入Server酱接口，适合一人为多人上报的情况，上报结果仅发送给一人。使用前请前往 [Server酱官网](http://sc.ftqq.com/3.version) 申请sckey。
- 自动获取上次填报地址进行上报（已对上海/非上海进行处理）
- ~~兼容每日一报/每日两报~~（挖坑待填）

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

### 添加用户，设置SCKey

#### 方法一：命令行下添加
```shell
# 添加用户
python3 main.py add
# 设置SCKey
python3 main.py sckey
```

#### 方法二：手动修改配置文件 
修改目录下`config.bak.yaml`文件名为`config.yaml`，按照文件所写格式修改填写。

### 启动
```shell
python3 main.py
```

启动后将自动上报一次，随后退出，建议配合Crontab定时启动（见下）

### 定时启动
```shell
vim /etc/crontab
```
根据实际情况添加如下内容
```
# 每天7:30运行一次，请注意服务器时间
30 7 * * * root /usr/bin/python3 /root/shuasr/main.py
```

保存并退出后

```shell
crontab /etc/crontab
```

## TODO

- [ ] 完善在校每日两报的上报

- [ ] 自动判断是否为上报时间上报

- [x] ~~使用命令行添加用户~~

## Thanks
[BlueFisher/SHU-selfreport](https://github.com/BlueFisher/SHU-selfreport)
