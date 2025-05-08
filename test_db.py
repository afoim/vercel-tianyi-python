import psycopg2
import os

# 数据库连接配置
DB_USER = os.environ.get("DB_USER", )
DB_PASSWORD = os.environ.get("DB_PASSWORD", )
DB_HOST = os.environ.get("DB_HOST", )
DB_PORT = os.environ.get("DB_PORT", )
DB_NAME = os.environ.get("DB_NAME", )

print("正在连接数据库...")
print(f"连接信息: {DB_HOST}:{DB_PORT}, 用户: {DB_USER}")

try:
    connection = psycopg2.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME
    )
    print("数据库连接成功!")
    
    # 测试查询
    cursor = connection.cursor()
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print("当前时间:", result)
    
    # 测试tianyi_sessions表
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tianyi_sessions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id TEXT NOT NULL UNIQUE,
            cookies JSONB NOT NULL,
            username TEXT,
            password TEXT,
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL
        );
        """)
        connection.commit()
        print("tianyi_sessions表创建或已存在")
        
        # 插入测试数据
        cursor.execute("""
        INSERT INTO tianyi_sessions (user_id, cookies, username, password, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
        """, ('test_user', '{"test":"cookie"}', 'test_username', 'test_password', 1625097600, 1625097600))
        connection.commit()
        print("测试数据插入成功")
        
        # 查询测试数据
        cursor.execute("SELECT * FROM tianyi_sessions")
        rows = cursor.fetchall()
        print(f"共有 {len(rows)} 条会话记录")
        
    except Exception as table_error:
        print(f"表操作失败: {table_error}")
        connection.rollback()
    
    # 关闭连接
    cursor.close()
    connection.close()
    print("数据库连接已关闭")
    
except Exception as e:
    print(f"连接失败: {e}") 