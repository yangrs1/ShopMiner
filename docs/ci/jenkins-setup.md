# ShopMiner Jenkins CI/CD 搭建指南

> 本文档详细说明如何在自托管的 Jenkins 环境中为 ShopMiner 项目配置持续集成（CI）流水线。  
> 流水线使用声明式 `Jenkinsfile`，支持 Gitee Webhook 自动触发、Allure 测试报告、代码覆盖率、Docker 构建等功能。

---

## 📋 目录

- [1. 前置条件](#1-前置条件)
- [2. Jenkins 插件安装](#2-jenkins-插件安装)
- [3. 全局工具配置](#3-全局工具配置)
- [4. 创建 Jenkins Pipeline 任务](#4-创建-jenkins-pipeline-任务)
- [5. Gitee Webhook 配置](#5-gitee-webhook-配置)
- [6. 环境变量说明](#6-环境变量说明)
- [7. 首次运行与验证](#7-首次运行与验证)
- [8. 常见问题排查](#8-常见问题排查)

---

## 1. 前置条件

| 组件 | 版本要求 | 说明 |
|------|---------|------|
| Jenkins | 2.x (推荐 2.375+) | 自托管实例，建议 4GB+ 内存 |
| Docker | 20.10+ | 用于 `docker-compose build` 阶段 |
| Docker Compose | v2.x | 多容器构建 |
| Python | 3.10+ | Jenkins 节点上需预装 |
| Node.js | 18+ | 用于前端构建和测试 |
| npm | 9+ | Node 包管理 |
| Git | 2.x | 源码拉取 |

---

## 2. Jenkins 插件安装

在 Jenkins 管理界面中安装以下必需插件：

### 必需插件

1. **Pipeline** (`pipeline`)
   - 提供声明式流水线 DSL 支持
   
2. **Allure Jenkins Plugin** (`allure-jenkins-plugin`)
   - 用于生成和展示 Allure 测试报告
   - 搜索 "Allure" 进行安装
   
3. **NodeJS Plugin** (`nodejs`)
   - 在流水线中管理 Node.js 版本
   - 支持在构建节点上自动安装 Node.js
   
4. **JUnit Plugin** (`junit`)
   - 通常预装在 Jenkins 中
   - 解析 JUnit XML 格式的测试结果

5. **HTML Publisher Plugin** (`htmlpublisher`)
   - 用于发布 HTML 覆盖率报告
   
6. **Git Plugin** (`git`)
   - 通常预装，用于源码管理

### 可选但推荐的插件

7. **Gitee Plugin** (`gitee`)
   - 支持 Gitee Webhook 自动触发 Pipeline
   - 可在 Jenkins 插件管理搜索安装
   
8. **Generic Webhook Trigger Plugin** (`generic-webhook-trigger`)
   - 通用 Webhook 触发器（Gitee Plugin 的替代方案）
   
9. **Workspace Cleanup Plugin** (`ws-cleanup`)
   - 构建后清理工作空间（Jenkinsfile 中已使用 `cleanWs()`）

### 安装步骤

```
Jenkins 首页 → Manage Jenkins → Plugins → Available plugins
→ 搜索并勾选以上插件 → 点击 "Install without restart"
```

---

## 3. 全局工具配置

### 3.1 配置 Node.js

```
1. Jenkins 首页 → Manage Jenkins → Tools
2. 找到 "NodeJS installations" 区域
3. 点击 "Add NodeJS"
4. Name: "NodeJS 18+"  （必须与 Jenkinsfile 中的 tool name 一致）
5. Version: 选择 "Node.js 18.x" 或 "Node.js 20.x"
6. 勾选 "Install automatically"
7. 点击 "Save"
```

### 3.2 配置 Allure 命令行

```
1. Jenkins 首页 → Manage Jenkins → Tools
2. 找到 "Allure Commandline installations" 区域
3. 点击 "Add Allure Commandline"
4. Name: "allure" （默认即可）
5. Version: 选择最新版
6. 勾选 "Install automatically"
7. 点击 "Save"
```

### 3.3 配置 Docker 权限

确保 Jenkins 运行用户（通常是 `jenkins`）有权限执行 Docker 命令：

```bash
# 将 jenkins 用户加入 docker 组
sudo usermod -aG docker jenkins

# 重启 Jenkins 服务
sudo systemctl restart jenkins
```

---

## 4. 创建 Jenkins Pipeline 任务

### 步骤

```
1. Jenkins 首页 → 新建任务（New Item）
2. 输入任务名称: "ShopMiner-CI"
3. 选择 "Pipeline" → 点击 "OK"
4. 进入任务配置页面
```

### 配置说明

#### General（通用）

| 选项 | 值 | 说明 |
|------|----|------|
| Discard old builds | ✅ 启用 | 建议：保持最近 10 天或 30 次构建 |
| GitHub project | 可选 | 填写 Gitee 仓库地址 |
| This project is parameterized | 可选 | 如需参数化构建可勾选 |

#### Pipeline（流水线）

| 选项 | 值 |
|------|----|
| Definition | **Pipeline Script from SCM** |
| SCM | **Git** |
| Repository URL | `https://gitee.com/你的用户名/ShopMiner.git` |
| Credentials | 添加 Gitee 凭据（用户名+密码 或 SSH Key） |
| Branches to build | `*/main` 或 `*/master` |
| Script Path | `Jenkinsfile` |
| Lightweight checkout | ✅ 勾选（可选，加快流水线初始化） |

### 凭据配置

```
1. 在 Repository URL 下方点击 "Add" → "Jenkins"
2. Kind: "Username with password"
3. Username: 你的 Gitee 用户名
4. Password: 你的 Gitee 密码（或个人访问令牌）
5. ID: "gitee-credentials"
6. 点击 "Save"
```

---

## 5. Gitee Webhook 配置

### 5.1 推荐方案：使用 Gitee Plugin

#### 前提：已安装 Gitee Plugin

#### 步骤一：在 Jenkins 任务中启用 Webhook 触发器

```
1. 进入 ShopMiner-CI 任务配置
2. 找到 "Build Triggers" 区域
3. 勾选 "Gitee Webhook Trigger"
4. 在 "Webhook URL" 会显示一个 URL，复制下来
5. 点击 "Save"
```

> 如果使用 Generic Webhook Trigger，勾选 "Generic Webhook Trigger" 并设置 Token。

#### 步骤二：在 Gitee 仓库中添加 Webhook

```
1. 登录 Gitee → 进入 ShopMiner 仓库
2. 点击 "管理" → "WebHooks" → "添加 WebHook"
3. URL: 粘贴 Jenkins 中复制的 Webhook URL
   - 格式类似: http://<jenkins-server>:8080/gitee-webhook/
4. 密码/签名密钥: 留空（或在 Jenkins 中设置 Secret）
5. 触发事件:
   - ✅ Push（推送）
   - ✅ Pull Request（可选）
6. 勾选 "Active"（激活）
7. 点击 "Add"
```

> **注意**：如果 Jenkins 部署在内网，需要确保 Gitee 能够访问到 Jenkins 服务器。  
> 可以使用 ngrok、frp 等工具将内网服务暴露到公网。

### 5.2 替代方案：SCM 轮询

`Jenkinsfile` 中已配置了 `pollSCM('H/5 * * * *')` 作为回退方案。  
该配置每 5 分钟检查一次 Gitee 仓库是否有变更。

如需调整轮询频率，修改 Jenkinsfile 中的 cron 表达式即可：

```groovy
triggers {
    pollSCM('H/5 * * * *')  // 每 5 分钟
    // pollSCM('H * * * *') // 每 1 小时
    // pollSCM('*/10 * * * *') // 每 10 分钟
}
```

### 5.3 Gitee Webhook 验证

配置完成后，可以在 Gitee Webhook 页面点击 "测试" 发送测试推送事件。  
Jenkins 端应能自动触发 Pipeline 构建。

---

## 6. 环境变量说明

### 在 Jenkinsfile 内部定义的环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VENV_DIR` | `${WORKSPACE}/.venv` | Python 虚拟环境目录 |
| `ALLURE_DIR` | `${WORKSPACE}/tests/report/allure-results` | Allure 测试结果目录 |
| `REPORTS_DIR` | `${WORKSPACE}/reports` | JUnit 报告输出目录 |
| `COVERAGE_DIR` | `${REPORTS_DIR}/coverage-html` | HTML 覆盖率报告目录 |

### 可在 Jenkins 全局配置中的环境变量

如果需要在 Jenkins 全局配置中添加环境变量：

```
Jenkins 首页 → Manage Jenkins → Configure System → Global properties
→ 勾选 "Environment variables" → 添加：
```

| 变量名 | 建议值 | 说明 |
|--------|--------|------|
| `FLASK_ENV` | `testing` | Flask 测试环境配置 |
| `TEST_DB_URI` | `sqlite:///:memory:` | 测试用数据库 URI（避免依赖外部 PostgreSQL） |

### 凭据管理

敏感信息（如数据库密码、API Key）建议使用 Jenkins Credentials 管理：

```
1. Jenkins 首页 → Manage Jenkins → Credentials
2. 添加凭据 → 选择类型（Secret text / Username with password）
3. 在 Jenkinsfile 中使用 credentials() 引用：

   environment {
       DB_PASSWORD = credentials('db-password-id')
   }
```

---

## 7. 首次运行与验证

### 手动触发构建

```
1. 进入 ShopMiner-CI 任务页面
2. 点击 "Build Now"（立即构建）
3. 查看 "Build History" 中的最新构建
4. 点击构建号 → "Console Output" 查看日志
```

### 验证各阶段

一个成功的构建应包含以下所有阶段（Stage View 中均为绿色 ✅）：

| 阶段 | 预期结果 |
|------|----------|
| Checkout | 从 Gitee 拉取代码成功 |
| Install Backend | pip 安装依赖无错误 |
| Install Frontend | npm ci 安装成功 |
| Run Backend Tests | pytest 执行通过（绿色） |
| Coverage | 覆盖率报告生成成功 |
| Frontend Tests | vitest 执行通过 |
| Allure Report | Allure 报告生成并展示 |
| Docker Build | docker-compose build 成功 |

### 查看报告

构建完成后，在构建页面中可查看：

1. **Test Result** → 通过 JUnit 插件展示的测试结果趋势
2. **Allure Report** → 在左侧菜单中点击 "Allure Report"
3. **Coverage Report** → 在左侧菜单中点击 "Coverage Report"

---

## 8. 常见问题排查

### 8.1 无法拉取代码（Checkout 失败）

**错误信息**：
```
Failed to connect to repository: Command "git ls-remote -h -- ...
```

**可能原因与解决**：
| 原因 | 解决方法 |
|------|----------|
| Gitee 凭据错误 | 在 Jenkins 中更新 Gitee 凭据 |
| Jenkins 无法访问 Gitee | 检查网络连接 / 代理设置 |
| SSH Key 未添加 | 在 Gitee 中添加 Jenkins 节点的公钥 |

### 8.2 pip 安装失败（Install Backend 失败）

**错误信息**：
```
ERROR: Could not find a version that satisfies the requirement ...
```

**可能原因与解决**：
| 原因 | 解决方法 |
|------|----------|
| Python 版本过低 | 确认 Jenkins 节点安装 Python 3.10+ |
| 网络超时 | 使用国内 PyPI 镜像：`pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt` |
| 依赖冲突 | 在 Jenkinsfile 中将 pip 升级到最新版：`pip install --upgrade pip` |

### 8.3 npm ci 失败（Install Frontend 失败）

**错误信息**：
```
npm ERR! cipm can only install packages with an existing package-lock.json
```

**原因**：`package-lock.json` 不存在或未提交到仓库。

**解决方法**：
```bash
# 在本地项目中生成锁文件并提交
cd frontend
npm install   # 生成 package-lock.json
git add frontend/package-lock.json
git commit -m "chore: add package-lock.json"
git push
```

或者临时改为 npm install（不推荐，锁文件缺失会导致构建不一致）：

在 Jenkinsfile 中将 `npm ci` 改为 `npm install`。

### 8.4 Allure 报告生成失败

**错误信息**：
```
[Allure] An error occurred during allure report generation
```

**可能原因与解决**：
| 原因 | 解决方法 |
|------|----------|
| Allure 命令行未安装 | 检查 Jenkins 全局工具配置 → Allure Commandline |
| 未找到测试结果 | 确认 `pytest` 的 `--alluredir` 参数路径正确 |

### 8.5 Docker 构建失败

**错误信息**：
```
Cannot connect to the Docker daemon
```

**原因**：Jenkins 用户没有 Docker 权限。

**解决方法**：
```bash
# 将 jenkins 用户加入 docker 组
sudo usermod -aG docker jenkins
# 重新登录或重启
sudo systemctl restart jenkins
```

### 8.6 测试全部失败（Run Backend Tests 失败）

**错误信息**：
```
ModuleNotFoundError: No module named 'app'
```

**原因**：Python 路径未正确设置。

**解决方法**：
在 Jenkinsfile 的测试阶段中设置 `PYTHONPATH`：

```groovy
sh """
    . "${VENV_DIR}/bin/activate"
    export PYTHONPATH="${WORKSPACE}:\${PYTHONPATH}"
    pytest ...
"""
```

### 8.7 Gitee Webhook 未触发构建

| 原因 | 解决方法 |
|------|----------|
| Webhook URL 不可访问 | 确认 Jenkins 公网地址正确 |
| 未勾选 "Active" | 在 Gitee Webhook 设置中勾选 |
| Plugin 未安装 | 确认已安装 Gitee Plugin 或 Generic Webhook Trigger |
| 防火墙阻挡 | 在 Jenkins 服务器防火墙中放行 8080 端口 |

### 8.8 前端测试报错（vitest 相关）

**错误信息**：
```
Error: Cannot find module '@vue/test-utils'
```

**原因**：`node_modules` 未正确安装。

**解决方法**：
```bash
# 清理后重新安装
cd frontend
rm -rf node_modules
npm ci
```

---

## 📎 附录

### 推荐的 Jenkins 系统配置

```bash
# Jenkins 启动参数（/etc/default/jenkins 或 systemd unit）
JAVA_ARGS="-Xms1024m -Xmx4096m -Djenkins.install.runSetupWizard=false"
```

### 国内镜像加速

如果构建节点在中国大陆，建议配置镜像加速：

**pip 镜像**：
```groovy
// 在 Jenkinsfile 的 Install Backend 阶段中添加
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

**npm 镜像**：
```groovy
// 在 Jenkinsfile 的 Install Frontend 阶段中添加
npm config set registry https://registry.npmmirror.com
npm ci
```

---

> 文档版本: v1.0  
> 最后更新: 2026-06-15  
> 如有问题，请联系项目维护者或在 Gitee Issues 中提出。
