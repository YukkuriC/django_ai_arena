# 代码竞技场
基于django的AI对战游戏运行平台

## 功能：

### usr_sys 用户系统
1. 用户注册登录修改密码邮件验证
1. 个人主页：查看已上传代码
1. 设置用户昵称
1. 使用[Gravatar](https://www.gravatar.com)生成用户头像

### match_sys 比赛系统
1. 比赛代码
    * 代码上传、保存、删除功能
    * 上传阶段的代码合法性验证
    * 限制单用户单游戏最大上传代码数
    * 代码编辑、在线验证功能
    * 基于CodeMirror的代码查看功能
1. pairmatch功能
    * 自己代码发起与他人代码的对战
    * 代码参与的所有比赛记录查询
    * 比赛记录查看、前端渲染与删除
1. 天梯系统
    * 显示特定类型游戏所有代码战绩与积分
    * 依据排名的匹配赛

### 其它
1. 多元素表格基于GET参数的部分显示、翻页功能

### external 比赛系统后端
1. 监视进程维护多进程比赛运行，支持超时中止与手动中止
1. 提供抽象层接口，调用ORM与不同比赛模块
1. 加载、验证比赛代码等辅助功能及接口
1. 现基于django_cron实现多进程发起比赛系统
    * 支持通过配置自动发起后台匹配赛

### 比赛项目
项目|上传代码+运行比赛|保存比赛记录|前端可视化记录
-|-|-|-
[井字棋]](https://github.com/YukkuriC/PyTicTacToe)|√|√|√
[漂移乒乓](https://github.com/chbpku/pingpong.sessdsa)|√|√|
[纸带圈地](https://github.com/chbpku/paper.io.sessdsa)|√|√|√
[OSMO](https://github.com/chbpku/osmo.sessdsa)|√|√|√
[2048](https://github.com/pkulab409/sessdsa.2048)|√|√|√
[星际群落](https://github.com/pkulab409/pkudsa.stellar)|√|√|√
[方块大战](https://github.com/pkulab409/pkudsa.tetris)|√|√|

### 向网站中添加新的比赛项目
详见[此文档](HOWTO_NEW_GAME.md)

## 待实现功能：

### usr_sys 用户系统
1. 用户大厅，检索所有用户公开信息

### match_sys 比赛系统
1. 比赛邀请功能
1. 比赛记录保存为PNG/GIF/MP4

### external 比赛系统后端
1. 基于图与pairmatch的复杂比赛系统框架

### 比赛项目
1. 黑白棋
    1. 移植
1. 漂移乒乓
    1. 前端查看比赛记录
1. 纸带圈地
    1. 前端页面布局修改
