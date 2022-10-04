# 自动申请明日离校

## 在 GitHub Actions 使用
目前设置北京北京时间 8:20 执行，以 GitHub Actions 实际执行时间为准

1. 设置环境变量 `APPLY_USERS` ，格式如下
    ```
    Username01,Password01[,API_TYPE,API_KEY_HERE][;Username02,Password02[,API_TYPE,API_KEY_HERE]...]
    ```
    例如
    ```
    19XXYYZZ,123456Abc;19QQWWEE,45678Ijk,2,asdfghj
    ```
2. 设置环境变量 `APPLY_SEND` ，可选，格式为 `API_TYPE,API_KEY_HERE`

## 在自己的服务器使用
1. 将示例配置文件 `apply.bak.yaml` 重命名为 `apply.yaml`，根据其中的提示编写
2. 自行设定Crontab执行 `python3 apply.py`
