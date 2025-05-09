# 天翼云网盘API

这是一个简单的天翼云网盘API实现，基于Vercel无服务器函数和PostgreSQL数据库。支持自动登录，无需每次操作重新登录。

## 功能特点

- 天翼云网盘自动登录和会话管理
- 文件和文件夹浏览
- 自动处理登录会话失效问题
- 会话持久化存储（使用PostgreSQL数据库）
- 简洁直观的Web界面
- 支持通过环境变量配置账号密码
- 支持验证码识别和会话管理

## 环境变量配置

复制 `env.example` 文件为 `.env`，然后填入以下信息：

```
# 天翼云账号密码
TIANYI_USERNAME=你的天翼云账号
TIANYI_PASSWORD=你的天翼云密码

# 数据库配置（已有默认值，可选修改）
DB_USER=postgres.XXXXXXXXXXXXXXXXXX
DB_PASSWORD=XXXXXXXXXXXXXXXXXXX
DB_HOST=XXXXXXXXXXXXX
DB_PORT=6543
DB_NAME=postgres

# 默认展示的目录ID，默认为根目录
DEFAULT_FOLDER_ID=-11
```

将环境变量部署到Vercel，或在本地开发时自动加载。

> 本项目原理为使用数据库内的长Cookie请求天翼云获取文件列表以及下载链接。因为本人环境太干净没法做带验证码登录的情况，如果遇到验证码问题请自行实现，或者本地抓包获取长Cookie手动写入数据库

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

### 验证码和登录接口

**URL**: `/api/login`
**方法**: `POST`
**请求体**:

```json
{
  "force": true  // 强制重新登录
}
```

**URL**: `/api/refresh`
**方法**: `POST`
**用途**: 获取验证码图片

**URL**: `/api/captcha/login`
**方法**: `POST`
**请求体**:

```json
{
  "validateCode": "验证码内容",
  "captchaToken": "验证码token",
  "lt": "lt值",
  "reqId": "请求ID",
  "appId": "应用ID"
}
```

### 会话管理接口

**URL**: `/api/sessions`
**方法**: `GET`
**用途**: 获取所有保存的会话

**URL**: `/api/sessions/save`
**方法**: `POST`
**请求体**:

```json
{
  "userId": "用户ID",
  "cookies": {} // cookies对象
}
```

**URL**: `/api/sessions/delete`
**方法**: `POST`
**请求体**:

```json
{
  "userId": "要删除的用户ID"
}
```

## 调试页面

系统提供了一个调试页面用于测试天翼云验证码功能和会话管理：

**URL**: `/debug.html`

调试页面功能：
- 强制登录测试：触发完整登录流程，包括验证码处理
- 获取验证码：专门用于获取验证码图片进行测试
- 提交验证码：测试验证码的识别和提交
- 会话管理：查看、保存和删除会话信息
- 环境变量测试：检查系统环境变量配置状态

**注意**：调试页面仅供开发测试使用，在生产环境中应当限制访问。

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
- 点击文件名：下载对应文件

### 验证码处理

当登录需要验证码时，系统会自动弹出验证码输入框。输入正确的验证码后，系统将自动完成登录流程并刷新文件列表。

### 安全说明

- 该项目不会在前端显示敏感信息，如账号密码
- 登录凭证（Cookies）会保存在数据库中以便后续使用
- 在生产环境中，建议限制对调试页面（`/debug.html`）的访问

## 数据库设计

系统使用PostgreSQL数据库存储会话信息。主要表结构：

- `tianyi_sessions`: 存储用户会话信息，包括cookies、用户ID等

详细的数据库设置请参考 `db_setup.md` 和 `create_table.sql` 文件。