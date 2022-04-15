# 如何添加新的比赛项目

## 零、决定名称

从排版统一性来说，它最好是4个字  
_井字棋：“你有事吗”_  
从排版统一性来说，它最好是 __不多于__ 4个字

* 在[总配置文件](main/settings.py)中`AI_TYPES`变量内注册名称  

    `AI_TYPES`类型为字典  
    各键值对内，键均为数字，代表其游戏类型序号  
    值则是比赛的显示名称，用于导航栏与各下拉选项框  
    以下将用`{index}`指代需替换为游戏序号的文本

## 一、创建网页

以下页面均遵循Django模板引擎语法，继承对象均为同目录下`base.html`

* 比赛说明页 ([示例](external/templates/game_info/0.html)) ([示例2，含图片](external/templates/game_info/5.html))
    * 命名路径为`external/templates/game_info/{index}.html`

* 比赛记录查看页
    * 命名路径为`external/templates/renderer/{index}.html`
    * 先记住有这么个东西，后面再展开写

## 二、链接游戏核心

* 决定一个英文简称

    * 无实际意义，仅在开发时决定文件路径
    * 以下以`{eng_name}`代替

* 创建相关链接文件

    * 在`external`目录下新建目录，作为子模块基础目录
        * 建议命名：`external/ai_{eng_name}`
        * 以下将以`{BASE}`代替该目录路径

    * 创建比赛进程接口文件`{BASE}/__init__.py`

    * 在目录`external/tags`下创建比赛记录标签解析文件
        * 建议命名：`external/tags/{eng_name}.py`

* 创建与拉取git submodule

    1. （可选）整理原仓库代码模块
        * 在原仓库创建新分支

        * 尽可能删除所有无关文件
            * 体积较大的非代码文件（如PDF等格式开发文档）
            * 无关的代码文件，如：
                * 用于本地可视化的py、html等文件
                * 示例AI代码
            * 其它与游戏核心实现无关的文件，如：
                * 规则说明、开发进度等md文件
                * license（危）
        
        * （如有需要）对原游戏核心进行整理
            * 代码导入方式通用化
                * 终极目标：一个接收两个module的函数
            * 比赛记录存储方式通用化
                * 可控写记录步骤 > 耦合比赛进度完成后自动写记录
                * 可控输出文件路径 > 硬编码输出固定记录文件
                * json > 易解析文本格式 > 二进制格式 > write-only面向人眼阅读文本格式

    1. 在[.gitmodules](.gitmodules)文件内注册

        ```ini
        [submodule "{BASE}/{仓库名称}"]
        path = {BASE}/{仓库名称}
        url = https://github.com/{仓库所有人}/{仓库名称}.git
	    branch = {想要拉取的分支名}
        ```
        * 可选：配置镜像源
            * ~~github.com.cnpmjs.org~~ RIP
            * ~~hub.fastgit.xyz~~ 只能pull没法push
            * 寄

    1. 拉取submodule
        ```bash
        git submodule init
        git submodule update
        ```

## 三、比赛进程接口文件`{BASE}/__init__.py` （[示例](external/ai_ttt/__init__.py)）

* 目标：继承[基础设施](external/_base.py)内的`BasePairMatch`类，实现“完成一局数轮比赛并输出结果”功能
    * 通过引用`from external.factory import FactoryDeco`并在类上使用装饰器`FactoryDeco({index})`以注册至主环境

