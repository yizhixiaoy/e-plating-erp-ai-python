"""OSS对象存储服务 - 多Provider架构（aliyun/minio），与Java后端OssStorageFactory保持一致

支持提供商:
- aliyun: 阿里云OSS（oss2 SDK）
- minio: MinIO私有部署（minio SDK）

与Java后端共享bucket和URL格式:
- 前端通过Java网关 /api/v1/files/resource 访问文件
- 知识库文件存储在 ai-knowledge/ 子目录下
"""
import io
import uuid
import asyncio
import logging
from datetime import datetime
from urllib.parse import quote, unquote
from app.config import settings

logger = logging.getLogger(__name__)

# IMM文档预览支持的文件格式（与阿里云官方文档一致）
# 表格文件：et、xls、xlt、xlsx、xlsm、xltx、xltm、csv
# 文字文件：doc、docx、txt、dot、wps、wpt、dotx、docm、dotm、rtf
# 演示文件：ppt、pptx、pptm、ppsx、ppsm、pps、potx、potm、dpt、dps
# PDF文件：pdf
IMM_PREVIEW_EXTENSIONS = frozenset({
    "et", "xls", "xlt", "xlsx", "xlsm", "xltx", "xltm", "csv",
    "doc", "docx", "txt", "dot", "wps", "wpt", "dotx", "docm", "dotm", "rtf",
    "ppt", "pptx", "pptm", "ppsx", "ppsm", "pps", "potx", "potm", "dpt", "dps",
    "pdf",
})

# 浏览器原生可渲染的图片格式
IMAGE_EXTENSIONS = frozenset({"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "ico"})

# 浏览器原生可显示的文本格式
TEXT_EXTENSIONS = frozenset({"txt", "md", "json", "csv", "xml", "html", "htm", "log", "yaml", "yml", "ini", "conf", "sql"})

# IMM预览URL签名参数
IMM_PREVIEW_PROCESS = "imm/previewdoc,copy_1"


def _get_ext(filename: str) -> str:
    """获取文件扩展名（小写）"""
    if not filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _is_imm_previewable(filename: str) -> bool:
    """检查文件是否支持IMM文档预览"""
    return _get_ext(filename) in IMM_PREVIEW_EXTENSIONS


def get_preview_type(filename: str) -> str:
    """根据文件类型判断预览策略

    Returns:
        'imm'    - 使用阿里云IMM文档预览（PDF/Office等）
        'image'  - 浏览器原生图片渲染
        'text'   - 浏览器文本显示
        'none'   - 不支持预览，仅提供下载
    """
    ext = _get_ext(filename)
    if not ext:
        return "none"
    if ext in IMM_PREVIEW_EXTENSIONS:
        return "imm"
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in TEXT_EXTENSIONS:
        return "text"
    return "none"


def generate_resource_url(oss_path: str, filename: str = None, action: str = "preview") -> str:
    """生成OSS直链URL（普通URL，不包含签名，用于图片等非IMM预览文件）

    URL格式：
    - 自定义域名: https://{domain}/{object_key}
    - 标准OSS: https://{bucket}.{endpoint}/{object_key}
    """
    if not oss_path:
        return ""

    # 解码oss_path（存储时是URL编码的）
    object_key = unquote(oss_path)

    # 优先使用自定义域名（CDN）
    if settings.ALIYUN_DOMAIN:
        return f"https://{settings.ALIYUN_DOMAIN}/{quote(object_key, safe='/')}"

    # 标准阿里云OSS URL
    return f"https://{settings.ALIYUN_BUCKET}.{settings.ALIYUN_ENDPOINT}/{quote(object_key, safe='/')}"


# ─────────────────────────── Provider 后端实现 ───────────────────────────


class _MinioBackend:
    """MinIO存储后端（minio SDK）"""

    def __init__(self):
        self._client = None
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.secure = settings.MINIO_SECURE
        self.bucket = settings.MINIO_BUCKET
        self.storage_type = "minio"

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.access_key and self.secret_key and self.bucket)

    def connect(self):
        from minio import Minio
        client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )
        if not client.bucket_exists(self.bucket):
            client.make_bucket(self.bucket)
            logger.info("[OSS/MinIO] Bucket创建成功: %s", self.bucket)
        self._client = client
        logger.info("[OSS/MinIO] 连接成功, endpoint=%s, bucket=%s", self.endpoint, self.bucket)

    @property
    def client(self):
        return self._client

    def upload(self, object_name: str, data: io.BytesIO, length: int, content_type: str):
        self._client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=data,
            length=length,
            content_type=content_type,
            metadata={"Cache-Control": "public, max-age=31536000"},
        )

    def download(self, object_name: str) -> bytes:
        response = self._client.get_object(
            bucket_name=self.bucket,
            object_name=object_name,
        )
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, object_name: str):
        self._client.remove_object(
            bucket_name=self.bucket,
            object_name=object_name,
        )


