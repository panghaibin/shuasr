# 自动申请次日进校与离校

## 在 GitHub Actions 使用
目前设置北京时间 9:20 执行，以 GitHub Actions 实际执行时间为准

1. 设置 Secrets `APPLY_USERS` ，格式如下
    ```
    Username01,Password01,InOr/AndOut[,API_TYPE,API_KEY][;Username02,Password02,InOr/AndOut[,API_TYPE,API_KEY]...]
    ```
    - `UsernameXX` 为学工号
    - `PasswordXX` 为密码
    - `InOr/AndOut` 可以为 `in` , `out` 或 `all` ，分别表示仅申请进校、仅申请离校、同时申请进校和离校。均为小写。
    - `API_TYPE` 和 `API_KEY` 为接收消息推送的 API 类型和 API Key，可选，详见 [多种消息推送接口](README.md#提醒结果消息推送介绍) ，不填则不推送消息
    
    例如：
    ```
    19XXYYZZ,123456Abc,in;19QQWWEE,45678Ijk,out,2,asdfghj;19AABBCC,987654Xyz,all
    ```
    []内的参数可选，若配置可为单个用户推送消息
2. （可选）设置 Secrets `APPLY_SEND` ，格式为 `API_TYPE,API_KEY_HERE`。设置后全部用户的申请结果将会推送到指定的推送接口。

然后记得到 Actions 页面启用 Workflow。

申请失败时不会使Actions失败，建议为每一个用户都配置消息推送，或者配置 `APPLY_SEND` 。

## 在自己的服务器使用
1. 将示例配置文件 `apply.bak.yaml` 重命名为 `apply.yaml`，根据其中的提示编写
2. 自行设定Crontab执行 `python3 apply.py`
