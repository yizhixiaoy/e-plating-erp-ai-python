"""统计分析工具 — 对ERP查询结果进行数值统计与趋势分析"""
import json
import re
from app.tools.base import BaseTool
from app.services.permissions import AI_PERMS


class StatsTool(BaseTool):
    name = "stats_tool"
    required_permission = AI_PERMS.CHAT_VIEW  # 统计分析需要AI对话权限
    description = """
    对查询结果进行统计分析。支持趋势分析、对比分析、占比计算、汇总统计。
    参数：
    - operation: 操作类型（trend/compare/ratio/summary）
    - data: 待分析的数据（JSON数组或键值对格式的文本）
    - params: 分析参数 {"group_by": "字段名", "sort": "asc|desc", "top_n": 5}
    """

    async def execute(
        self,
        operation: str,
        data: str,
        params: dict = None
    ) -> dict:
        """执行统计分析"""
        params = params or {}

        # 尝试解析数据
        parsed = self._parse_data(data)

        if operation == "trend":
            result_text = self._analyze_trend(parsed, data, params)
        elif operation == "compare":
            result_text = self._analyze_compare(parsed, data, params)
        elif operation == "ratio":
            result_text = self._analyze_ratio(parsed, data, params)
        elif operation == "summary":
            result_text = self._analyze_summary(parsed, data, params)
        else:
            result_text = f"统计分析 [{operation}]:\n数据: {data}\n（不支持的操作类型）"

        return {
            "content": result_text,
            "references": [{
                "source_type": "database",
                "source_id": "stats",
                "doc_title": "统计分析",
                "section_title": operation
            }]
        }

    def _parse_data(self, data: str):
        """尝试多种方式解析输入数据"""
        if not data or not data.strip():
            return None

        # 1. 直接JSON解析
        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            pass

        # 2. 提取JSON代码块
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', data, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except (json.JSONDecodeError, TypeError):
                pass

        # 3. 提取内嵌JSON对象/数组
        brace_match = re.search(r'[\{\[].*[\}\]]', data, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except (json.JSONDecodeError, TypeError):
                pass

        return None

    def _extract_numbers(self, parsed) -> list[float]:
        """从解析结果中提取数值列表"""
        numbers = []
        if parsed is None:
            return numbers

        if isinstance(parsed, list):
            for item in parsed:
                numbers.extend(self._extract_numbers(item))
        elif isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, (int, float)):
                    numbers.append(float(v))
                elif isinstance(v, (list, dict)):
                    numbers.extend(self._extract_numbers(v))
                elif isinstance(v, str):
                    try:
                        numbers.append(float(v.replace(",", "").replace("%", "")))
                    except ValueError:
                        pass
        elif isinstance(parsed, (int, float)):
            numbers.append(float(parsed))
        elif isinstance(parsed, str):
            try:
                numbers.append(float(parsed.replace(",", "").replace("%", "")))
            except ValueError:
                pass

        return numbers

    def _extract_time_series(self, parsed) -> list[tuple[str, float]]:
        """从解析结果提取时间序列（key-date, value-number）"""
        series = []
        if not isinstance(parsed, dict):
            return series

        date_pattern = re.compile(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}月\d{1,2}日?|\d{4}年\d{1,2}月')
        for key, val in parsed.items():
            if date_pattern.search(str(key)):
                try:
                    if isinstance(val, (int, float)):
                        series.append((str(key), float(val)))
                    elif isinstance(val, str):
                        series.append((str(key), float(val.replace(",", ""))))
                except (ValueError, TypeError):
                    pass
        return series

    def _compute_stats(self, numbers: list[float]) -> dict:
        """计算基础统计量"""
        if not numbers:
            return {}
        n = len(numbers)
        sorted_nums = sorted(numbers)
        total = sum(sorted_nums)
        avg = total / n
        median = sorted_nums[n // 2] if n % 2 == 1 else (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2
        return {
            "count": n,
            "sum": round(total, 2),
            "mean": round(avg, 2),
            "median": round(median, 2),
            "min": round(sorted_nums[0], 2),
            "max": round(sorted_nums[-1], 2),
        }

    def _analyze_summary(self, parsed, raw_data: str, params: dict) -> str:
        """汇总统计：计算总数/均值/中位数/极值"""
        numbers = self._extract_numbers(parsed)
        if not numbers:
            return f"【汇总统计】\n原始数据: {raw_data}\n（无法提取数值字段，请检查数据格式）"

        stats = self._compute_stats(numbers)
        lines = ["【汇总统计】"]
        lines.append(f"- 数据量: {stats['count']} 条")
        lines.append(f"- 总和: {stats['sum']}")
        lines.append(f"- 均值: {stats['mean']}")
        lines.append(f"- 中位数: {stats['median']}")
        lines.append(f"- 最小值: {stats['min']}")
        lines.append(f"- 最大值: {stats['max']}")
        return "\n".join(lines)

    def _analyze_trend(self, parsed, raw_data: str, params: dict) -> str:
        """趋势分析：计算环比增长率，识别趋势方向"""
        lines = ["【趋势分析】"]

        # 尝试提取时间序列
        series = self._extract_time_series(parsed)
        if len(series) >= 2:
            values = [v for _, v in series]
            stats = self._compute_stats(values)
            lines.append(f"- 数据点数: {len(series)}")
            lines.append(f"- 均值: {stats.get('mean', 'N/A')}")
            lines.append(f"- 最小值: {stats.get('min', 'N/A')}")
            lines.append(f"- 最大值: {stats.get('max', 'N/A')}")

            # 计算总体趋势
            first_val = values[0]
            last_val = values[-1]
            if first_val and first_val != 0:
                change_pct = round((last_val - first_val) / first_val * 100, 2)
                direction = "上升" if change_pct > 0 else ("下降" if change_pct < 0 else "持平")
                lines.append(f"- 总体变化: {change_pct:+.2f}%（{direction}）")

            # 逐期环比
            lines.append("\n逐期环比变化率：")
            for i in range(1, len(series)):
                prev = values[i - 1]
                curr = values[i]
                if prev and prev != 0:
                    rate = round((curr - prev) / prev * 100, 2)
                    lines.append(f"  {series[i][0]}: {rate:+.2f}% (前值={prev}, 当前={curr})")

            return "\n".join(lines)

        # 降级：对纯数值计算基本趋势指标
        numbers = self._extract_numbers(parsed)
        if numbers and len(numbers) >= 2:
            stats = self._compute_stats(numbers)
            first_half = numbers[:len(numbers) // 2]
            second_half = numbers[len(numbers) // 2:]
            first_avg = sum(first_half) / len(first_half) if first_half else 0
            second_avg = sum(second_half) / len(second_half) if second_half else 0
            if first_avg:
                change = round((second_avg - first_avg) / first_avg * 100, 2)
                direction = "上升" if change > 0 else ("下降" if change < 0 else "持平")
            else:
                change, direction = 0, "持平"

            lines.append(f"- 数据点数: {stats['count']}")
            lines.append(f"- 前半段均值: {round(first_avg, 2)} → 后半段均值: {round(second_avg, 2)}")
            lines.append(f"- 趋势方向: {direction} ({change:+.2f}%)")
            lines.append(f"- 整体: 均值={stats['mean']}, 中位数={stats['median']}, 范围=[{stats['min']}, {stats['max']}]")
            return "\n".join(lines)

        return f"【趋势分析】\n原始数据: {raw_data}\n（数据量不足或格式不支持趋势计算）"

    def _analyze_compare(self, parsed, raw_data: str, params: dict) -> str:
        """对比分析：多组数据横向比较"""
        numbers = self._extract_numbers(parsed)
        if not numbers:
            return f"【对比分析】\n原始数据: {raw_data}\n（无法提取数值字段）"

        stats = self._compute_stats(numbers)
        lines = ["【对比分析】"]
        lines.append(f"- 数据总量: {stats['count']} 条")
        lines.append(f"- 总和: {stats['sum']}")
        lines.append(f"- 均值: {stats['mean']}")
        lines.append(f"- 中位数: {stats['median']}")
        lines.append(f"- 极差: {stats['max']} - {stats['min']} = {round(stats['max'] - stats['min'], 2)}")

        if stats['mean'] and stats['mean'] != 0:
            cv = round((stats.get('max', 0) - stats.get('min', 0)) / stats['mean'] * 100, 2)
            lines.append(f"- 离散度(CV近似): {cv}%")

        return "\n".join(lines)

    def _analyze_ratio(self, parsed, raw_data: str, params: dict) -> str:
        """占比分析：计算各部分占总体的百分比"""
        numbers = self._extract_numbers(parsed)
        if not numbers:
            return f"【占比分析】\n原始数据: {raw_data}\n（无法提取数值字段）"

        total = sum(numbers)
        if total == 0:
            return f"【占比分析】\n数据总和为0，无法计算占比"

        lines = ["【占比分析】"]
        lines.append(f"- 总值: {round(total, 2)}")

        for i, val in enumerate(numbers):
            pct = round(val / total * 100, 2)
            lines.append(f"- 第{i + 1}项: {val} ({pct}%)")

        return "\n".join(lines)
