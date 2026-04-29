"""
匹配引擎 - 基于规则的语义匹配

提供产品匹配的核心能力：
1. 关键词匹配
2. 规格参数比对
3. 产品相关性排序
4. 价格计算

当AI服务不可用时，使用此引擎进行纯规则匹配
"""
import re
import json
from typing import List, Dict, Optional, Tuple
from collections import Counter


class MatchingEngine:
    """
    匹配引擎类 - 实现基于规则的产品匹配逻辑
    """

    def __init__(self):
        """初始化匹配引擎"""
        pass

    def find_best_match(self, demand_text: str, knowledge_base: list) -> Optional[Dict]:
        """
        根据需求文本，在知识库中查找最佳匹配产品
        
        Args:
            demand_text: 需求文本（B列设备名称 + C列招标参数）
            knowledge_base: 知识库产品列表
        
        Returns:
            最佳匹配产品信息，无匹配返回None
        """
        if not demand_text or not knowledge_base:
            return None

        # 打分排序
        scored_products = self.rank_products(demand_text, knowledge_base)
        if scored_products and scored_products[0].get("_score", 0) > 0:
            best = scored_products[0]
            # 移除内部评分字段
            best.pop("_score", None)
            return best

        return None

    def compare_specs(self, demand_spec: str, product_spec: str) -> List[str]:
        """
        对比需求规格和产品规格，找出不满足的参数项
        
        Args:
            demand_spec: 需求规格文本（C列内容）
            product_spec: 产品规格文本（I列内容）
        
        Returns:
            不满足的参数项列表
        """
        if not demand_spec or not product_spec:
            return []

        non_matching = []

        # 提取需求中的参数键值对
        demand_params = self._extract_params(demand_spec)
        product_params = self._extract_params(product_spec)

        # 对比每个需求参数
        for key, value in demand_params.items():
            if key in product_params:
                prod_value = product_params[key]
                # 检查值是否匹配（数值比较）
                if not self._values_match(value, prod_value):
                    non_matching.append(f"{key}: 需求{value} ≠ 产品{prod_value}")
            else:
                # 需求中有但产品中没有的参数
                # 尝试模糊匹配参数名
                found = False
                for p_key in product_params:
                    if self._param_name_similar(key, p_key):
                        found = True
                        if not self._values_match(value, product_params[p_key]):
                            non_matching.append(f"{key}: 需求{value} ≠ 产品{product_params[p_key]}")
                        break
                if not found:
                    non_matching.append(f"{key}: {value}（产品无此参数）")

        return non_matching

    def rank_products(self, demand_text: str, products: list) -> list:
        """
        根据需求文本对产品进行相关性排序
        
        Args:
            demand_text: 需求文本
            products: 产品列表
        
        Returns:
            按相关性评分排序的产品列表（含_score字段）
        """
        if not products:
            return []

        demand_lower = demand_text.lower()

        # 提取需求中的关键词
        demand_keywords = self._extract_search_keywords(demand_text)

        scored = []
        for product in products:
            score = self._calculate_relevance(demand_lower, demand_keywords, product)
            product_copy = dict(product)
            product_copy["_score"] = score
            scored.append(product_copy)

        # 按评分降序排列
        scored.sort(key=lambda x: x["_score"], reverse=True)
        return scored

    def calculate_price(self, quantity: float, unit_price: float) -> Dict:
        """
        计算产品总价
        
        Args:
            quantity: 数量
            unit_price: 单价
        
        Returns:
            包含单价、数量和总价的字典
        """
        try:
            qty = float(quantity) if quantity else 0
            price = float(unit_price) if unit_price else 0
        except (ValueError, TypeError):
            qty = 0
            price = 0

        total = qty * price
        return {
            "quantity": int(qty) if qty == int(qty) else qty,
            "unit_price": round(price, 2),
            "total": round(total, 2),
        }

    def _calculate_relevance(self, demand_lower: str, demand_keywords: list, product: dict) -> float:
        """
        计算产品与需求的相关性评分
        
        Args:
            demand_lower: 小写的需求文本
            demand_keywords: 需求关键词列表
            product: 产品信息
        
        Returns:
            相关性评分（0-100）
        """
        score = 0.0

        # 构建产品搜索文本
        product_text = " ".join(filter(None, [
            product.get("product_name", ""),
            product.get("brand", ""),
            product.get("model", ""),
            product.get("internal_code", ""),
            product.get("category", ""),
            product.get("specs_json", ""),
        ])).lower()

        # 1. 关键词命中评分（最高60分）
        keyword_matches = 0
        for kw in demand_keywords:
            if kw.lower() in product_text:
                keyword_matches += 1
                score += 10.0

        # 关键词覆盖率奖励
        if demand_keywords and keyword_matches > 0:
            coverage = keyword_matches / len(demand_keywords)
            score += coverage * 20.0

        # 2. 完整产品名匹配（最高20分）
        product_name = product.get("product_name", "").lower()
        if product_name and product_name in demand_lower:
            score += 20.0
        elif demand_lower and demand_lower[:10] in product_text:
            score += 10.0

        # 3. 品牌匹配（最高10分）
        brand = product.get("brand", "").lower()
        if brand and brand in demand_lower:
            score += 10.0

        # 4. 型号匹配（最高10分）
        model = product.get("model", "").lower()
        if model and model in demand_lower:
            score += 10.0

        # 5. 内部编码匹配（最高5分）
        internal_code = product.get("internal_code", "").lower()
        if internal_code and internal_code in demand_lower:
            score += 5.0

        # 6. 分类匹配奖励（最高5分）
        category = product.get("category", "").lower()
        if category:
            cat_keywords = re.findall(r'[\u4e00-\u9fff]{2,}', category)
            for ck in cat_keywords:
                if ck in demand_lower:
                    score += 2.5
                    break

        return score

    def _extract_params(self, spec_text: str) -> Dict[str, str]:
        """
        从规格文本中提取参数键值对
        
        Args:
            spec_text: 规格文本（如 "电压:220V; 功率:100W"）
        
        Returns:
            参数字典 {参数名: 参数值}
        """
        params = {}

        if not spec_text:
            return params

        # 尝试JSON格式
        try:
            if spec_text.startswith("{"):
                return json.loads(spec_text)
        except json.JSONDecodeError:
            pass

        # 尝试多种分隔符模式
        # 模式1: 参数名:值; 参数名:值;
        # 模式2: 参数名=值, 参数名=值
        # 模式3: 参数名：值；参数名：值；

        # 统一分隔符
        # 先把中文分号逗号换成英文
        text = spec_text.replace("；", ";").replace("，", ",").replace("：", ":").replace("＝", "=")

        # 按分号或换行分割
        pairs = re.split(r'[;\n]+', text)

        for pair in pairs:
            pair = pair.strip()
            if not pair:
                continue

            # 尝试冒号分割
            if ":" in pair:
                parts = pair.split(":", 1)
            elif "=" in pair:
                parts = pair.split("=", 1)
            else:
                continue

            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                if key and value:
                    params[key] = value

        return params

    def _values_match(self, demand_val: str, product_val: str) -> bool:
        """
        检查两个参数值是否匹配
        
        Args:
            demand_val: 需求值
            product_val: 产品值
        
        Returns:
            是否匹配
        """
        if not demand_val or not product_val:
            return True  # 空值视为匹配

        d_val = demand_val.strip().lower()
        p_val = product_val.strip().lower()

        # 完全匹配
        if d_val == p_val:
            return True

        # 数值比较 - 提取数字
        d_nums = re.findall(r'(\d+\.?\d*)', d_val)
        p_nums = re.findall(r'(\d+\.?\d*)', p_val)

        if d_nums and p_nums:
            # 比较所有数值对
            for dn in d_nums:
                for pn in p_nums:
                    try:
                        d_num = float(dn)
                        p_num = float(pn)
                        # 允许5%的误差
                        if d_num > 0 and abs(d_num - p_num) / d_num <= 0.05:
                            return True
                    except ValueError:
                        continue

        # 范围匹配（如 "100-200" 包含 "150"）
        range_match = re.match(r'(\d+\.?\d*)\s*[-~]\s*(\d+\.?\d*)', d_val)
        if range_match:
            try:
                low = float(range_match.group(1))
                high = float(range_match.group(2))
                for pn in p_nums:
                    p_num = float(pn)
                    if low <= p_num <= high:
                        return True
            except ValueError:
                pass

        # 包含关系
        if d_val in p_val or p_val in d_val:
            return True

        return False

    def _param_name_similar(self, name1: str, name2: str) -> bool:
        """
        检查两个参数名是否相似（同义词识别）
        
        Args:
            name1: 参数名1
            name2: 参数名2
        
        Returns:
            是否相似
        """
        if not name1 or not name2:
            return False

        n1 = name1.strip().lower()
        n2 = name2.strip().lower()

        if n1 == n2:
            return True

        # 常见同义词映射
        synonyms = {
            "电压": ["额定电压", "工作电压", "电压范围", "输入电压", "电源电压"],
            "功率": ["额定功率", "工作功率", "输出功率", "输入功率", "最大功率"],
            "电流": ["额定电流", "工作电流", "输入电流", "输出电流", "最大电流"],
            "尺寸": ["外形尺寸", "外形", "大小", "规格尺寸", "体积"],
            "重量": ["净重", "毛重", "质量", "总重"],
            "温度": ["工作温度", "环境温度", "运行温度", "使用温度"],
            "材质": ["材料", "材料材质", "外壳材质", "主体材质"],
            "颜色": ["色彩", "外观颜色", "机身颜色"],
        }

        for key, syn_list in synonyms.items():
            if n1 in syn_list or n1 == key:
                if n2 in syn_list or n2 == key:
                    return True

        # 公共子串检查
        if len(n1) >= 2 and len(n2) >= 2:
            # 一个参数名包含另一个
            if n1 in n2 or n2 in n1:
                return True

        return False

    def _extract_search_keywords(self, text: str) -> List[str]:
        """
        从文本中提取搜索关键词
        
        Args:
            text: 输入文本
        
        Returns:
            关键词列表
        """
        if not text:
            return []

        keywords = []

        # 提取中文词组（2个汉字以上）
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
        keywords.extend(chinese_words)

        # 提取英文/数字型号
        eng_nums = re.findall(r'[A-Za-z0-9][A-Za-z0-9\-\.\+/]+[A-Za-z0-9]', text)
        keywords.extend(eng_nums)

        # 过滤停用词
        stop_words = {"的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
                      "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会",
                      "着", "没有", "看", "好", "自己", "这", "他", "她", "它", "们",
                      "参数", "需求", "设备", "型号", "规格", "招标"}

        keywords = [kw for kw in keywords if kw not in stop_words]

        # 去重
        seen = set()
        unique_kw = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_kw.append(kw)

        return unique_kw
