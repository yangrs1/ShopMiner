# 从 SQLite 迁移到 PostgreSQL

## 背景

ShopMiner 当前统一使用 PostgreSQL 16 作为主数据库。如果在开发环境中使用了 SQLite，需要按以下步骤迁移。

## 迁移步骤

### 1. 导出 SQLite 数据

```bash
# 使用 SQLite 的 .dump 命令导出
sqlite3 instance/shopminer.db .dump > shopminer_dump.sql
```

### 2. 创建 PostgreSQL 数据库

```bash
# 登录 PostgreSQL
psql -U postgres

# 创建数据库和用户
CREATE DATABASE shopminer;
CREATE USER shopminer WITH PASSWORD 'shopminer';
GRANT ALL PRIVILEGES ON DATABASE shopminer TO shopminer;
\c shopminer
GRANT ALL ON SCHEMA public TO shopminer;
```

### 3. 修改环境变量

在 `.env` 文件中设置：

```env
DB_URI=postgresql://shopminer:shopminer@localhost:5432/shopminer
```

### 4. 运行数据库迁移

```bash
flask db upgrade
```

### 5. 验证连接

```bash
curl http://localhost:5000/api/v1/health
# 预期: {"status":"healthy","database":"connected",...}
```

## 注意事项

- SQLite 和 PostgreSQL 在数据类型上有差异（如 BOOLEAN、JSON 支持）
- 确保生产环境始终使用 PostgreSQL，不要在 production 配置中使用 SQLite
- 测试环境仍可使用 SQLite（`sqlite://`）以加快测试速度
