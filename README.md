# 天翼云网盘API

这是一个简单的天翼云网盘API实现，基于Vercel无服务器函数和PostgreSQL数据库。支持自动登录，无需每次操作重新登录。

## 功能特点

- 天翼云网盘自动登录和会话管理
- 文件和文件夹浏览
- 自动处理登录会话失效问题
- 会话持久化存储（使用PostgreSQL数据库）
- 简洁直观的Web界面
- 支持通过环境变量配置账号密码

## 环境变量配置

复制 `env.example` 文件为 `.env`，然后填入以下信息：

```
# 天翼云账号密码
TIANYI_USERNAME=你的天翼云账号
TIANYI_PASSWORD=你的天翼云密码

# 数据库配置（已有默认值，可选修改）
DB_USER=postgres.aounyouknclwcjjnseqz
DB_PASSWORD=WnDry41tMptHopMi
DB_HOST=aws-0-us-east-2.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres

# 默认展示的目录ID，默认为根目录
DEFAULT_FOLDER_ID=-11
```

将环境变量部署到Vercel，或在本地开发时自动加载。

### 自定义默认文件夹

可以通过修改 `DEFAULT_FOLDER_ID` 环境变量来设置应用启动时默认展示的文件夹：

- `-11`: 根目录（默认值）
- 其他值: 天翼云网盘中的其他文件夹ID

要获取特定文件夹的ID，可以先浏览到该文件夹，然后查看浏览器地址栏或网络请求中的folderId参数。

## API接口

### 自动登录接口

**URL**: `/api/auto-login`
**方法**: `GET`

**响应**:

```json
{
  "status": "success",
  "message": "登录成功",
  "data": {
    "cookies": {
      // 登录后的cookies
    },
    "userId": "default_user"
  }
}
```

### 获取文件列表接口

**URL**: `/api/files`
**方法**: `POST`
**请求体**:

```json
{
  "userId": "default_user", // 默认用户ID
  "folderId": "-11" // 可选，默认为根目录
}
```

**URL方式调用**: `/api/files?userId=default_user&folderId=-11`
**方法**: `GET`

**响应**:

```json
{
  "status": "success",
  "data": {
    "folders": [
      {
        "id": "folder_id",
        "name": "文件夹名称",
        "lastOpTime": "最后操作时间",
        "type": "folder"
      }
    ],
    "files": [
      {
        "id": "file_id",
        "name": "文件名",
        "lastOpTime": "最后操作时间",
        "size": 文件大小,
        "icon": "图标URL",
        "type": "file"
      }
    ],
    "folderId": "当前文件夹ID"
  }
}
```

## 本地开发

1. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

2. 复制 `env.example` 为 `.env` 并填写相关信息

3. 使用Vercel CLI进行本地开发：
   ```
   vercel dev
   ```

## 部署

1. 将代码推送到GitHub

2. 在Vercel上连接仓库并部署

3. 在Vercel项目设置中添加环境变量:
   - `TIANYI_USERNAME` - 天翼云账号
   - `TIANYI_PASSWORD` - 天翼云密码
   - `DEFAULT_FOLDER_ID` - 默认展示的文件夹ID（可选，默认为根目录"-11"）
   - 其他数据库相关环境变量（如有必要）

## 使用说明

访问部署后的网址，系统会自动登录并显示文件列表。无需任何用户交互。

### 页面操作

- 点击文件夹：进入对应文件夹
- 点击"返回上一级"：返回上级文件夹
- 点击"刷新文件列表"：重新获取当前文件夹内容
- 点击"刷新登录"：强制重新登录