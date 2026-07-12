"""货物图片CLIP嵌入服务

使用OpenCLIP模型提取货物图片的特征向量，用于图片相似度搜索和交叉比对。
"""
import io
import logging
import numpy as np
from PIL import Image
import torch

logger = logging.getLogger(__name__)


class GoodsImageClipService:
    """货物图片CLIP嵌入服务

    使用OpenCLIP ViT-B-32模型提取图片512维特征向量。
    与Java端的goods_image表配合，将图片特征存储到PostgreSQL pgvector中。
    """

    MODEL_NAME = "ViT-B-32"
    MODEL_SOURCE = "laion/CLIP-vit-b-32-wmt-multilingual"

    def __init__(self):
        self._model = None
        self._processor = None
        self._device = "cpu"  # 有GPU时改为 "cuda"

    @property
    def model(self):
        """延迟初始化CLIP模型"""
        if self._model is None:
            try:
                import open_clip
                logger.info("[CLIP] 正在加载模型: %s/%s", self.MODEL_NAME, self.MODEL_SOURCE)
                self._model, _, self._processor = open_clip.create_model_and_transforms(
                    self.MODEL_NAME,
                    pretrained=self.MODEL_SOURCE,
                    device=self._device,
                )
                self._model.eval()
                logger.info("[CLIP] 模型加载成功")
            except ImportError:
                logger.error("[CLIP] open_clip库未安装，请运行: pip install open-clip-torch")
                raise
            except Exception as e:
                logger.error("[CLIP] 模型加载失败: %s", e)
                raise
        return self._model

    @property
    def processor(self):
        if self._processor is None:
            # 模型初始化时会同时创建processor
            _ = self.model
        return self._processor

    def get_embedding(self, image_bytes: bytes) -> list[float]:
        """从图片字节数组提取特征向量

        Args:
            image_bytes: 图片的二进制数据

        Returns:
            特征向量（归一化后的float列表）
        """
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            transforms = self.processor
            tensor = transforms(image).unsqueeze(0).to(self._device)

            with torch.no_grad():
                embedding = self.model.encode_image(tensor)
                # L2归一化
                embedding = embedding / embedding.norm(dim=-1, keepdim=True)
                return embedding.squeeze(0).cpu().tolist()
        except Exception as e:
            logger.error("[CLIP] 图片特征提取失败: %s", e)
            raise

    def batch_get_embeddings(self, images: list[bytes]) -> list[list[float]]:
        """批量提取图片特征向量

        Args:
            images: 图片字节数组列表

        Returns:
            特征向量列表
        """
        results = []
        for img_bytes in images:
            results.append(self.get_embedding(img_bytes))
        return results

    def cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """计算两个向量之间的余弦相似度

        Args:
            vec_a: 向量A
            vec_b: 向量B

        Returns:
            余弦相似度 [0, 1]
        """
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
