import json
import time
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# 数据库连接配置 - 优先使用环境变量
DB_USER = os.environ.get("DB_USER", )
DB_PASSWORD = os.environ.get("DB_PASSWORD", )
DB_HOST = os.environ.get("DB_HOST", )
DB_PORT = os.environ.get("DB_PORT", )
DB_NAME = os.environ.get("DB_NAME", )

class PostgresManager:
    """
    PostgreSQL数据库管理器，用于存储和获取天翼云网盘的登录信息
    """
    def __init__(self):
        self.table_name = "tianyi_sessions"
        self.connection = None
        try:
            self.connection = psycopg2.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                dbname=DB_NAME
            )
            # 确保表存在
            self._ensure_table_exists()
            self.is_connected = True
            print("数据库连接成功")
        except Exception as e:
            print(f"数据库连接失败: {str(e)}")
            self.is_connected = False
    
    def _ensure_table_exists(self):
        """确保数据表存在，如果不存在则创建"""
        if not self.connection:
            return
            
        try:
            # 创建表的SQL
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS tianyi_sessions (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                user_id TEXT NOT NULL UNIQUE,
                cookies JSONB NOT NULL,
                username TEXT,
                password TEXT,
                created_at BIGINT NOT NULL,
                updated_at BIGINT NOT NULL
            );
            """
            
            # 创建索引的SQL
            create_index_sql = """
            CREATE INDEX IF NOT EXISTS idx_tianyi_sessions_user_id ON tianyi_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_tianyi_sessions_updated_at ON tianyi_sessions(updated_at);
            """
            
            # 执行SQL
            cursor = self.connection.cursor()
            cursor.execute(create_table_sql)
            cursor.execute(create_index_sql)
            self.connection.commit()
            cursor.close()
            
        except Exception as e:
            print(f"确保表存在时出错: {str(e)}")
            if self.connection:
                self.connection.rollback()
    
    def save_session(self, user_id, cookies, username="", password=""):
        """
        保存或更新会话信息
        
        Args:
            user_id: 用户标识符
            cookies: 登录会话的cookies (dict)
            username: 用户名 (可选)
            password: 密码 (可选，敏感数据，实际应该加密存储)
        
        Returns:
            bool: 是否保存成功
        """
        if not self.is_connected or not self.connection:
            print("数据库未连接，无法保存会话")
            return False
        
        try:
            # 检查是否已存在
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM tianyi_sessions WHERE user_id = %s", (user_id,))
            existing_record = cursor.fetchone()
            
            current_time = int(time.time())
            
            # 确保cookies是字符串
            if isinstance(cookies, dict):
                cookies_json = json.dumps(cookies)
            else:
                cookies_json = cookies
                
            if existing_record:
                # 记录已存在，更新
                update_sql = """
                UPDATE tianyi_sessions 
                SET cookies = %s, updated_at = %s
                """
                params = [cookies_json, current_time]
                
                # 如果提供了用户名和密码，也更新它们
                if username:
                    update_sql += ", username = %s"
                    params.append(username)
                if password:
                    update_sql += ", password = %s"
                    params.append(password)
                
                update_sql += " WHERE user_id = %s"
                params.append(user_id)
                
                cursor.execute(update_sql, params)
            else:
                # 记录不存在，插入
                insert_sql = """
                INSERT INTO tianyi_sessions (user_id, cookies, username, password, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    insert_sql, 
                    (user_id, cookies_json, username, password, current_time, current_time)
                )
            
            self.connection.commit()
            cursor.close()
            return True
            
        except Exception as e:
            print(f"保存会话失败: {str(e)}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_session(self, user_id):
        """
        获取会话信息
        
        Args:
            user_id: 用户标识符
        
        Returns:
            dict or None: 会话信息，如果不存在则返回None
        """
        if not self.is_connected or not self.connection:
            print("数据库未连接，无法获取会话")
            return None
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM tianyi_sessions WHERE user_id = %s", (user_id,))
            session = cursor.fetchone()
            cursor.close()
            
            if session:
                # 将行转换为字典
                session_dict = dict(session)
                
                # 解析cookies
                if "cookies" in session_dict and session_dict["cookies"]:
                    if isinstance(session_dict["cookies"], str):
                        session_dict["cookies"] = json.loads(session_dict["cookies"])
                return session_dict
            
            return None
            
        except Exception as e:
            print(f"获取会话失败: {str(e)}")
            return None
    
    def delete_session(self, user_id):
        """
        删除会话信息
        
        Args:
            user_id: 用户标识符
        
        Returns:
            bool: 是否删除成功
        """
        if not self.is_connected or not self.connection:
            print("数据库未连接，无法删除会话")
            return False
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM tianyi_sessions WHERE user_id = %s", (user_id,))
            self.connection.commit()
            cursor.close()
            return True
            
        except Exception as e:
            print(f"删除会话失败: {str(e)}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def list_sessions(self):
        """
        列出所有会话信息
        
        Returns:
            list: 会话列表
        """
        if not self.is_connected or not self.connection:
            print("数据库未连接，无法获取会话列表")
            return []
        
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("SELECT * FROM tianyi_sessions ORDER BY updated_at DESC")
            sessions = cursor.fetchall()
            cursor.close()
            
            # 处理结果
            result = []
            for session in sessions:
                session_dict = dict(session)
                if "cookies" in session_dict and session_dict["cookies"]:
                    if isinstance(session_dict["cookies"], str):
                        try:
                            session_dict["cookies"] = json.loads(session_dict["cookies"])
                        except json.JSONDecodeError:
                            session_dict["cookies"] = {}
                    elif not isinstance(session_dict["cookies"], dict):
                        session_dict["cookies"] = {}
                result.append(session_dict)
            
            return result
            
        except Exception as e:
            print(f"获取会话列表失败: {str(e)}")
            return []
    
    def __del__(self):
        """析构函数，关闭数据库连接"""
        if self.connection:
            self.connection.close()

# 为了向后兼容，保持类名不变
SupabaseManager = PostgresManager 