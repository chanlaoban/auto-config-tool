"""
学习引擎 - 从用户行为中学习匹配规则

从用户的手动匹配、反馈修正中提取模式，
生成可复用的匹配规则，实现持续学习改进
"""
import json
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter


class LearningEngine:
    """
    学习引擎类
    
    功能：
    1. learn_from_example: 从用户手动映射中学习
    2. learn_from_feedback: 从用户反馈修正中更新规则
    3. extract_patterns: 从历史数据中提取匹配模式
    4. generate_memory: 生成可导出的记忆数据
    """

    def __init__(self):
        """初始化学习引擎"""
        self.matching_rules: List[Dict] = []  # 匹配规则列表
        self.parameter_mappings: Dict[str, str] = {}  # 参数映射字典
        self.preferences: Dict[str, Any] = {}  # 用户偏好
        self._keyword_counter: Dict[str, int] = Counter()  # 关键词频率统计

    def load_memory(self, rules: list, mappings: dict, preferences: dict):
        """加载已有的记忆数据"""
        self.matching_rules = rules
        self.parameter_mappings = mappings
        self.preferences = preferences
        # 重建关键词频率
        for rule in rules:
            for kw in rule.get("keywords", []):
                self._keyword_counter[kw] += 1

    def learn_from_example(self, demand: dict, product_mapping: dict) -> List[Dict]:
        """
        从用户手动映射中学习匹配规则
        
        Args:
            demand: 需求数据（B=设备名称, C=招标/需求参数等）
            product_mapping: 用户选择的产品映射（H-R列）
        
        Returns:
            提取的新规则列表
        """
        new_rules = []

        # 从设备名称提取关键词
        device_name = demand.get("B", "")
        if device_name:
            keywords = self._extract_keywords(device_name)
            if keywords and product_mapping.get("H"):
                rule = {
                    "keyword": device_name,
                    "keywords": keywords,
                    "product_name": product_mapping.get("H", ""),
                    "brand": product_mapping.get("J", ""),
                    "model": product_mapping.get("K", ""),
                    "internal_code": product_mapping.get("L", ""),
                    "specs": product_mapping.get("I", ""),
                    "unit": product_mapping.get("N", ""),
                    "price": product_mapping.get("O", "0"),
                    "confidence": 0.8,
                    "source": "manual_mapping",
                }
                new_rules.append(rule)

        # 从需求参数提取规格映射
        demand_spec = demand.get("C", "")
        product_spec = product_mapping.get("I", "")
        if demand_spec and product_spec:
            # 提取参数映射关系
            mappings = self._extract_parameter_mappings(demand_spec, product_spec)
            self.parameter_mappings.update(mappings)

        # 添加到规则列表
        for rule in new_rules:
            # 检查是否已有相似规则
            existing = False
            for i, r in enumerate(self.matching_rules):
                if r.get("keyword", "").lower() == rule["keyword"].lower():
                    # 更新已有规则（增加置信度）
                    self.matching_rules[i]["confidence"] = min(
                        1.0, self.matching_rules[i].get("confidence", 0.5) + 0.1
                    )
                    existing = True
                    break
            if not existing:
                self.matching_rules.append(rule)

        return new_rules

    def learn_from_feedback(self, correction: dict) -> None:
        """
        从用户反馈修正中更新规则
        
        Args:
            correction: 修正数据，包含原始匹配和用户修正后的值
        """
        original = correction.get("original", {})
        corrected = correction.get("corrected", {})

        # 如果用户修正了产品选择，降低原规则的置信度
        if original.get("H") and corrected.get("H") and original["H"] != corrected["H"]:
            for rule in self.matching_rules:
                if rule.get("product_name") == original["H"]:
                    rule["confidence"] = max(0.1, rule.get("confidence", 0.5) - 0.2)

        # 如果用户修正了品牌
        if original.get("J") and corrected.get("J") and original["J"] != corrected["J"]:
            self.preferences["preferred_brands"] = self.preferences.get("preferred_brands", [])
            if corrected["J"] not in self.preferences["preferred_brands"]:
                self.preferences["preferred_brands"].append(corrected["J"])

        # 学习新的参数映射
        if corrected.get("I"):
            self.parameter_mappings[corrected.get("H", "")] = corrected["I"]

    def find_matching_rule(self, demand_text: str) -> Optional[Dict]:
        """
        根据需求文本查找匹配的规则
        
        Args:
            demand_text: 需求文本
        
        Returns:
            匹配到的规则（H-R列格式），无匹配返回None
        """
        if not demand_text:
            return None

        demand_lower = demand_text.lower()
        best_match = None
        best_score = 0.0

        for rule in self.matching_rules:
            score = 0.0
            keywords = rule.get("keywords", [])
            for kw in keywords:
                if kw.lower() in demand_lower:
                    score += 1.0
                # 部分匹配
                elif any(kw.lower()[:3] in demand_lower for kw in keywords if len(kw) > 3):
                    score += 0.3

            # 权重乘以置信度
            weight = rule.get("confidence", 0.5)
            score = score * weight / max(len(keywords), 1)

            if score > best_score and score > 0.3:  # 阈值0.3
                best_score = score
                best_match = rule

        if best_match:
            return {
                "H": best_match.get("product_name", ""),
                "I": best_match.get("specs", ""),
                "J": best_match.get("brand", ""),
                "K": best_match.get("model", ""),
                "L": best_match.get("internal_code", ""),
                "M": "",
                "N": best_match.get("unit", ""),
                "O": best_match.get("price", "0"),
                "P": "",
                "Q": f"规则匹配(置信度:{best_score:.2f})",
                "R": "",
            }

        return None

    def extract_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """
        从历史数据中提取匹配模式
        
        Args:
            history: 历史学习日志列表
        
        Returns:
            提取的模式信息
        """
        if not history:
            return {}

        patterns = {
            "common_keywords": [],
            "preferred_brands": [],
            "common_categories": [],
            "typical_quantities": {},
        }

        # 统计关键词频率
        keyword_freq = Counter()
        brand_freq = Counter()
        category_freq = Counter()
        quantities = []

        for entry in history:
            try:
                input_data = json.loads(entry.get("input_data", "{}"))
                output_data = json.loads(entry.get("output_data", "{}"))

                # 提取关键词
                demand = input_data.get("demand", "") or f"{input_data.get('B', '')} {input_data.get('C', '')}"
                keywords = self._extract_keywords(demand)
                for kw in keywords:
                    keyword_freq[kw] += 1

                # 提取品牌偏好
                brand = output_data.get("J", "")
                if brand:
                    brand_freq[brand] += 1

                # 提取分类
                product_name = output_data.get("H", "")
                if product_name:
                    category_freq[product_name[:10]] += 1

                # 提取数量
                qty = output_data.get("M", "0")
                try:
                    quantities.append(float(qty))
                except (ValueError, TypeError):
                    pass

            except (json.JSONDecodeError, KeyError):
                continue

        # 取最常见的关键词（过滤单字和通用词）
        self._keyword_counter.update(keyword_freq)
        common_kw = [kw for kw, count in self._keyword_counter.most_common(20) if len(kw) >= 2 and count >= 2]
        patterns["common_keywords"] = common_kw[:10]

        # 品牌偏好
        patterns["preferred_brands"] = [b for b, _ in brand_freq.most_common(5)]

        # 数量统计
        if quantities:
            patterns["typical_quantities"] = {
                "min": min(quantities),
                "max": max(quantities),
                "avg": sum(quantities) / len(quantities),
            }

        # 更新偏好
        if patterns["preferred_brands"]:
            self.preferences["preferred_brands"] = patterns["preferred_brands"]

        return patterns

    def generate_memory(self) -> Dict:
        """
        生成可序列化的记忆字典
        
        Returns:
            包含所有学习数据的字典
        """
        return {
            "version": "1.0",
            "matching_rules": self.matching_rules,
            "parameter_mappings": self.parameter_mappings,
            "preferences": self.preferences,
            "stats": {
                "total_rules": len(self.matching_rules),
                "total_mappings": len(self.parameter_mappings),
                "top_keywords": [kw for kw, _ in self._keyword_counter.most_common(10)],
            },
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """
        从文本中提取关键词
        
        Args:
            text: 输入文本
        
        Returns:
            关键词列表
        """
        if not text:
            return []

        # 中文关键词提取（基于标点、空格分割）
        # 去除常见标点和单位
        cleaned = re.sub(r'[，。、；：！？""''（）\(\)\[\]【】\-/\s]', ' ', text)
        parts = [p.strip() for p in cleaned.split() if p.strip()]

        # 合并连续中文字符
        keywords = []
        for part in parts:
            # 中文词组
            chinese_parts = re.findall(r'[\u4e00-\u9fff]{2,}', part)
            keywords.extend(chinese_parts)

            # 英文/数字部分
            eng_parts = re.findall(r'[A-Za-z0-9\-]+', part)
            keywords.extend(eng_parts)

        # 过滤停用词和过短的词
        stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
                      "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
                      "没有", "看", "好", "自己", "这", "他", "她", "它", "们"}
        keywords = [kw for kw in keywords if kw not in stop_words]

        # 去重但保持顺序
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords[:10]  # 最多返回10个关键词

    def _extract_parameter_mappings(self, demand_spec: str, product_spec: str) -> Dict[str, str]:
        """
        从需求和产品规格中提取参数映射关系
        
        Args:
            demand_spec: 需求规格文本
            product_spec: 产品规格文本
        
        Returns:
            参数映射字典 {需求参数名: 产品参数名}
        """
        mappings = {}

        # 提取键值对模式
        demand_pairs = re.findall(r'([^：:]{1,20})[：:]\s*([^；;，,]+)', demand_spec)
        product_pairs = re.findall(r'([^：:]{1,20})[：:]\s*([^；;，,]+)', product_spec)

        demand_params = {k.strip(): v.strip() for k, v in demand_pairs}
        product_params = {k.strip(): v.strip() for k, v in product_pairs}

        # 尝试匹配相似的参数名
        for d_key in demand_params:
            best_match = None
            best_score = 0
            for p_key in product_params:
                # 简单的字符串相似度
                score = self._str_similarity(d_key, p_key)
                if score > best_score and score > 0.3:
                    best_score = score
                    best_match = p_key

            if best_match:
                mappings[d_key] = best_match

        return mappings

    def _str_similarity(self, s1: str, s2: str) -> float:
        """计算两个字符串的简单相似度"""
        if not s1 or not s2:
            return 0.0
        s1, s2 = s1.lower(), s2.lower()
        if s1 == s2:
            return 1.0
        # 基于公共子序列的简单相似度
        common = sum(1 for c in s1 if c in s2)
        return common / max(len(s1), len(s2))
