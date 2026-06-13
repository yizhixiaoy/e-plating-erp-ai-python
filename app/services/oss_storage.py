"""OSS对象存储服务 - MinIO兼容，与Java后端FileUploadUtils共享bucket和URL格式"""
import io
import uuid
import asyncio
import logging
from datetime import datetime
from urllib.parse import quote, unquote
from app.config import settings

logger = logging.getLogger(__name__)

# Java后端资源访问接口基础路径（与FileUploadUtils.RESOURCE_BASE_PATH保持一致）
RESOURCE_BASE_PATH = "/api/v1/files/resource"


class OssStorageService:
    """MinIO对象存储服务

    与Java后端的OssStorage体系对接：
    - 共享同一个bucket
    - 生成与FileUploadUtils.getResourceUrl()格式一致的资源URL
    - 前端通过Java网关 /api/v1/files/resource 访问文件

    路径规范:
    - 知识库文档: ai-knowledge/kb/{kb_id}/{yyyy_MM_dd}/{uuid}.{ext}
    - 对话临时文档: ai-knowledge/temp/{tenant_id}/{yyyy_MM_dd}/{uuid}.{ext}
    """

    def __init__(self):
        self._client = None
        self.bucket = settings.OSS_BUCKET
        self.enabled = settings.OSS_ENABLED

    @property
    def client(self):
        """延迟初始化MinIO客户端"""
        if self._client is None and self.enabled:
            try:
                from minio import Minio
                self._client = Minio(
                    endpoint=settings.OSS_ENDPOINT,
                    access_key=settings.OSS_ACCESS_KEY,
                    secret_key=settings.OSS_SECRET_KEY,
                    secure=settings.OSS_SECURE,
                )
                # 检查bucket是否存在，不存在则创建
                if not self._client.bucket_exists(self.bucket):
                    self._client.make_bucket(self.bucket)
                    logger.info(f"[OSS] Bucket创建成功: {self.bucket}")
                logger.info(f"[OSS] MinIO初始化成功, endpoint={settings.OSS_ENDPOINT}, bucket={self.bucket}")
            except ImportError:
                logger.warning("[OSS] minio SDK未安装，OSS功能不可用")
                self.enabled = False
            except Exception as e:
                logger.error(f"[OSS] MinIO初始化失败: {e}")
                self.enabled = False
        return self._client

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
        if not self.enabled or not self.client:
            logger.warning("[OSS] OSS未启用，跳过上传")
            return ""

        def _upload():
            data = io.BytesIO(file_content)
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=object_name,
                data=data,
                length=len(file_content),
                content_type=content_type,
                metadata={"Cache-Control": "public, max-age=31536000"},
            )

        await asyncio.to_thread(_upload)
        oss_path = quote(object_name, safe="/")
        logger.info(f"[OSS] 上传成功: {self.bucket}/{object_name}")
        return oss_path

    async def download_file(self, oss_path: str) -> bytes:
        """从OSS下载文件

        Args:
            oss_path: OSS路径（URL编码）

        Returns:
            文件二进制内容
        """
        if not self.enabled or not self.client:
            raise RuntimeError("OSS未启用，无法下载")

        decoded_path = unquote(oss_path)

        def _download():
            response = self.client.get_object(
                bucket_name=self.bucket,
                object_name=decoded_path,
            )
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        return await asyncio.to_thread(_download)

    async def delete_file(self, oss_path: str):
        """删除OSS文件"""
        if not self.enabled or not self.client:
            return

        decoded_path = unquote(oss_path)

        def _delete():
            self.client.remove_object(
                bucket_name=self.bucket,
                object_name=decoded_path,
            )

        await asyncio.to_thread(_delete)
        logger.info(f"[OSS] 删除成功: {self.bucket}/{decoded_path}")

    def get_resource_url(self, oss_path: str, filename: str = None, action: str = "preview") -> str:
        """生成与Java FileUploadUtils.getResourceUrl()格式一致的资源URL

        Args:
            oss_path: OSS路径（URL编码）
            filename: 原始文件名（用于下载时显示）
            action: 操作类型 preview/download

        Returns:
            完整资源URL，如 /api/v1/files/resource?filename=xxx&ossPath=xxx&action=preview
        """
        if not oss_path:
            return ""

        if not filename:
            filename = self._extract_filename(oss_path)

        return (
            f"{RESOURCE_BASE_PATH}"
            f"?filename={quote(filename, safe='')}"
            f"&ossPath={oss_path}"
            f"&action={action}"
        )

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
