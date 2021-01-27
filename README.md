# SHUASR
Ver.21.01.27

Shanghai University Auto SelfReport

上海大学健康之路自动上报

## 特色
- 接入Server酱接口，适合一人为多人上报的情况，上报结果仅发送给一人。使用前请前往 http://sc.ftqq.com/3.version 申请sckey。
- 自动获取上次填报地址进行上报（已对上海/非上海进行处理）
- ~~兼容每日一报/每日两报~~（挖坑待填）

## 使用
### 下载
```shell
git clone https://github.com/panghaibin/shuasr.git
cd shuasr
```

### 安装依赖
```shell
pip install -r requirements.txt
```

### 创建配置文件（防止更新后被覆盖）
```shell
cp config.yaml.bak config.yaml
```

### 修改配置文件
```shell
vim config.yaml
# 也可用其它编辑器
```
格式如下
```yaml
sckey: ""

users:
  "id_card_num_here1":
    - "password_here"
    # 校区设置（未完善，置空或设置为0）
    - 0
  "id_card_num_here2":
    - "password_here"
    - ~
```

### 启动
```shell
python main.py
```

启动后将自动上报一次，随后退出，建议配合Crontab定时启动（见下）

### 定时启动
```shell
vim /etc/crontab
```
根据实际情况添加如下内容
```
# 每天7:30运行一次
30 7 * * * root /usr/bin/python3 /root/shusar/main.py
```

## TODO

-[ ] 完善在校每日两报的上报

-[ ] 自动判断是否为上报时间上报

## Thanks
[BlueFisher/SHU-selfreport](https://github.com/BlueFisher/SHU-selfreport)
