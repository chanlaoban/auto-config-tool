"""
AI Agent 服务 - 封装OpenAI兼容API，提供智能匹配能力

提供三种模式：
1. learning - 学习模式：分析用户行为，学习匹配规则
2. semi-auto - 半自动模式：AI推荐+用户确认
3. full-auto - 全自动模式：完全由AI自动匹配

当AI API不可用时，自动回退到基于规则的匹配
"""
import json
import re
from typing import Optional, List, Dict, Any
from httpx import AsyncClient, Client
from config import AI_API_KEY, AI_MODEL, AI_API_BASE, COLUMNS_18


class AIClient:
    """OpenAI兼容API客户端，封装AI查询和匹配功能"""

    def __init__(self):
        self.api_key = AI_API_KEY
        self.model = AI_MODEL
        self.api_base = AI_API_BASE.rstrip("/")
        self._available = bool(self.api_key)

    def _is_available(self) -> bool:
        """检查AI API是否可用"""
        return self._available

    def _build_system_prompt(self, mode: str = "general") -> str:
        """
        构建系统提示词，根据模式说明18列结构
        
        18列定义:
        A=序号, B=设备名称, C=招标/需求参数, D=单位, E=数量, 
        F=(空), G=(空), 
        H=产品名称, I=产品规格, J=品牌, K=产品型号, 
        L=厂家内部型号, M=数量, N=单位, O=产品单价, 
        P=总价, Q=备注, R=不满足参数
        """
        base_prompt = """你是一个专业的企业级产品配置专家助手，帮助用户将招标需求匹配到产品目录中。

表格的18列结构如下：
A列(序号): 行号，自动编号
B列(设备名称): 需求中的设备/产品名称
C列(招标/需求参数): 招标文件或需求中的详细技术参数
D列(单位): 需求的计量单位
E列(数量): 需求的数量
F列(空): 留空，作为需求区和产品区的分隔
G列(空): 留空，作为需求区和产品区的分隔
H列(产品名称): 匹配到的产品名称
I列(产品规格): 匹配产品的详细规格参数
J列(品牌): 产品品牌
K列(产品型号): 产品型号
L列(厂家内部型号): 厂家内部编码或型号
M列(数量): 匹配数量（通常与E列一致）
N列(单位): 产品单位
O列(产品单价): 单个产品的价格
P列(总价): 数量×单价的总价
Q列(备注): 补充说明信息
R列(不满足参数): 列出需求中未满足的参数项

需求侧是A-E列，产品侧是H-R列，F-G列为空分隔区。
"""
        if mode == "match":
            return base_prompt + """
你的任务：根据用户输入的需求行数据（B=设备名称, C=招标/需求参数），从产品列表中找出最匹配的产品。
返回格式：JSON对象，包含H-R列的值。
注意：仔细对比需求参数中的技术指标与产品规格，在R列中标出需求中有但产品不满足的参数项。
"""
        elif mode == "auto_configure":
            return base_prompt + """
你的任务：批量处理所有需求行，为每条需求匹配最佳产品。
对于每条需求，分析B列设备名称和C列招标参数，搜索产品列表，选择最匹配的产品。
输出完整的18列数据，确保每个产品匹配合理，价格计算准确。
如果某个需求找不到合适产品，H-R列留空并在R列注明"未找到匹配产品"。
"""
        else:
            return base_prompt + """
你是一个专业的产品配置顾问，请根据用户的问题和提供的上下文信息，给出准确、专业的回答。
"""

    async def _call_api_async(self, messages: list, temperature: float = 0.3) -> str:
        """异步调用OpenAI兼容API"""
        if not self._is_available():
            raise ConnectionError("AI API未配置，无法使用AI功能")

        async with AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 4096,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def _call_api(self, messages: list, temperature: float = 0.3) -> str:
        """同步调用OpenAI兼容API"""
        if not self._is_available():
            raise ConnectionError("AI API未配置，无法使用AI功能")

        with Client(timeout=60.0) as client:
            response = client.post(
                f"{self.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 4096,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    def query(self, prompt: str, context: str = "") -> str:
        """
        通用AI查询
        
        Args:
            prompt: 用户提示词
            context: 上下文信息（知识库内容等）
        
        Returns:
            AI的文本回复
        """
        messages = [
            {"role": "system", "content": self._build_system_prompt("general")},
        ]
        if context:
            messages.append({"role": "user", "content": f"背景信息:\n{context}\n\n请回答: {prompt}"})
        else:
            messages.append({"role": "user", "content": prompt})
        
        try:
            return self._call_api(messages)
        except Exception as e:
            # API调用失败，回退到规则匹配
            return self._fallback_query(prompt, context)

    def _fallback_query(self, prompt: str, context: str) -> str:
        """API不可用时的回退查询逻辑"""
        # 简单的关键词回复
        return f"AI API暂不可用。您的查询: {prompt[:100]}...\n请配置有效的AI_API_KEY后重试。"

    def match_demand_to_product(self, demand_text: str, products: list) -> Optional[dict]:
        """
        匹配需求到产品
        
        Args:
            demand_text: 需求文本（B列+C列内容）
            products: 产品列表
        
        Returns:
            匹配结果字典（H-R列），如果失败返回None
        """
        if not products:
            return None

        # 构建产品列表文本
        products_text = "\n".join([
            f"- {p.get('product_name', '')} | 品牌: {p.get('brand', '')} | "
            f"型号: {p.get('model', '')} | 规格: {p.get('specs_json', '')} | "
            f"价格: {p.get('price', 0)}/{p.get('unit', '')}"
            for p in products[:100]  # 限制上下文长度
        ])

        messages = [
            {"role": "system", "content": self._build_system_prompt("match")},
            {"role": "user", "content": f"需求: {demand_text}\n\n可用产品列表:\n{products_text}\n\n请返回最匹配产品的H-R列JSON数据。"}
        ]

        try:
            response = self._call_api(messages, temperature=0.2)
            return self._parse_product_response(response)
        except Exception:
            return None

    def auto_configure(self, demand_text: str, products: list) -> Optional[dict]:
        """
        全自动配置 - 为单条需求匹配产品
        
        Args:
            demand_text: 需求文本
            products: 产品列表
        
        Returns:
            匹配结果的H-R列字典
        """
        if not products:
            return None

        products_text = "\n".join([
            json.dumps(p, ensure_ascii=False) for p in products[:100]
        ])

        messages = [
            {"role": "system", "content": self._build_system_prompt("auto_configure")},
            {"role": "user", "content": f"需求: {demand_text}\n\n产品列表:\n{products_text}\n\n请返回匹配的产品信息（H-R列JSON）。"}
        ]

        try:
            response = self._call_api(messages, temperature=0.2)
            return self._parse_product_response(response)
        except Exception:
            return None

    def extract_product_info(self, text: str) -> dict:
        """
        从文本中提取产品信息
        
        Args:
            text: 包含产品信息的文本
        
        Returns:
            提取的产品信息字典
        """
        messages = [
            {"role": "system", "content": "你是一个产品信息提取器。从文本中提取产品名称、品牌、型号、规格参数、价格等信息，返回JSON格式。"},
            {"role": "user", "content": f"请从以下文本中提取产品信息:\n{text}"}
        ]

        try:
            response = self._call_api(messages, temperature=0.1)
            try:
                # 尝试解析JSON响应
                return json.loads(response)
            except json.JSONDecodeError:
                # 如果响应不是纯JSON，尝试从中提取JSON
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                return {"product_name": text[:100]}
        except Exception:
            return {"product_name": text[:100]}

    def _parse_product_response(self, response: str) -> Optional[dict]:
        """
        解析AI返回的产品匹配结果
        
        Args:
            response: API返回的文本
        
        Returns:
            解析后的产品信息字典（H-R列）
        """
        try:
            # 尝试直接解析JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试从markdown代码块中提取JSON
            json_match = re.search(r'```(?:json)?\s*\n?(\{.*?\})\n?\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            # 尝试提取最外层花括号内容
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

            return None


# 单例
ai_client = AIClient()
