<p align="center">
  <img src="app.ico" width="80" />
</p>

<h1 align="center">密盾 AegisVault</h1>

<p align="center">
  <strong>本地加密的 AI 账号管理工具</strong><br/>
  所有数据存储在本地，密码经 AES-256 加密，安全可靠
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-3.0-7B6CF0?style=flat-square" />
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/PyQt6-GUI-41CD52?style=flat-square" />
  <img src="https://img.shields.io/badge/SQLite-Database-003B57?style=flat-square&logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" />
</p>

---

## 功能特性

### 🔐 安全加密
- **PBKDF2 + Fernet (AES-256)** 加密所有密码和 API Key
- 480,000 次迭代的密钥派生，抵御暴力破解
- 主密码不存储明文，仅保存哈希值
- 密码修改历史记录

### 📋 账号管理
- 支持 9 大分类：AI 对话、AI 开发、AI 绘图、办公 AI、社交通讯、游戏娱乐、购物电商、金融支付、其他
- 账号状态跟踪：库存中 / 已出租 / 已售出 / 已回收
- 到期日自动提醒（7 天内即将到期高亮）
- 星标收藏、颜色标签、自定义标签
- 快速模板创建（内置 DeepSeek、ChatGPT、Claude、Cursor、Midjourney）

### 📂 工作空间
- 多工作空间隔离管理（售卖空间 / 个人空间）
- 支持自定义空间图标和类型（个人 / 商户）
- 空间间账号自动迁移

### 🛡️ 安全分析
- 密码强度评分（0-4 级）
- 弱密码 / 重复密码 / 空密码检测
- 账号整体健康度评估

### 💰 财务分析
- 月支出 / 年投入统计
- 售卖收入与利润率计算
- 分类成本分析
- 账号状态分布统计

### 🔧 更多功能
- 🔑 安全密码生成器（8-64 位，可选大小写/数字/符号）
- 📊 仪表盘数据总览
- 👥 客户信息管理
- 🗑️ 回收站（软删除 + 恢复）
- 📝 操作日志审计
- 📤 导入导出（JSON / CSV）
- 🔄 旧版本数据迁移
- 🌗 深色 / 浅色主题切换
- 🔒 30 分钟无操作自动锁定
- 🔍 API Key 有效性验证（DeepSeek / OpenAI 兼容接口）

---

## 快速开始

### 方式一：安装包（推荐）

下载 `output/AegisVault_Setup_v3.0.exe`，双击安装即可使用，无需 Python 环境。

### 方式二：源码运行

```bash
# 克隆仓库
git clone <仓库地址>
cd AegisVault

# 安装依赖
pip install -r requirements.txt

# 启动桌面版
python main_gui.py
```

### 方式三：自行打包 EXE

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 打包（二选一）

# 仅打包 EXE（无需额外软件）
python build_gui.py
# → 输出: dist/AegisVault/AegisVault.exe

# 打包完整安装包（需先安装 Inno Setup 6）
python build_installer.py
# → 输出: output/AegisVault_Setup_v3.0.exe
```

> **Inno Setup 下载**：https://jrsoftware.org/isdl.php （仅生成 .exe 安装包时需要，直接运行 EXE 不需要）

### 方式四：Web 版

```bash
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
# 浏览器打开 http://127.0.0.1:8000
```

---

## 项目结构

```
AegisVault/
├── main_gui.py          # PyQt6 桌面端（主程序）
├── db.py                # 数据库 & 加密模块
├── app.py               # FastAPI Web 后端
├── templates/
│   └── index.html       # Web 前端页面
├── build_gui.py         # PyInstaller 打包脚本
├── build_installer.py   # 安装包构建脚本（PyInstaller + Inno Setup）
├── installer.iss        # Inno Setup 配置
├── app.ico              # 应用图标
├── requirements.txt     # 全部依赖
├── accounts.db          # SQLite 数据库（运行后自动生成）
├── .salt                # 加密盐值（运行后自动生成）
└── backups/             # 自动备份目录
```

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 桌面 GUI | PyQt6 |
| Web 后端 | FastAPI + Uvicorn |
| 数据库 | SQLite |
| 加密 | cryptography (Fernet / PBKDF2-HMAC-SHA256) |
| 打包 | PyInstaller + Inno Setup |
| 主题 | 自研深色/浅色双主题系统 |

---

## 安全说明

- 所有敏感数据（密码、API Key）使用 **Fernet 对称加密**（基于 AES-128-CBC）存储
- 主密码通过 **PBKDF2-HMAC-SHA256**（480,000 次迭代）派生加密密钥
- 加密盐值存储在独立文件 `.salt` 中
- 数据库文件 `accounts.db` 中不含任何明文密码
- 修改主密码时自动重新加密全部数据
- 支持自动备份，最多保留 5 份

> ⚠️ 请妥善保管 `.salt` 文件和主密码，丢失后数据将无法解密恢复。

---

## 系统要求

- **操作系统**：Windows 10 / 11
- **Python**：3.10+（源码运行时）
- **磁盘空间**：约 150 MB（安装后）