class _AliyunBackend:
    """阿里云OSS存储后端（oss2 SDK）"""

    def __init__(self):
        self._client = None
        self.endpoint = settings.ALIYUN_ENDPOINT
        self.access_key_id = settings.ALIYUN_ACCESS_KEY_ID
        self.access_key_secret = settings.ALIYUN_ACCESS_KEY_SECRET
        self.bucket_name = settings.ALIYUN_BUCKET
        self.storage_type = "aliyun"

    def is_configured(self) -> bool:
        return bool(self.endpoint and self.access_key_id and self.access_key_secret and self.bucket_name)

    def connect(self):
        import oss2
        auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        # 确保endpoint包含协议前缀
        endpoint = self.endpoint
        if not endpoint.startswith(("http://", "https://")):
            endpoint = f"https://{endpoint}"
        self._client = oss2.Bucket(auth, endpoint, self.bucket_name)
        logger.info("[OSS/Aliyun] 连接成功, endpoint=%s, bucket=%s", self.endpoint, self.bucket_name)

    @property
    def client(self):
        return self._client

    def upload(self, object_name: str, data: io.BytesIO, length: int, content_type: str):
        headers = {
            "Content-Type": content_type,
            "Cache-Control": "public, max-age=31536000",
            "x-oss-server-side-encryption": "AES256",
        }
        self._client.put_object(object_name, data, headers=headers)

    def download(self, object_name: str) -> bytes:
        result = self._client.get_object(object_name)
        return result.read()

    def delete(self, object_name: str):
        self._client.delete_object(object_name)

    def sign_url_with_process(self, object_name: str, process: str, expire: int = 3600) -> str:
        """生成带有 OSS 处理参数的签名URL（用于IMM文档预览、图片处理等）

        Args:
            object_name: OSS对象路径（未编码）
            process: OSS处理参数，如 'imm/previewdoc,copy_1'
            expire: URL有效期（秒），默认3600秒

        Returns:
            带有签名和处理参数的完整URL
        """
        return self._client.sign_url(
            'GET', object_name, expire,
            params={'x-oss-process': process},
            slash_safe=True  # 保持路径中的/不编码为%2F，否则OSS路由无法识别
        )


# ─────────────────────────── 统一存储服务 ───────────────────────────