* 主要函数接口（以下均为`@classmethod`，默认为`NotImplementedError`）
    * `run_once(cls, d_local, d_global)`：运行一局比赛，返回比赛记录对象
        * 通过`d_local['players']`获取玩家代码模块列表
        * 通过`d_local['names']`获取玩家名称列表
            * 其中外部发起比赛者固定为`code1`，接收者固定为`code2`
        * 上述列表长度均为2，`#0`位为当前小轮指定先手玩家，`#1`位为当前小轮指定后手玩家
        
    * `output_queue(cls, match_log)`：读取比赛记录，返回比赛结果元组
        * 元组`#0`位对象为int或None，代表比赛胜者
            内容|含义
            -|-
            0|先手胜
            1|后手胜
            None|平局
        * 后续位可根据需要自定义内容

    * `runner_fail_log(cls, winner, descrip, d_local, d_global)`：处理异常情况
        * 需返回空的比赛记录对象
        * `winner`参数为int或None，定义同上
        * `descrip`参数记录该局比赛发生的异常
        * 可能触发该函数的情形如下：
            情形|winner|descrip
            -|-|-
            一方import或运行时报错|int|报错判负方异常对象
            双方import时均报错|None|异常列表
            `run_once`函数捕捉到异常|None|平台异常对象

            * 以上“异常列表”均指代一个长为2的列表，`#0`、`#1`位分别为小轮先后手玩家对应异常对象

    * `get_winner(cls, record)`：给定比赛记录，提取输出其对应的胜利者
        内容|含义
        -|-
        0|大局发起方胜利
        1|大局接收方胜利
        None|平局
            

* 主要可选函数接口（以下均为`@classmethod`，默认实现不会抛出异常）
    * `pre_run(cls, d_local, d_global)`：开始多小轮比赛前初始化比赛环境
        * 返回值将写入cls.init_params变量，可按需使用

    * `swap_fields(cls, d_local, d_global)`：先后手玩家交换时运行一次，可按需使用

* 代码规范接口：Meta类
    * 继承自[基础设施](external/_base.py)中的`BaseCodeLoader.Meta`（即`BasePairMatch.Meta`）类，用于进行AST代码审查
    * 可自定义内容如下（以下各项均为列表）：
        变量名|是否含默认实现|内容|元素类型
        -|-|-
        module_whitelist|是|可import的内置库|字符串，为库名称
        func_blacklist|是|禁止使用的内置函数|字符串，为函数名称
        game_whitelist|否|可额外import的游戏基础设施库|字符串，为库名称
        required_functions|否|代码模块中需要实现的函数|字符串，为函数名称
        required_classes|否|代码模块中需要实现的类|元组，`#0`位为类名称，`#1`位为类中需要的函数名称列表（定义同`required_functions`）

* 其余接口可查看[基础设施](external/_base.py)中相关函数注释

* 建议：二次封装
    * 将比赛对局发生统一为“两个分别取了名的代码模块发生一场比赛，返回其记录”的函数
    * 将比赛记录文件统一为JSON格式

## 四、比赛记录标签解析文件（[示例](external/tags/ttt.py)）

* 目标：继承[基础设施](external/tag_loader.py)内的`RecordBase`类，“在比赛大局查看页面解析各局结果”功能
    * 通过引用同文件内的`RecordDeco`并在类上使用装饰器`RecordDeco({index})`以注册至主环境

* 函数接口（以下所有`match`参数为[Django模型](match_sys/models.py)中的大局比赛`PairMatch`对象，`record`参数为各小局比赛记录对象）
    接口名称|说明|包含默认实现
    -|-|-
    i_holder|该轮是否为接收方先手，返回bool|否
    i_winner|该轮后手方是否胜利，0为先手胜，1为后手胜，None为平局|否
    r_winner|该局胜利玩家|是（依赖`i_holder`与`i_winner`实现）
    r_holder|该局先手玩家名称|是（依赖`i_holder`）
    r_length|该对局持续长度|否
    r_win_desc|胜利原因|否
    r_desc_plus|详细原因说明|否

## 五、后端侧运行检验

* 至此，顺利的话游戏内核应该已经嵌入网站中，直至大局比赛查看页面均可工作，可以上传一些代码测试其结果了

    代码类型|预期结果
    -|-
    不具备基本结构/企图用exec等搞事的代码|于上传/编辑保存阶段报错，不予通过
    随机代码|可正常发起比赛，呈现较弱的实力
    认真开发的代码|可正常发起比赛，呈现较强的实力

* 一些可能发生的神秘问题与定位

    问题|异常定位
    -|-
    所有场次均为相同结果|内核嵌入、运行
    所有比赛均为0局“已完成”结束|比赛记录保存；<br>C++段错误等直接炸毁Python进程的情况
    弱代码暴打强代码；<br>胜者显示与计分不符|胜者判断

## 六、前端对局可视化页面`external/templates/renderer/{index}.html`

## TODO