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

-- 添加注释
COMMENT ON TABLE tianyi_sessions IS '存储天翼云网盘登录会话信息';
COMMENT ON COLUMN tianyi_sessions.id IS '唯一标识符';
COMMENT ON COLUMN tianyi_sessions.user_id IS '用户标识符，通常是用户名或邮箱的MD5值';
COMMENT ON COLUMN tianyi_sessions.cookies IS '登录会话的cookies，JSON格式';
COMMENT ON COLUMN tianyi_sessions.username IS '用户名或邮箱';
COMMENT ON COLUMN tianyi_sessions.password IS '密码（敏感数据，实际应加密存储）';
COMMENT ON COLUMN tianyi_sessions.created_at IS '创建时间戳';
COMMENT ON COLUMN tianyi_sessions.updated_at IS '更新时间戳'; 