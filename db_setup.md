# 数据库设置指南

## Supabase 连接问题解决

当你看到以下错误信息时：

```
保存会话失败: {'message': 'Invalid API key', 'hint': 'Double check your Supabase `anon` or `service_role` API key.'}
```

这表明你的 Supabase API 密钥无效。请按照以下步骤解决：

### 1. 创建 Supabase 项目

1. 访问 [Supabase 官网](https://supabase.com/) 并登录
2. 创建一个新项目
3. 记下项目 URL 和 API 密钥（anon key）

### 2. 创建数据表

在 Supabase 控制台中执行以下 SQL 创建必要的表：

```sql
-- 创建天翼云会话表
CREATE TABLE IF NOT EXISTS tianyi_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL UNIQUE,
    cookies JSONB NOT NULL,
    username TEXT,
    password TEXT,
    created_at BIGINT NOT NULL,
    updated_at BIGINT NOT NULL
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_tianyi_sessions_user_id ON tianyi_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_tianyi_sessions_updated_at ON tianyi_sessions(updated_at);
```

### 3. 设置环境变量

创建一个 `.env` 文件（不要上传到公共仓库）并添加以下内容：

```
SUPABASE_URL=https://你的项目ID.supabase.co
SUPABASE_KEY=你的anon密钥
```

### 4. 修改 db_manager.py

已经更新了 `db_manager.py` 文件，支持从环境变量读取配置。如果环境变量未设置，将使用默认值。

### 临时解决方案

如果你暂时不想使用 Supabase，可以在 `api/index.py` 文件中修改登录逻辑，不保存会话到数据库，而是直接返回 cookies。这样可以绕过数据库连接问题。

1. 将登录结果直接返回，不调用 `save_session` 方法
2. 前端保存 cookies 到 localStorage
3. 使用时直接传入 cookies 而不是 userId

### 安全注意事项

请注意，数据库中存储了用户的密码，实际生产环境应对密码进行加密存储。 