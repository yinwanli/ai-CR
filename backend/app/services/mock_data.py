"""
Mock Data Service for Demo Testing
Provides static mock data for testing and demonstration purposes.
"""
from typing import Dict, Any, List


class MockDataService:
    """Service class providing mock data for demo testing."""

    @staticmethod
    def get_mock_requirement(jira_key: str) -> str:
        """
        Returns mock requirement document based on jira_key.

        Args:
            jira_key: JIRA ticket identifier (e.g., PROJ-123, DMP-456)

        Returns:
            Mock requirement document content
        """
        mock_requirements = {
            "PROJ-123": """
# 需求文档: PROJ-123 - 用户登录功能

## 1. 功能概述
实现用户登录功能，支持用户名密码登录，确保系统安全性。

## 2. 功能需求

### 2.1 登录验证
- 用户输入用户名和密码
- 系统验证用户名和密码是否匹配
- 密码错误次数超过5次，锁定账户30分钟
- 登录成功后生成Token，有效期2小时

### 2.2 输入校验
- 用户名: 3-20个字符，只允许字母、数字、下划线
- 密码: 6-20个字符，必须包含字母和数字
- 用户名和密码不能为空

### 2.3 安全要求
- 密码必须加密存储，使用bcrypt算法
- Token使用JWT格式，包含用户ID和过期时间
- 登录日志记录IP地址和登录时间
- 异常登录检测: 同一IP 10分钟内失败超过3次需验证码

### 2.4 异常处理
- 用户不存在: 提示"用户名或密码错误"（不暴露具体原因）
- 密码错误: 提示"用户名或密码错误"
- 账户锁定: 提示"账户已锁定，请30分钟后重试"
- 数据库连接失败: 记录日志，返回"系统繁忙，请稍后重试"

### 2.5 响应格式
成功响应:
```json
{
    "code": 200,
    "message": "登录成功",
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "expire_at": "2024-01-01T12:00:00Z"
    }
}
```

失败响应:
```json
{
    "code": 401,
    "message": "用户名或密码错误",
    "data": null
}
```

## 3. 验收标准
- [ ] 支持正确用户名密码登录
- [ ] 用户名格式校验正确
- [ ] 密码格式校验正确
- [ ] 密码错误5次后账户锁定
- [ ] Token生成和验证正确
- [ ] 异常情况处理正确
""",

            "DMP-456": """
# 需求文档: DMP-456 - 订单创建功能

## 1. 功能概述
实现用户创建订单功能，支持商品下单、优惠计算、库存检查。

## 2. 功能需求

### 2.1 订单创建流程
- 用户选择商品和数量
- 系统检查库存是否充足
- 计算订单总金额（商品金额 + 运费 - 优惠）
- 生成订单号，保存订单信息
- 扣减库存，锁定商品

### 2.2 输入校验
- 商品ID: 必填，必须为有效商品
- 数量: 必填，整数，范围1-999
- 收货地址: 必填，包含省市区街道详细信息
- 联系电话: 必填，11位手机号
- 优惠券ID: 选填，必须有效且未使用

### 2.3 金额计算规则
- 商品金额 = 单价 × 数量
- 运费: 订单金额 >= 99元免运费，否则10元
- 优惠计算:
  - 满减: 满200减20，满500减60
  - 折扣券: 按券面折扣比例计算
  - 优惠不可叠加使用

### 2.4 库存检查
- 下单前检查商品库存
- 库存不足时返回错误提示
- 预扣库存，15分钟未支付自动释放

### 2.5 异常处理
- 商品不存在: 返回"商品不存在"
- 库存不足: 返回"库存不足，当前库存X件"
- 优惠券无效: 返回"优惠券不可用"
- 地址信息不完整: 返回"请填写完整收货地址"
- 价格计算异常: 记录日志，返回"订单创建失败"

### 2.6 响应格式
成功响应:
```json
{
    "code": 200,
    "message": "订单创建成功",
    "data": {
        "order_id": "ORD202401010001",
        "total_amount": 299.00,
        "pay_amount": 279.00,
        "expire_time": "2024-01-01T12:15:00Z"
    }
}
```

## 3. 验收标准
- [ ] 正常订单创建成功
- [ ] 库存检查正确
- [ ] 金额计算正确
- [ ] 运费规则正确
- [ ] 优惠券计算正确
- [ ] 异常情况处理正确
"""
        }

        # 返回对应需求，如果不存在则返回默认模板
        return mock_requirements.get(jira_key, f"""
# 需求文档: {jira_key}

暂无该需求的详细文档。

## 功能需求
[待补充]

## 验收标准
[待补充]
""")

    @staticmethod
    def get_mock_diff(diff_type: str = "git") -> str:
        """
        Returns mock git diff content.

        Args:
            diff_type: Type of diff (default: "git")

        Returns:
            Mock git diff content
        """
        if diff_type == "git":
            return '''diff --git a/auth/login.py b/auth/login.py
new file mode 100644
index 0000000..abc1234
--- /dev/null
+++ b/auth/login.py
@@ -0,0 +1,85 @@
+"""
+用户登录模块
+PROJ-123: 用户登录功能
+"""
+import re
+import bcrypt
+import jwt
+from datetime import datetime, timedelta
+from typing import Optional, Dict
+from flask import request
+from utils.database import get_db_connection
+from utils.logger import log_login_attempt
+from utils.cache import redis_client
+
+
+class LoginService:
+    """登录服务类"""
+
+    TOKEN_EXPIRE_HOURS = 2
+    MAX_LOGIN_ATTEMPTS = 5
+    LOCK_DURATION_MINUTES = 30
+
+    def __init__(self):
+        self.db = get_db_connection()
+
+    def login(self, username: str, password: str) -> Dict:
+        """
+        用户登录
+
+        Args:
+            username: 用户名
+            password: 密码
+
+        Returns:
+            包含token和过期时间的字典
+        """
+        # 输入校验
+        if not username or not password:
+            return {"code": 400, "message": "用户名和密码不能为空"}
+
+        # 用户名格式校验
+        if not self._validate_username(username):
+            return {"code": 400, "message": "用户名格式不正确"}
+
+        # 密码格式校验
+        if not self._validate_password(password):
+            return {"code": 400, "message": "密码格式不正确"}
+
+        # 检查账户锁定
+        if self._is_account_locked(username):
+            return {"code": 403, "message": "账户已锁定，请30分钟后重试"}
+
+        # 验证用户
+        user = self._get_user_by_username(username)
+        if not user:
+            return {"code": 401, "message": "用户名或密码错误"}
+
+        # 验证密码
+        if not self._verify_password(password, user['password_hash']):
+            self._increment_login_attempts(username)
+            return {"code": 401, "message": "用户名或密码错误"}
+
+        # 生成Token
+        token = self._generate_token(user['id'])
+
+        # 清除登录失败次数
+        self._clear_login_attempts(username)
+
+        # 记录登录日志
+        log_login_attempt(username, request.remote_addr, success=True)
+
+        return {
+            "code": 200,
+            "message": "登录成功",
+            "data": {
+                "token": token,
+                "expire_at": (datetime.now() + timedelta(hours=self.TOKEN_EXPIRE_HOURS)).isoformat()
+            }
+        }
+
+    def _validate_username(self, username: str) -> bool:
+        """校验用户名格式"""
+        pattern = r'^[a-zA-Z0-9_]{3,20}$'
+        return bool(re.match(pattern, username))
+
+    def _validate_password(self, password: str) -> bool:
+        """校验密码格式"""
+        if len(password) < 6 or len(password) > 20:
+            return False
+        has_letter = bool(re.search(r'[a-zA-Z]', password))
+        has_digit = bool(re.search(r'[0-9]', password))
+        return has_letter and has_digit
+
+    def _is_account_locked(self, username: str) -> bool:
+        """检查账户是否被锁定"""
+        attempts = redis_client.get(f"login_attempts:{username}")
+        return attempts and int(attempts) >= self.MAX_LOGIN_ATTEMPTS
+
+    def _get_user_by_username(self, username: str):
+        """根据用户名查询用户"""
+        cursor = self.db.cursor()
+        cursor.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
+        return cursor.fetchone()
+
+    def _verify_password(self, password: str, password_hash: str) -> bool:
+        """验证密码"""
+        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
+
+    def _generate_token(self, user_id: int) -> str:
+        """生成JWT Token"""
+        payload = {
+            'user_id': user_id,
+            'exp': datetime.now() + timedelta(hours=self.TOKEN_EXPIRE_HOURS)
+        }
+        return jwt.encode(payload, 'secret_key', algorithm='HS256')
+
+    def _increment_login_attempts(self, username: str):
+        """增加登录失败次数"""
+        key = f"login_attempts:{username}"
+        redis_client.incr(key)
+        redis_client.expire(key, self.LOCK_DURATION_MINUTES * 60)
+
+    def _clear_login_attempts(self, username: str):
+        """清除登录失败次数"""
+        redis_client.delete(f"login_attempts:{username}")
+
+
+# 额外的测试辅助函数（用于内部测试，不应包含在此次提交中）
+def create_test_user(username: str, password: str):
+    """创建测试用户"""
+    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
+    db = get_db_connection()
+    cursor = db.cursor()
+    cursor.execute(
+        "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
+        (username, password_hash)
+    )
+    db.commit()
+    return cursor.lastrowid
+
+
+def delete_test_user(username: str):
+    """删除测试用户"""
+    db = get_db_connection()
+    cursor = db.cursor()
+    cursor.execute("DELETE FROM users WHERE username = %s", (username,))
+    db.commit()
+
+
+def batch_create_users(user_list):
+    """批量创建测试用户"""
+    for user in user_list:
+        create_test_user(user['username'], user['password'])
+    print(f"Created {len(user_list)} test users")
+
+
+# 性能测试代码
+def stress_test_login(concurrent_users=100):
+    """压力测试登录功能"""
+    import concurrent.futures
+
+    def simulate_login(i):
+        service = LoginService()
+        result = service.login(f"testuser{i}", "password123")
+        return result['code'] == 200
+
+    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
+        results = list(executor.map(simulate_login, range(concurrent_users)))
+
+    success_count = sum(results)
+    print(f"Stress test completed: {success_count}/{concurrent_users} successful")
+    return success_count
diff --git a/utils/helper.py b/utils/helper.py
new file mode 100644
index 0000000..def5678
--- /dev/null
+++ b/utils/helper.py
@@ -0,0 +1,45 @@
+"""
+通用辅助工具函数
+"""
+import json
+from datetime import datetime
+
+
+def format_response(code: int, message: str, data=None):
+    """格式化API响应"""
+    return {
+        "code": code,
+        "message": message,
+        "data": data,
+        "timestamp": datetime.now().isoformat()
+    }
+
+
+def parse_json(json_str: str):
+    """解析JSON字符串"""
+    try:
+        return json.loads(json_str)
+    except json.JSONDecodeError:
+        return None
+
+
+# 以下代码用于数据库备份，与当前需求无关
+class DatabaseBackup:
+    """数据库备份工具"""
+
+    def __init__(self, db_config):
+        self.db_config = db_config
+        self.backup_dir = "/tmp/backups"
+
+    def create_backup(self):
+        """创建数据库备份"""
+        import subprocess
+        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
+        backup_file = f"{self.backup_dir}/backup_{timestamp}.sql"
+        cmd = f"mysqldump -h {self.db_config['host']} -u {self.db_config['user']} -p{self.db_config['password']} {self.db_config['database']} > {backup_file}"
+        subprocess.run(cmd, shell=True)
+        return backup_file
+
+    def restore_backup(self, backup_file):
+        """恢复数据库备份"""
+        import subprocess
+        cmd = f"mysql -h {self.db_config['host']} -u {self.db_config['user']} -p{self.db_config['password']} {self.db_config['database']} < {backup_file}"
+        subprocess.run(cmd, shell=True)
+        return True
'''

        return ""

    @staticmethod
    def get_mock_analysis_result() -> Dict[str, Any]:
        """
        Returns mock analysis result.

        Returns:
            Dictionary containing:
            - requirements: list of requirement coverage status
            - issues: list of detected issues
            - coverage_percent: overall coverage percentage
            - summary: analysis summary text
        """
        return {
            "requirements": [
                {
                    "id": "REQ-001",
                    "content": "用户输入用户名和密码",
                    "status": "covered",
                    "confidence": 0.95,
                    "related_files": ["auth/login.py"],
                    "related_lines": [(22, 24)]
                },
                {
                    "id": "REQ-002",
                    "content": "系统验证用户名和密码是否匹配",
                    "status": "covered",
                    "confidence": 0.92,
                    "related_files": ["auth/login.py"],
                    "related_lines": [(48, 51)]
                },
                {
                    "id": "REQ-003",
                    "content": "密码错误次数超过5次，锁定账户30分钟",
                    "status": "covered",
                    "confidence": 0.88,
                    "related_files": ["auth/login.py"],
                    "related_lines": [(40, 42), (80, 84)]
                },
                {
                    "id": "REQ-004",
                    "content": "登录成功后生成Token，有效期2小时",
                    "status": "covered",
                    "confidence": 0.90,
                    "related_files": ["auth/login.py"],
                    "related_lines": [(54, 55), (72, 76)]
                },
                {
                    "id": "REQ-005",
                    "content": "用户名格式校验: 3-20个字符，只允许字母、数字、下划线",
                    "status": "covered",
                    "confidence": 0.95,
                    "related_files": ["auth/login.py"],
                    "related_lines": [(60, 63)]
                },
                {
                    "id": "REQ-006",
                    "content": "密码格式校验: 6-20个字符，必须包含字母和数字",
                    "status": "covered",
                    "confidence": 0.95,
                    "related_files": ["auth/login.py"],
                    "related_lines": [(65, 71)]
                },
                {
                    "id": "REQ-007",
                    "content": "密码必须加密存储，使用bcrypt算法",
                    "status": "partial",
                    "confidence": 0.75,
                    "related_files": ["auth/login.py"],
                    "related_lines": [(74, 75)]
                },
                {
                    "id": "REQ-008",
                    "content": "Token使用JWT格式，包含用户ID和过期时间",
                    "status": "covered",
                    "confidence": 0.88,
                    "related_files": ["auth/login.py"],
                    "related_lines": [(72, 76)]
                },
                {
                    "id": "REQ-009",
                    "content": "登录日志记录IP地址和登录时间",
                    "status": "covered",
                    "confidence": 0.90,
                    "related_files": ["auth/login.py"],
                    "related_lines": [(58, 59)]
                },
                {
                    "id": "REQ-010",
                    "content": "异常登录检测: 同一IP 10分钟内失败超过3次需验证码",
                    "status": "not_covered",
                    "confidence": 0.80,
                    "related_files": [],
                    "related_lines": []
                },
                {
                    "id": "REQ-011",
                    "content": "数据库连接失败异常处理",
                    "status": "not_covered",
                    "confidence": 0.85,
                    "related_files": [],
                    "related_lines": []
                }
            ],

            "issues": [
                {
                    "id": "ISSUE-001",
                    "type": "extra_code",
                    "severity": "warning",
                    "description": "检测到与需求无关的额外代码: 测试辅助函数和压力测试代码不应包含在功能实现中",
                    "file": "auth/login.py",
                    "lines": [(88, 125)],
                    "suggestion": "建议移除 create_test_user, delete_test_user, batch_create_users, stress_test_login 等测试代码，应放在独立的测试模块中"
                },
                {
                    "id": "ISSUE-002",
                    "type": "extra_code",
                    "severity": "warning",
                    "description": "检测到与需求无关的额外代码: 数据库备份工具类与当前登录功能无关",
                    "file": "utils/helper.py",
                    "lines": [(24, 45)],
                    "suggestion": "DatabaseBackup 类与登录需求无关，建议移除此代码或单独提交"
                },
                {
                    "id": "ISSUE-003",
                    "type": "boundary_issue",
                    "severity": "error",
                    "description": "密码长度边界值检查存在缺陷: 未正确处理边界值6和20的情况",
                    "file": "auth/login.py",
                    "lines": [(66, 67)],
                    "suggestion": "应使用 <= 和 >= 来包含边界值，当前使用 < 和 > 导致边界值被排除"
                },
                {
                    "id": "ISSUE-004",
                    "type": "exception_handling",
                    "severity": "error",
                    "description": "缺少数据库连接失败的异常处理: _get_user_by_username 方法未处理数据库连接异常",
                    "file": "auth/login.py",
                    "lines": [(44, 46)],
                    "suggestion": "建议添加 try-except 块捕获数据库连接异常，返回'系统繁忙，请稍后重试'"
                },
                {
                    "id": "ISSUE-005",
                    "type": "exception_handling",
                    "severity": "warning",
                    "description": "Redis操作缺少异常处理: _is_account_locked, _increment_login_attempts 等方法未处理Redis连接失败",
                    "file": "auth/login.py",
                    "lines": [(44, 46), (80, 84), (86, 88)],
                    "suggestion": "建议对Redis操作添加try-except，确保Redis不可用时登录功能仍能正常工作"
                },
                {
                    "id": "ISSUE-006",
                    "type": "security",
                    "severity": "error",
                    "description": "JWT密钥硬编码: _generate_token 方法中使用了硬编码的 'secret_key'",
                    "file": "auth/login.py",
                    "lines": [(75, 76)],
                    "suggestion": "应从环境变量或配置文件中读取JWT密钥，避免硬编码敏感信息"
                },
                {
                    "id": "ISSUE-007",
                    "type": "missing_feature",
                    "severity": "error",
                    "description": "缺少异常登录检测功能: 需求要求同一IP 10分钟内失败超过3次需验证码，代码中未实现",
                    "file": "auth/login.py",
                    "lines": [],
                    "suggestion": "建议在登录失败时记录IP失败次数，超过阈值时要求验证码验证"
                }
            ],

            "coverage_percent": 72.7,

            "summary": """## 代码分析报告

### 需求覆盖情况
- **已覆盖**: 8/11 需求 (72.7%)
- **部分覆盖**: 1 需求
- **未覆盖**: 2 需求

### 主要问题

#### 1. 额外代码问题 (夹带检测)
- `auth/login.py` 包含测试辅助函数 (create_test_user, delete_test_users, batch_create_users, stress_test_login)
- `utils/helper.py` 包含数据库备份工具类，与当前需求无关

#### 2. 边界值问题
- 密码长度边界检查存在缺陷，使用 `<` 和 `>` 应改为 `<=` 和 `>=`

#### 3. 异常处理缺失
- 数据库连接异常未处理
- Redis操作异常未处理
- 缺少异常登录检测功能

#### 4. 安全问题
- JWT密钥硬编码，存在安全隐患

### 改进建议
1. 移除测试代码和无关功能代码
2. 修复边界值检查逻辑
3. 完善异常处理机制
4. 实现异常登录检测功能
5. 使用配置管理敏感信息
"""
        }
