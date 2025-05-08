from http.server import BaseHTTPRequestHandler
import base64
import json
import re
import urllib.parse
import hashlib
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import requests
import random
import time
import os
from api.db_manager import SupabaseManager

# 从环境变量获取天翼云账号，避免在代码中硬编码
# 若需配置，请设置环境变量TIANYI_USERNAME和TIANYI_PASSWORD
TIANYI_USERNAME = os.environ.get("TIANYI_USERNAME", "")
TIANYI_PASSWORD = os.environ.get("TIANYI_PASSWORD", "")
DEFAULT_USER_ID = "default_user"  # 默认用户ID，用于存储会话
# 从环境变量获取默认文件夹ID，默认为根目录
DEFAULT_FOLDER_ID = os.environ.get("DEFAULT_FOLDER_ID", "-11")

class handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # 初始化数据库管理器
        self.db_manager = SupabaseManager()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path.startswith('/api/files'):
            path_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            user_id = path_params.get('userId', [''])[0] or DEFAULT_USER_ID
            cookie_str = path_params.get('cookies', [''])[0]
            folder_id = path_params.get('folderId', [DEFAULT_FOLDER_ID])[0]  # 使用环境变量中的默认文件夹ID
            
            # 优先使用userId从数据库获取cookies
            cookies = None
            session = None
            if user_id:
                session = self.db_manager.get_session(user_id)
                if session and 'cookies' in session:
                    cookies = session['cookies']
            
            # 如果没有userId或者数据库中没有对应的cookies，则使用传入的cookies
            if not cookies and cookie_str:
                try:
                    cookies = json.loads(cookie_str)
                except:
                    pass
            
            # 如果仍然没有cookies，尝试使用默认账号登录
            if not cookies:
                login_result = self.cloud189_login(TIANYI_USERNAME, TIANYI_PASSWORD)
                if login_result.get('status') == 'success' and 'data' in login_result and 'cookies' in login_result['data']:
                    cookies = login_result['data']['cookies']
                    # 保存cookies到数据库
                    self.db_manager.save_session(
                        user_id=DEFAULT_USER_ID,
                        cookies=cookies,
                        username=TIANYI_USERNAME,
                        password=TIANYI_PASSWORD
                    )
            
            if not cookies:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "无法获取登录凭证"}).encode('utf-8'))
                return
            
            try:
                username = session.get('username', TIANYI_USERNAME) if session else TIANYI_USERNAME
                password = session.get('password', TIANYI_PASSWORD) if session else TIANYI_PASSWORD
                files_result = self.get_files(cookies, folder_id, username, password)
                
                # 如果是自动刷新的情况，更新数据库中的cookies
                if files_result.get('status') == 'need_refresh' and 'data' in files_result and 'cookies' in files_result['data']:
                    self.db_manager.save_session(user_id, files_result['data']['cookies'])
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(files_result).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
        elif self.path.startswith('/api/download'):
            # 处理下载请求
            path_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            file_id = path_params.get('fileId', [''])[0]
            user_id = path_params.get('userId', [''])[0] or DEFAULT_USER_ID
            
            if not file_id:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "文件ID不能为空"}).encode('utf-8'))
                return
            
            # 获取会话cookies
            cookies = None
            session = None
            if user_id:
                session = self.db_manager.get_session(user_id)
                if session and 'cookies' in session:
                    cookies = session['cookies']
            
            if not cookies:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "无法获取登录凭证"}).encode('utf-8'))
                return
            
            # 获取下载链接
            try:
                download_link = self.get_download_link(cookies, file_id)
                
                # 如果成功获取下载链接，返回下载链接信息
                if download_link.get('status') == 'success':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(download_link).encode('utf-8'))
                else:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(download_link).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": f"获取下载链接失败: {str(e)}"}).encode('utf-8'))
        elif self.path.startswith('/api/sessions'):
            # 获取所有会话列表
            sessions = self.db_manager.list_sessions()
            # 敏感信息处理，去除密码字段
            for session in sessions:
                if 'password' in session:
                    session['password'] = '******' if session['password'] else ''
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "data": sessions}).encode('utf-8'))
        elif self.path == '/api/auto-login':
            # 自动登录接口，使用默认账号
            login_result = self.cloud189_login(TIANYI_USERNAME, TIANYI_PASSWORD)
            
            if login_result.get('status') == 'success' and 'data' in login_result and 'cookies' in login_result['data']:
                # 保存到数据库
                self.db_manager.save_session(
                    user_id=DEFAULT_USER_ID,
                    cookies=login_result['data']['cookies'],
                    username=TIANYI_USERNAME,
                    password=TIANYI_PASSWORD
                )
                # 设置用户ID
                login_result['data']['userId'] = DEFAULT_USER_ID
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(login_result).encode('utf-8'))
        elif self.path == '/api/config':
            # 返回配置信息，包括默认文件夹ID
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success",
                "data": {
                    "defaultFolderId": DEFAULT_FOLDER_ID,
                    "rootFolderId": "-11"  # 根目录ID
                }
            }).encode('utf-8'))
        else:
            self.send_response(200)
            self.send_header('Content-type','text/plain')
            self.end_headers()
            self.wfile.write('Hello, world!'.encode('utf-8'))
        return
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        request_body = json.loads(post_data.decode('utf-8'))
        
        # 处理登录请求
        if self.path == '/api/login':
            # 使用请求中的用户名和密码，如果没有提供则使用默认账号
            username = request_body.get('username', TIANYI_USERNAME)
            password = request_body.get('password', TIANYI_PASSWORD)
            validate_code = request_body.get('validateCode', '')
            remember = request_body.get('remember', True)
            
            # 其他登录参数，可能来自验证码请求
            captcha_token = request_body.get('captchaToken', '')
            lt = request_body.get('lt', '')
            req_id = request_body.get('reqId', '')
            app_id = request_body.get('appId', '')
            
            login_result = self.cloud189_login(username, password, validate_code)
            
            # 如果登录成功且需要记住登录信息，保存到数据库
            if login_result.get('status') == 'success' and remember and 'data' in login_result and 'cookies' in login_result['data']:
                # 如果使用的是默认账号，用默认用户ID，否则使用用户名的MD5值
                if username == TIANYI_USERNAME and password == TIANYI_PASSWORD:
                    user_id = DEFAULT_USER_ID
                else:
                    user_id = self.generate_user_id(username)
                
                saved = self.db_manager.save_session(
                    user_id=user_id,
                    cookies=login_result['data']['cookies'],
                    username=username if remember else "",
                    password=password if remember else ""
                )
                if saved:
                    login_result['data']['userId'] = user_id
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(login_result).encode('utf-8'))
        # 处理文件列表请求
        elif self.path == '/api/files':
            user_id = request_body.get('userId', DEFAULT_USER_ID)
            cookies = request_body.get('cookies', {})
            folder_id = request_body.get('folderId', DEFAULT_FOLDER_ID)  # 使用环境变量中的默认文件夹ID
            username = request_body.get('username', '')
            password = request_body.get('password', '')
            
            # 如果提供了userId，从数据库获取会话信息
            if user_id:
                session = self.db_manager.get_session(user_id)
                if session:
                    cookies = session.get('cookies', cookies)
                    username = session.get('username', username)
                    password = session.get('password', password)
            
            # 如果仍然没有cookies或用户名密码，使用默认账号
            if not cookies:
                login_result = self.cloud189_login(TIANYI_USERNAME, TIANYI_PASSWORD)
                if login_result.get('status') == 'success' and 'data' in login_result and 'cookies' in login_result['data']:
                    cookies = login_result['data']['cookies']
                    username = TIANYI_USERNAME
                    password = TIANYI_PASSWORD
                    # 保存cookies到数据库
                    self.db_manager.save_session(
                        user_id=DEFAULT_USER_ID,
                        cookies=cookies,
                        username=TIANYI_USERNAME,
                        password=TIANYI_PASSWORD
                    )
                # 如果需要验证码，返回需要验证码的提示
                elif login_result.get('status') == 'need_captcha':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(login_result).encode('utf-8'))
                    return
            
            if not cookies:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "无法获取登录凭证"}).encode('utf-8'))
                return
            
            files_result = self.get_files(cookies, folder_id, username, password)
            
            # 如果是自动刷新的情况，更新数据库中的cookies
            if files_result.get('status') == 'need_refresh' and 'data' in files_result and 'cookies' in files_result['data']:
                self.db_manager.save_session(user_id, files_result['data']['cookies'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(files_result).encode('utf-8'))
        # 处理刷新登录请求
        elif self.path == '/api/refresh':
            user_id = request_body.get('userId', DEFAULT_USER_ID)
            username = request_body.get('username', '')
            password = request_body.get('password', '')
            validate_code = request_body.get('validateCode', '')
            
            # 如果提供了userId，从数据库获取用户名和密码
            if user_id:
                session = self.db_manager.get_session(user_id)
                if session:
                    username = session.get('username', username)
                    password = session.get('password', password)
            
            # 如果没有用户名密码，使用默认账号
            if not username or not password:
                username = TIANYI_USERNAME
                password = TIANYI_PASSWORD
            
            login_result = self.cloud189_login(username, password, validate_code)
            
            # 如果登录成功，更新数据库
            if login_result.get('status') == 'success' and 'data' in login_result and 'cookies' in login_result['data']:
                self.db_manager.save_session(user_id, login_result['data']['cookies'])
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(login_result).encode('utf-8'))
        # 验证码验证登录
        elif self.path == '/api/captcha/login':
            username = request_body.get('username', TIANYI_USERNAME)
            password = request_body.get('password', TIANYI_PASSWORD)
            validate_code = request_body.get('validateCode', '')
            captcha_token = request_body.get('captchaToken', '')
            lt = request_body.get('lt', '')
            req_id = request_body.get('reqId', '')
            app_id = request_body.get('appId', '')
            remember = request_body.get('remember', True)
            
            if not validate_code:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "验证码不能为空"}).encode('utf-8'))
                return
            
            login_result = self.cloud189_login(username, password, validate_code)
            
            # 如果登录成功且需要记住登录信息，保存到数据库
            if login_result.get('status') == 'success' and remember and 'data' in login_result and 'cookies' in login_result['data']:
                # 如果使用的是默认账号，用默认用户ID，否则使用用户名的MD5值
                if username == TIANYI_USERNAME and password == TIANYI_PASSWORD:
                    user_id = DEFAULT_USER_ID
                else:
                    user_id = self.generate_user_id(username)
                
                self.db_manager.save_session(
                    user_id=user_id,
                    cookies=login_result['data']['cookies'],
                    username=username if remember else "",
                    password=password if remember else ""
                )
                login_result['data']['userId'] = user_id
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(login_result).encode('utf-8'))
        # 删除会话
        elif self.path == '/api/sessions/delete':
            user_id = request_body.get('userId', '')
            
            if not user_id:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "需要userId参数"}).encode('utf-8'))
                return
            
            deleted = self.db_manager.delete_session(user_id)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "success" if deleted else "error",
                "message": "会话已删除" if deleted else "删除会话失败"
            }).encode('utf-8'))
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))
    
    def generate_user_id(self, username):
        """生成唯一的用户ID，使用用户名的MD5值"""
        md5 = hashlib.md5()
        md5.update(username.encode('utf-8'))
        return md5.hexdigest()
    
    def random_str(self):
        return '0.' + str(random.randint(0, 9999999999999999))
    
    def get_files(self, cookies, folder_id=None, username='', password=''):
        # 如果没有提供文件夹ID，使用默认文件夹ID
        if folder_id is None:
            folder_id = DEFAULT_FOLDER_ID
            
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'Referer': 'https://cloud.189.cn/',
            'Accept': 'application/json;charset=UTF-8'
        })
        
        # 设置cookie
        for key, value in cookies.items():
            session.cookies.set(key, value)
        
        file_list = []
        folder_list = []
        page_num = 1
        
        try:
            while True:
                params = {
                    'noCache': self.random_str(),
                    'pageSize': '60',
                    'pageNum': str(page_num),
                    'mediaType': '0',
                    'folderId': folder_id,
                    'iconOption': '5',
                    'orderBy': 'lastOpTime',
                    'descending': 'true'
                }
                
                response = session.get('https://cloud.189.cn/api/open/file/listFiles.action', params=params)
                
                # 检查登录状态，如果登录失效则尝试重新登录
                if 'InvalidSessionKey' in response.text or response.status_code == 401:
                    # 如果提供了用户名和密码，尝试重新登录
                    if username and password:
                        login_result = self.cloud189_login(username, password)
                        if login_result.get('status') == 'success':
                            # 更新cookies
                            new_cookies = login_result.get('data', {}).get('cookies', {})
                            # 返回结果中包含新cookies和需要刷新的信息
                            return {
                                "status": "need_refresh",
                                "message": "登录已刷新，请重新获取文件列表",
                                "data": {
                                    "cookies": new_cookies
                                }
                            }
                    return {"status": "error", "message": "登录已失效，请重新登录"}
                
                result = response.json()
                
                # 检查是否有错误码
                if result.get('res_code') and result.get('res_code') != 0:
                    return {"status": "error", "message": result.get('res_message', '获取文件列表失败')}
                
                # 检查文件列表是否为空
                file_list_ao = result.get('fileListAO', {})
                if not file_list_ao or file_list_ao.get('count', 0) == 0:
                    break
                
                # 处理文件列表
                for folder in file_list_ao.get('folderList', []):
                    folder_list.append({
                        'id': str(folder.get('id', '')),
                        'name': folder.get('name', ''),
                        'lastOpTime': folder.get('lastOpTime', ''),
                        'type': 'folder'
                    })
                
                for file in file_list_ao.get('fileList', []):
                    file_list.append({
                        'id': str(file.get('id', '')),
                        'name': file.get('name', ''),
                        'lastOpTime': file.get('lastOpTime', ''),
                        'size': file.get('size', 0),
                        'icon': file.get('icon', {}).get('smallUrl', ''),
                        'type': 'file'
                    })
                
                # 检查是否有更多页
                if len(file_list_ao.get('folderList', [])) == 0 and \
                   len(file_list_ao.get('fileList', [])) == 0:
                    break
                
                page_num += 1
                # 限制最多获取5页数据，避免过多请求
                if page_num > 5:
                    break
            
            return {
                "status": "success",
                "data": {
                    "folders": folder_list,
                    "files": file_list,
                    "folderId": folder_id
                }
            }
            
        except Exception as e:
            return {"status": "error", "message": f"获取文件列表出错: {str(e)}"}
    
    def cloud189_login(self, username, password, validateCode=""):
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'Referer': 'https://cloud.189.cn/'
        })
        
        # 敏感账号信息 - 用于日志显示
        masked_username = self._mask_sensitive_info(username)
        
        # 访问登录URL获取重定向
        url = "https://cloud.189.cn/api/portal/loginUrl.action?redirectURL=https%3A%2F%2Fcloud.189.cn%2Fmain.action"
        res = session.get(url)
        
        # 检查是否已经登录
        redirect_url = res.url
        if redirect_url == "https://cloud.189.cn/web/main":
            # 获取cookies
            cookies_dict = {name: value for name, value in session.cookies.items()}
            return {
                "status": "success",
                "message": "已登录",
                "data": {
                    "cookies": cookies_dict
                }
            }
        
        # 获取登录参数
        lt = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_url).query).get('lt', [''])[0]
        req_id = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_url).query).get('reqId', [''])[0]
        app_id = urllib.parse.parse_qs(urllib.parse.urlparse(redirect_url).query).get('appId', [''])[0]
        
        if not lt or not app_id:
            return {"status": "error", "message": "获取登录参数失败"}
        
        headers = {
            'lt': lt,
            'reqid': req_id,
            'referer': redirect_url,
            'origin': 'https://open.e.189.cn'
        }
        
        # 获取验证码Token和图片
        captcha_token = ""
        need_captcha = False
        
        try:
            # 检查是否需要验证码
            check_url = "https://open.e.189.cn/api/logbox/oauth2/needcaptcha.do"
            check_data = {
                'accountType': '01',
                'userName': username
            }
            check_res = session.post(check_url, headers=headers, data=check_data)
            check_result = check_res.json()
            
            # 防止check_result是整数而不是字典
            need_captcha = False
            if isinstance(check_result, dict):
                need_captcha = check_result.get('needCaptcha', False)
            elif isinstance(check_result, (int, bool)):
                need_captcha = bool(check_result)
                
            if need_captcha:
                # 获取验证码Token
                html_res = session.get(redirect_url)
                html_content = html_res.text
                
                # 使用正则表达式查找captchaToken
                import re
                token_match = re.search(r"captchaToken' value='(.+?)'", html_content)
                if token_match:
                    captcha_token = token_match.group(1)
                
                vcode_match = re.search(r"picCaptcha\.do\?token=([A-Za-z0-9&=]+)", html_content)
                if vcode_match:
                    vcode_id = vcode_match.group(1)
                    
                    # 获取验证码图片
                    timestamp = str(int(time.time() * 1000))
                    captcha_url = f"https://open.e.189.cn/api/logbox/oauth2/picCaptcha.do?token={vcode_id}{timestamp}"
                    captcha_res = session.get(captcha_url, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
                        'Referer': 'https://open.e.189.cn/api/logbox/oauth2/unifyAccountLogin.do',
                    })
                    
                    # 如果没有提供验证码，则返回验证码图片供用户输入
                    if not validateCode:
                        try:
                            captcha_base64 = base64.b64encode(captcha_res.content).decode('utf-8')
                            print(f"验证码图片大小: {len(captcha_res.content)} 字节")
                            response_data = {
                                "status": "need_captcha",
                                "message": "需要验证码",
                                "data": {
                                    "captcha_token": captcha_token,
                                    "captcha_image": captcha_base64,
                                    "lt": lt,
                                    "req_id": req_id,
                                    "app_id": app_id
                                }
                            }
                            return response_data
                        except Exception as img_e:
                            print(f"处理验证码图片失败: {str(img_e)}")
                            # 返回错误但不包含验证码图片
                            return {
                                "status": "error",
                                "message": f"获取验证码图片失败: {str(img_e)}"
                            }
        except Exception as e:
            # 如果获取验证码过程出错，继续尝试登录
            print(f"获取验证码失败: {str(e)}")
            pass
        
        # 获取应用配置
        app_conf_data = {
            'version': '2.0',
            'appKey': app_id
        }
        app_conf_res = session.post('https://open.e.189.cn/api/logbox/oauth2/appConf.do', 
                                headers=headers, 
                                data=app_conf_data)
        app_conf = app_conf_res.json()
        
        if app_conf.get('result') != '0':
            return {"status": "error", "message": app_conf.get('msg', '获取应用配置失败')}
        
        # 获取加密配置
        encrypt_conf_data = {
            'appId': app_id
        }
        encrypt_conf_res = session.post('https://open.e.189.cn/api/logbox/config/encryptConf.do',
                                    headers=headers,
                                    data=encrypt_conf_data)
        encrypt_conf = encrypt_conf_res.json()
        
        if encrypt_conf.get('result') != 0:
            return {"status": "error", "message": "获取加密配置失败"}
        
        # 使用RSA加密用户名和密码
        pre = encrypt_conf['data']['pre']
        pub_key = encrypt_conf['data']['pubKey']
        
        username_encrypted = pre + self.rsa_encode(username.encode(), pub_key, True)
        password_encrypted = pre + self.rsa_encode(password.encode(), pub_key, True)
        
        # 提交登录请求
        login_data = {
            'version': 'v2.0',
            'apToken': '',
            'appKey': app_id,
            'accountType': app_conf['data']['accountType'],
            'userName': username_encrypted,
            'epd': password_encrypted,
            'captchaType': '1' if need_captcha else '',
            'validateCode': validateCode,
            'smsValidateCode': '',
            'captchaToken': captcha_token,
            'returnUrl': app_conf['data']['returnUrl'],
            'mailSuffix': app_conf['data']['mailSuffix'],
            'dynamicCheck': 'FALSE',
            'clientType': str(app_conf['data']['clientType']),
            'cb_SaveName': '3',
            'isOauth2': str(app_conf['data']['isOauth2']).lower(),
            'state': '',
            'paramId': app_conf['data']['paramId']
        }
        
        login_res = session.post('https://open.e.189.cn/api/logbox/oauth2/loginSubmit.do',
                              headers=headers,
                              data=login_data)
        login_result = login_res.json()
        
        if login_result.get('result') != 0:
            error_msg = login_result.get('msg', '登录失败')
            
            # 检查是否是验证码错误
            if '验证码' in error_msg:
                # 如果验证码错误但之前没有要求验证码，尝试重新获取验证码
                if not need_captcha and not validateCode:
                    return self.cloud189_login(username, password)
                
                # 如果已经尝试了验证码但仍然失败，返回错误信息
                try:
                    # 重新获取验证码图片
                    timestamp = str(int(time.time() * 1000))
                    captcha_url = f"https://open.e.189.cn/api/logbox/oauth2/picCaptcha.do?token={lt}{timestamp}"
                    captcha_res = session.get(captcha_url, headers=headers)
                    captcha_base64 = base64.b64encode(captcha_res.content).decode('utf-8')
                    
                    return {
                        "status": "need_captcha",
                        "message": error_msg,
                        "data": {
                            "captcha_token": captcha_token,
                            "captcha_image": captcha_base64,
                            "lt": lt,
                            "req_id": req_id,
                            "app_id": app_id
                        }
                    }
                except Exception as img_e:
                    print(f"获取新验证码图片失败: {str(img_e)}")
                    return {
                        "status": "need_captcha",
                        "message": error_msg,
                        "data": {
                            "captcha_token": captcha_token,
                            "lt": lt,
                            "req_id": req_id,
                            "app_id": app_id
                        }
                    }
            
            return {"status": "error", "message": error_msg}
        
        # 如果有toUrl，需要访问这个URL完成登录流程
        to_url = login_result.get('toUrl')
        if to_url:
            session.get(to_url)
        
        # 获取cookies
        cookies_dict = {name: value for name, value in session.cookies.items()}
        
        return {
            "status": "success",
            "message": "登录成功",
            "data": {
                "cookies": cookies_dict
            }
        }
    
    def rsa_encode(self, data, public_key, use_hex=False):
        # 处理公钥格式
        public_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
        rsa_key = RSA.importKey(public_key)
        cipher = PKCS1_v1_5.new(rsa_key)
        
        # 加密数据
        encrypted = cipher.encrypt(data)
        b64_str = base64.b64encode(encrypted).decode('utf-8')
        
        if use_hex:
            return self.b64_to_hex(b64_str)
        return b64_str
    
    def b64_to_hex(self, b64_str):
        b64map = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        bi_rm = "0123456789abcdefghijklmnopqrstuvwxyz"
        
        result = ""
        e = 0
        c = 0
        
        for char in b64_str:
            if char != "=":
                v = b64map.index(char)
                if e == 0:
                    e = 1
                    result += bi_rm[v >> 2]
                    c = 3 & v
                elif e == 1:
                    e = 2
                    result += bi_rm[(c << 2) | (v >> 4)]
                    c = 15 & v
                elif e == 2:
                    e = 3
                    result += bi_rm[c]
                    result += bi_rm[v >> 2]
                    c = 3 & v
                else:
                    e = 0
                    result += bi_rm[(c << 2) | (v >> 4)]
                    result += bi_rm[15 & v]
        
        if e == 1:
            result += bi_rm[c << 2]
        
        return result

    def get_download_link(self, cookies, file_id):
        """获取文件下载链接"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'Referer': 'https://cloud.189.cn/',
            'Accept': 'application/json;charset=UTF-8'
        })
        
        # 设置cookie
        for key, value in cookies.items():
            session.cookies.set(key, value)
        
        try:
            # 获取文件信息
            file_info_url = 'https://cloud.189.cn/api/portal/getFileInfo.action'
            response = session.get(file_info_url, params={
                'fileId': file_id
            })
            
            if response.status_code != 200:
                return {
                    "status": "error",
                    "message": f"获取文件信息失败，状态码: {response.status_code}"
                }
            
            file_info = response.json()
            
            # 检查错误码
            if 'res_code' in file_info and file_info['res_code'] != 0:
                return {
                    "status": "error",
                    "message": file_info.get('res_message', '获取文件信息失败')
                }
            
            # 获取下载URL - 检查不同字段名
            download_url = None
            if 'downloadUrl' in file_info:
                download_url = file_info['downloadUrl']
            elif 'fileDownloadUrl' in file_info:
                download_url = file_info['fileDownloadUrl']
            
            if not download_url:
                return {
                    "status": "error",
                    "message": "无法获取下载链接，接口返回数据不包含下载URL"
                }
            
            # 处理URL确保使用https
            if download_url.startswith('//'):
                download_url = 'https:' + download_url
            elif not download_url.startswith('http'):
                download_url = 'https://' + download_url
            
            # 跟随重定向获取真实下载链接
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
            })
            
            # 禁用重定向自动跟随，手动处理重定向
            response = session.get(download_url, allow_redirects=False)
            
            # 如果有重定向，获取重定向URL
            real_download_url = download_url
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_url = response.headers.get('Location', '')
                
                if redirect_url:
                    # 再次检查重定向
                    real_download_url = redirect_url
                    
                    # 跟踪最多3次重定向
                    max_redirects = 3
                    redirect_count = 0
                    
                    while redirect_count < max_redirects:
                        try:
                            redirect_response = session.get(real_download_url, allow_redirects=False)
                            if redirect_response.status_code in (301, 302, 303, 307, 308):
                                new_redirect = redirect_response.headers.get('Location', '')
                                if new_redirect:
                                    real_download_url = new_redirect
                                    redirect_count += 1
                                else:
                                    break
                            else:
                                break
                        except Exception:
                            break
            
            # 确保URL使用https
            real_download_url = real_download_url.replace('http://', 'https://')
            
            # 获取文件名
            file_name = None
            if 'fileName' in file_info:
                file_name = file_info['fileName']
            elif 'name' in file_info:
                file_name = file_info['name']
            
            if not file_name:
                file_name = f'文件_{file_id}'
            
            return {
                "status": "success",
                "data": {
                    "url": real_download_url,
                    "fileName": file_name,
                    "fileId": file_id
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"获取下载链接失败: {str(e)}"
            }

    def _mask_sensitive_info(self, text):
        """隐藏敏感信息，如用户名、账号等"""
        if not text:
            return "***"
        
        # 隐藏电子邮件
        if '@' in text:
            parts = text.split('@')
            username = parts[0]
            domain = parts[1]
            
            if len(username) > 3:
                masked_username = username[:2] + '*' * (len(username) - 3) + username[-1]
            else:
                masked_username = username[0] + '*' * (len(username) - 1) 
                
            return f"{masked_username}@{domain}"
        
        # 隐藏手机号码
        if len(text) == 11 and text.isdigit():
            return text[:3] + '****' + text[7:]
        
        # 隐藏其他类型的文本
        if len(text) > 3:
            return text[0] + '*' * (len(text) - 2) + text[-1]
        else:
            return text[0] + '*' * (len(text) - 1)