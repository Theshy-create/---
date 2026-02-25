# 密盾 AegisVault

> 本地加密的 AI 账号管理工具 — 所有数据存储在本地，密码经 AES-256 加密，安全可靠。

![version](https://img.shields.io/badge/version-3.0-7B6CF0?style=flat-square)
![python](https://img.shields.io/badge/python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-41CD52?style=flat-square)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat-square&logo=sqlite&logoColor=white)

---

## 下载安装

**直接使用（无需 Python 环境）：** 下载仓库中 [`output/AegisVault_Setup_v3.0.exe`](output/AegisVault_Setup_v3.0.exe)，双击安装即可。

---

## 功能一览

| 模块 | 功能 |
|------|------|
| **加密安全** | PBKDF2 + Fernet (AES-256) 加密密码和 API Key，48 万次迭代密钥派生 |
| **账号管理** | 9 大分类、状态跟踪（库存/出租/售出/回收）、到期提醒、星标收藏、颜色标签 |
| **工作空间** | 多空间隔离（售卖/个人）、自定义图标和类型、空间间账号迁移 |
| **安全分析** | 密码强度评分、弱密码/重复/空密码检测、整体健康度评估 |
| **财务分析** | 月支出/年投入统计、收入与利润率计算、分类成本分析 |
| **密码工具** | 安全密码生成器（8-64 位，可选大小写/数字/符号） |
| **数据管理** | 导入导出（JSON/CSV）、回收站（软删除+恢复）、旧版本数据迁移 |
| **其他** | 仪表盘总览、客户管理、操作日志、深色/浅色主题、30 分钟自动锁定、API Key 验证 |

---

## 从源码运行

```bash
git clone https://github.com/Theshy-create/---.git
cd ---
pip install -r requirements.txt
python main_gui.py
```

## 自行打包

```bash
pip install -r requirements.txt

# 打包 EXE
python build_gui.py
# → dist/AegisVault/AegisVault.exe

# 打包安装程序（需要 Inno Setup 6：https://jrsoftware.org/isdl.php）
python build_installer.py
# → output/AegisVault_Setup_v3.0.exe
```

## Web 版

```bash
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000`

---

## 项目结构

```
├── main_gui.py          # PyQt6 桌面端主程序
├── db.py                # 数据库 & 加密模块
├── app.py               # FastAPI Web 后端
├── templates/index.html # Web 前端
├── build_gui.py         # PyInstaller 打包脚本
├── build_installer.py   # 安装包构建（PyInstaller + Inno Setup）
├── installer.iss        # Inno Setup 配置
├── requirements.txt     # Python 依赖
├── app.ico              # 应用图标
└── output/              # 安装包输出目录
```

运行后自动生成：`accounts.db`（加密数据库）、`.salt`（加密盐值）、`backups/`（自动备份）

## 技术栈

| 组件 | 技术 |
|------|------|
| 桌面 GUI | PyQt6 |
| Web 后端 | FastAPI + Uvicorn |
| 数据库 | SQLite |
| 加密 | cryptography（Fernet / PBKDF2-HMAC-SHA256） |
| 打包 | PyInstaller + Inno Setup |

---

## 安全说明

- 所有密码和 API Key 使用 **Fernet 对称加密** 存储，数据库中无明文
- 主密码通过 **PBKDF2-HMAC-SHA256**（480,000 次迭代）派生密钥
- 修改主密码时自动重新加密全部数据
- 自动备份，最多保留 5 份

> ⚠️ 请妥善保管 `.salt` 文件和主密码，丢失后数据无法恢复。

## 系统要求

- Windows 10 / 11
- Python 3.10+（仅源码运行时需要）
