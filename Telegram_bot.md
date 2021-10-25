# 通过 Telegram Bot 推送填报结果 

1. 创建 Bot

    打开 [@BotFather](https://t.me/botfather) ，点击 `/newbot` ，输入一个自定义昵称。然后输入一个以 `bot` 结尾的用户名，且不可以和其他任何 Bot 重名。创建成功后，会返回一个 token ，形如 `123456789:mbpSwrgRCr1iLt4MZRYqq0mlko-MGXMcg` 。

2. 获取 Chat ID

    点击 `t.me/botUsername` ，打开创建的 Bot 。点击 `/start` ，然后发送 `@userinfobot` 并点击它。随后点击 `/start` ， `userinfobot` 将返回一个 `Id` ，为一串数字。

3. 在本项目中使用

    在本项目中，这两个参数的存储格式为 `BOT_TOKEN@CHAT_ID` ，即将两个参数用 `@` 作为分隔符拼接。例如 `123456789:mbpSwrgRCr1iLt4MZRYqq0mlko-MGXMcg@987456321`
    
    若要在 GitHub Actions 中使用，设置 Secrets 的 `SEND` 的值为 `3,BOT_TOKEN@CHAT_ID` ，前面的 `3` 为本项目中的消息发送代号；若在自建服务器使用，根据提示输入即可。