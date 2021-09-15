# 干他妈的今日校园签到

首先，我默认是在Linux or macOS下操作

> cp configExample.yml config.yml

然后在config.yml里面填写你的签到信息

> python3 autosign.py

缺哪个库装哪个库就行,懒,没有技术支持

如果要定时执行，Linux的话设置一个crontab就行，Windows设计划任务(这个时候最好把脚本的313行config.yml以及脚本中的图片文件的路径改成绝对路径)

