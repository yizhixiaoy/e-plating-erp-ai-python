"""写作模板与生成服务"""
from app.models.schemas import WriterTemplate, WriterRequest

WRITER_TEMPLATES = {
    WriterTemplate.REPORT: {
        "name": "工作报告",
        "prompt": """请根据以下主题{extra_points}，生成一份正式的工作报告：

{topic}

要求：
1. 使用正式的商务中文
2. 包含：背景概述、主要成果、数据分析、存在问题、下一步计划
3. 条理清晰，突出重点
4. 字数：约{word_count}字
5. 风格：{style_instruction}"""
    },
    WriterTemplate.NOTICE: {
        "name": "通知公告",
        "prompt": """请根据以下主题{extra_points}，撰写一份正式的通知公告：

{topic}

要求：
1. 包含：发布部门、通知对象、具体事项、时间安排、注意事项
2. 语言规范正式，条理清楚
3. 字数：约{word_count}字
4. 风格：{style_instruction}"""
    },
    WriterTemplate.SUMMARY: {
        "name": "工作总结",
        "prompt": """请根据以下主题{extra_points}，撰写一份工作总结：

{topic}

要求：
1. 包含：工作回顾、成果亮点、不足反思、改进计划
2. 有数据支撑，有深度思考
3. 字数：约{word_count}字
4. 风格：{style_instruction}"""
    },
    WriterTemplate.CONTRACT: {
        "name": "合同草稿",
        "prompt": """请根据以下主题{extra_points}，起草一份标准合同文本：

{topic}

要求：
1. 包含标准合同条款结构
2. 使用专业法律用语
3. 标注需要双方确认的关键条款
4. 字数：约{word_count}字
5. 风格：{style_instruction}"""
    },
    WriterTemplate.CUSTOM: {
        "name": "自定义写作",
        "prompt": """请根据以下主题{extra_points}，生成符合要求的文本：

{topic}

要求：
1. 内容准确完整
2. 表达流畅自然
3. 字数：约{word_count}字
4. 风格：{style_instruction}"""
    }
}


class WriterService:
    """写作助手服务"""

    @staticmethod
    def build_prompt(request: WriterRequest, knowledge_context: str = "") -> dict:
        """构建写作Prompt

        Args:
            request: 写作请求
            knowledge_context: 知识库检索到的参考内容（可选）
        """
        template = WRITER_TEMPLATES.get(
            request.template_type,
            WRITER_TEMPLATES[WriterTemplate.CUSTOM]
        )

        style_instructions = {
            "formal": "正式、专业",
            "concise": "简洁、精炼",
            "detailed": "详细、全面"
        }

        extra_points = ""
        if request.key_points:
            extra_points = "（要点：" + "、".join(request.key_points) + "）"

        prompt = template["prompt"].format(
            topic=request.topic,
            extra_points=extra_points,
            word_count=request.word_count,
            style_instruction=style_instructions.get(request.style, "正式、专业")
        )

        system_prompt = "你是电镀行业ERP系统的专业写作助手，擅长撰写各类商务和工艺文档。"

        # 注入知识库参考内容
        if knowledge_context:
            system_prompt += (
                "\n\n【参考资料】以下是从知识库检索到的相关内容，请在写作中适当引用：\n"
                f"{knowledge_context}"
            )

        return {
            "system_prompt": system_prompt,
            "user_prompt": prompt,
            "template_name": template["name"]
        }
