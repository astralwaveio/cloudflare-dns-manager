# Cloudflare DNS 管理工具

一个简单易用的 Cloudflare DNS 记录管理命令行工具，提供友好的终端界面。

## 功能

- 查看和管理所有域名(zones)下的DNS记录
- 添加、修改、删除DNS记录
- 批量删除DNS记录
- 按名称或内容筛选DNS记录
- 支持所有DNS记录类型(A, AAAA, CNAME, MX, TXT等)
- 管理TTL和代理状态(灰色/橙色云朵)
- 友好的中文界面

## 安装

### 前提条件

- Python 3.7+
- pip (Python包管理器)

### 安装步骤

1. 克隆仓库:

```bash
git clone https://github.com/yourusername/cloudflare-dns-manager.git
cd cloudflare-dns-manager
```

2. 安装依赖:

```bash
pip install -r requirements.txt
```

## 使用方法

### 配置

首次运行程序时，会提示您输入 Cloudflare API 凭证信息。您可以选择：

1. **API 令牌** (推荐): 提供更精细的权限控制
   - 在 Cloudflare 仪表盘 -> 我的个人资料 -> API 令牌 中创建
   - 需要 "Zone:DNS:Edit" 权限

2. **Global API 密钥 + 邮箱**: 提供完整的账户访问权限
   - 在 Cloudflare 仪表盘 -> 我的个人资料 -> API 令牌 -> API 密钥 中查看

您也可以直接编辑 `config/config.yaml` 文件来配置这些信息:

```yaml
auth:
  api_token: "your-api-token"
  # 或者使用以下组合
  # api_key: "your-global-api-key"
  # email: "your-email@example.com" 
```

### 运行程序

```bash
# 基本运行
python main.py

# 指定配置文件
python main.py --config /path/to/config.yaml

# 调试模式
python main.py --debug
```

### 快捷键

程序内可用的快捷键:

- 域名列表页面:
  - `Q`: 退出程序
  - `R`: 刷新域名列表

- DNS记录页面:
  - `ESC`: 返回上一级
  - `R`: 刷新记录列表
  - `A`: 添加记录
  - `E`: 编辑记录
  - `D`: 删除记录
  - `B`: 批量删除模式
  - `F`: 筛选记录

- 表单页面:
  - `ESC`: 取消
  - `F1`: 保存

## 项目结构

```
cloudflare-dns-manager/
├── config/                # 配置文件目录
│   └── config.yaml        # 主配置文件
├── src/                   # 源代码
│   ├── api.py            # Cloudflare API 交互
│   ├── models.py         # 数据模型
│   ├── ui.py             # TUI界面实现
│   ├── config.py         # 配置管理
│   └── utils.py          # 工具函数
└── main.py               # 程序入口
```


## 所需的依赖包

创建一个 requirements.txt 文件，包含以下内容：

```
requests>=2.25.0
pyyaml>=5.1
textual>=0.14.0
rich>=12.0.0
```

## 使用说明

1. 克隆本仓库或下载源码
2. 安装依赖: `pip install -r requirements.txt`
3. 运行程序: `python main.py`
4. 首次运行会要求输入 Cloudflare API 凭证
5. 登录成功后，您将看到您的 Cloudflare 域名列表
6. 使用键盘导航和快捷键来管理DNS记录

这是一个完整的 Cloudflare DNS 管理工具，使用 textual 库提供了友好的终端用户界面。它支持查看、添加、编辑和删除 DNS 记录，以及批量删除功能。配置通过 YAML 文件管理，简单易用。