class OssStorageService:
    """OSS对象存储服务（多Provider统一接口）

    与Java后端的OssStorageFactory体系对接：
    - 根据 OSS_PROVIDER 自动选择存储后端（aliyun/minio）
    - 共享同一个bucket，生成与FileUploadUtils.getResourceUrl()格式一致的URL
    - 前端通过Java网关 /api/v1/files/resource 访问文件

    路径规范:
    - 知识库文档: ai-knowledge/kb/{kb_id}/{yyyy_MM_dd}/{uuid}.{ext}
    - 对话临时文档: ai-knowledge/temp/{tenant_id}/{yyyy_MM_dd}/{uuid}.{ext}
    """

    def __init__(self):
        self.enabled = settings.OSS_ENABLED
        self._backend = None
        self._connected = False
        self._provider = settings.OSS_PROVIDER.lower()

    @property
    def backend(self):
        """延迟初始化存储后端（支持重试：连接失败不永久禁用，下次调用自动重连）"""
        if self._backend is not None and self._connected:
            return self._backend

        if not self.enabled:
            return None

        # 按 provider 选择后端
        backend = self._create_backend()
        if backend is None:
            return None

        # 检查配置是否完整
        if not backend.is_configured():
            logger.warning("[OSS] Provider '%s' 配置不完整，OSS不可用", self._provider)
            self.enabled = False  # 配置缺失，永久禁用
            return None

        # 尝试连接
        try:
            backend.connect()
            self._backend = backend
            self._connected = True
            return backend
        except ImportError as ie:
            logger.warning("[OSS] Provider '%s' SDK未安装: %s，OSS功能永久不可用", self._provider, ie)
            self.enabled = False
            return None
        except Exception as e:
            logger.warning("[OSS] Provider '%s' 连接失败（稍后重试）: %s", self._provider, e)
            self._connected = False
            return None

    def _create_backend(self):
        """根据 provider 创建对应的存储后端"""
        if self._provider == "aliyun":
            return _AliyunBackend()
        elif self._provider == "minio":
            return _MinioBackend()
        else:
            logger.warning("[OSS] 不支持的 provider: %s，仅支持 aliyun / minio", self._provider)
            self.enabled = False
            return None

    @property
    def bucket(self) -> str:
        """当前使用的 bucket 名称"""
        if self._backend:
            if isinstance(self._backend, _MinioBackend):
                return self._backend.bucket
            elif isinstance(self._backend, _AliyunBackend):
                return self._backend.bucket_name
        # 回退到配置值
        if self._provider == "aliyun":
            return settings.ALIYUN_BUCKET
        return settings.MINIO_BUCKET

    def _generate_object_name(self, module: str, file_type: str) -> str:
        """生成OSS对象路径（与Java FileUploadUtils路径规范一致）

        格式: {module}/{yyyy_MM_dd}/{uuid}.{ext}
        """
        date_path = datetime.now().strftime("%Y_%m_%d")
        file_uuid = uuid.uuid4().hex
        ext = file_type.lstrip(".") if file_type else ""
        if ext:
            return f"{module}/{date_path}/{file_uuid}.{ext}"
        return f"{module}/{date_path}/{file_uuid}"

    def generate_kb_object_name(self, kb_id: int, file_type: str) -> str:
        """生成知识库文档的OSS路径"""
        return self._generate_object_name(f"ai-knowledge/kb/{kb_id}", file_type)

    def generate_temp_object_name(self, tenant_id: int, file_type: str) -> str:
        """生成对话临时文档的OSS路径"""
        return self._generate_object_name(f"ai-knowledge/temp/{tenant_id}", file_type)

    async def upload_file(
        self, file_content: bytes, object_name: str, content_type: str = "application/octet-stream"
    ) -> str:
        """上传文件到OSS

        Args:
            file_content: 文件二进制内容
            object_name: OSS对象路径（由generate_*_object_name生成）
            content_type: MIME类型

        Returns:
            oss_path（URL编码后的对象路径）
        """
        if not self.enabled:
            logger.warning("[OSS] OSS未启用（配置关闭或SDK缺失），跳过上传")
            return ""

        backend = self.backend
        if not backend:
            raise RuntimeError(
                f"OSS存储服务不可用（provider={self._provider}），"
                f"请检查OSS配置是否正确"
            )

        def _upload():
            data = io.BytesIO(file_content)
            backend.upload(object_name, data, len(file_content), content_type)

        await asyncio.to_thread(_upload)
        # oss_path编码方式与Java保持一致：URLEncoder.encode() 编码所有字符（包括斜杠）
        # Java: URLEncoder.encode(objectName, UTF_8) → "ai-knowledge%2Fkb%2F1%2F..."
        oss_path = quote(object_name, safe="")
        logger.info("[OSS/%s] 上传成功: %s/%s", backend.storage_type, self.bucket, object_name)
        return oss_path

    async def download_file(self, oss_path: str) -> bytes:
        """从OSS下载文件

        Args:
            oss_path: OSS路径（URL编码）

        Returns:
            文件二进制内容
        """
        backend = self.backend
        if not backend:
            raise RuntimeError("OSS存储服务不可用，无法下载")

        decoded_path = unquote(oss_path)

        def _download():
            return backend.download(decoded_path)

        return await asyncio.to_thread(_download)

    async def delete_file(self, oss_path: str):
        """删除OSS文件"""
        backend = self.backend
        if not backend:
            return

        decoded_path = unquote(oss_path)

        def _delete():
            backend.delete(decoded_path)

        await asyncio.to_thread(_delete)
        logger.info("[OSS/%s] 删除成功: %s/%s", backend.storage_type, self.bucket, decoded_path)

    def get_resource_url(self, oss_path: str, filename: str = None, action: str = "preview") -> str:
        """生成与Java FileUploadUtils.getResourceUrl()格式一致的资源URL（委托给模块级函数）"""
        return generate_resource_url(oss_path, filename, action)

    def get_preview_url(self, oss_path: str, filename: str = None) -> str:
        """生成文档预览URL

        支持IMM预览的文件（PDF、Office等）：生成带签名的IMM预览URL（有有效期）
        不支持IMM的文件（图片等）：生成普通OSS直链URL

        Args:
            oss_path: OSS路径（URL编码，存储在DB中的值）
            filename: 原始文件名，用于判断文件类型；None时从oss_path提取

        Returns:
            预览URL：
            - IMM预览：https://bucket.endpoint/object_key?x-oss-process=imm/previewdoc&Signature=xxx&Expires=xxx
            - 普通直链：https://bucket.endpoint/object_key
        """
        if not oss_path:
            return ""

        actual_filename = filename or self._extract_filename(oss_path)

        # 检查是否支持IMM预览
        if (
            settings.IMM_PREVIEW_ENABLED
            and self._provider == "aliyun"
            and _is_imm_previewable(actual_filename)
        ):
            backend = self.backend
            if backend and isinstance(backend, _AliyunBackend):
                object_key = unquote(oss_path)
                try:
                    signed_url = backend.sign_url_with_process(
                        object_key,
                        IMM_PREVIEW_PROCESS,
                        settings.IMM_PREVIEW_EXPIRE
                    )
                    logger.debug("[OSS] 生成IMM预览URL: %s (expire=%ds)", actual_filename, settings.IMM_PREVIEW_EXPIRE)
                    return signed_url
                except Exception as e:
                    logger.warning("[OSS] 生成IMM预览URL失败，回退到直链: %s, err=%s", actual_filename, e)

        # 回退到普通直链URL
        return generate_resource_url(oss_path, actual_filename)

    @staticmethod
    def _extract_filename(oss_path: str) -> str:
        """从OSS路径提取文件名"""
        decoded = unquote(oss_path)
        last_slash = decoded.rfind("/")
        return decoded[last_slash + 1:] if last_slash >= 0 else decoded

    @staticmethod
    def guess_content_type(file_type: str) -> str:
        """根据文件类型推断MIME类型"""
        mime_map = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xls": "application/vnd.ms-excel",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "txt": "text/plain",
            "md": "text/markdown",
            "csv": "text/csv",
            "json": "application/json",
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
        }
        return mime_map.get(file_type.lower(), "application/octet-stream")
