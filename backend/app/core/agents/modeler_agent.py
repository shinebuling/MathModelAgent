from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import MODELER_PROMPT
from app.schemas.A2A import CoordinatorToModeler, ModelerToCoder
from app.utils.log_util import logger
import json
import re
from icecream import ic

# TODO: 提问工具tool


class ModelerAgent(Agent):  # 继承自Agent类
    def __init__(
        self,
        task_id: str,
        model: LLM,
        max_chat_turns: int = 30,  # 添加最大对话轮次限制
    ) -> None:
        super().__init__(task_id, model, max_chat_turns)
        self.system_prompt = MODELER_PROMPT

    async def run(self, coordinator_to_modeler: CoordinatorToModeler) -> ModelerToCoder:
        await self.append_chat_history(
            {"role": "system", "content": self.system_prompt}
        )
        await self.append_chat_history(
            {
                "role": "user",
                "content": json.dumps(coordinator_to_modeler.questions),
            }
        )

        response = await self.model.chat(
            history=self.chat_history,
            agent_name=self.__class__.__name__,
        )

        content = response.choices[0].message.content

        # 提取JSON内容的方法，改进版本
        def _extract_json_from_response(content: str) -> str:
            # 移除markdown代码块标记
            content = re.sub(r"```json\s*", "", content)
            content = re.sub(r"```\s*", "", content)
            
            # 尝试找到完整的JSON对象 - 改进的匹配方法
            # 先尝试匹配完整的JSON对象（平衡的大括号）
            def find_json_object(text: str) -> str:
                start = text.find('{')
                if start == -1:
                    return text.strip()
                
                brace_count = 0
                for i in range(start, len(text)):
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            return text[start:i+1]
                
                # 如果没有找到匹配的结束括号，返回从开始到结尾
                return text[start:]
            
            json_str = find_json_object(content)
            
            # 清理控制字符
            json_str = re.sub(r"[\x00-\x1F\x7F]", "", json_str)
            
            # 移除多余的空格和换行
            json_str = json_str.strip()
            
            return json_str

        json_str = _extract_json_from_response(content)

        if not json_str:
            raise ValueError("返回的 JSON 字符串为空，请检查输入内容。")
        
        def _attempt_repair_and_load(s: str):
            """尝试修复常见的非严格 JSON 问题并解析为 Python 对象。

            修复策略（按顺序尝试）：
            - 将单引号替换为双引号
            - 用 null/true/false 替换 None/True/False
            - 移除尾随逗号
            - 为未加引号的键添加双引号（保守匹配）
            """
            # 1. 直接尝试解析
            try:
                return json.loads(s)
            except Exception:
                pass

            repaired = s

            # 2. 替换单引号为双引号（谨慎处理）
            repaired = re.sub(r"(?<!\\)\'", '"', repaired)

            # 3. 替换 Python 布尔/空值为 JSON 格式
            repaired = re.sub(r"\bNone\b", "null", repaired)
            repaired = re.sub(r"\bTrue\b", "true", repaired)
            repaired = re.sub(r"\bFalse\b", "false", repaired)

            # 4. 移除尾随逗号（在 } 或 ] 之前）
            repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)

            # 5. 为未加引号的键添加双引号（保守规则：键由非空白且不包含引号和冒号的字符组成）
            def _quote_keys(match):
                prefix = match.group(1)
                key = match.group(2).strip()
                return f'{prefix}"{key}":'

            repaired = re.sub(r'([\{,\n\s])(\s*[^"\'\n\r\t\,\:\{\}\[\]]+?)\s*:', _quote_keys, repaired)

            # 6. 再次移除不必要的控制字符和多余空白
            repaired = re.sub(r"[\x00-\x1F\x7F]", "", repaired).strip()

            # 7. 尝试解析修复后的字符串
            try:
                return json.loads(repaired)
            except Exception as e:
                # 解析仍失败，返回 None 并将修复结果作为调试信息
                logger.error("尝试修复后的 JSON 仍然无法解析。修复后示例：%s", repaired[:1000])
                raise e

        try:
            questions_solution = _attempt_repair_and_load(json_str)
            ic(questions_solution)
            return ModelerToCoder(questions_solution=questions_solution)
        except Exception as e:
            logger.error(f"首次JSON解析失败，尝试二次解析纠错")
            logger.error(f"原始内容: {content[:1000]}...")
            logger.error(f"清理后内容: {json_str[:1000]}...")
            
            # 二次解析：将错误内容回传给模型请求纠错
            repair_content = None
            try:
                logger.info("启动二次解析，请求模型纠错...")
                
                repair_prompt = f"""
你之前的回复不是有效的 JSON 格式。以下是你的原始回复：

{content}

请严格按照要求，将上述内容转换为有效的 JSON 格式。要求：
1. 直接输出 JSON，不要任何解释、注释或 markdown 代码块
2. 使用双引号，不允许单引号
3. 键名必须用双引号包围
4. 不允许尾随逗号
5. 所有值都是字符串类型
6. 格式必须是：{{"eda": "...", "ques1": "...", "sensitivity_analysis": "..."}}

请立即输出修正后的 JSON：
"""
                
                await self.append_chat_history({
                    "role": "user", 
                    "content": repair_prompt
                })
                
                repair_response = await self.model.chat(
                    history=self.chat_history,
                    agent_name=self.__class__.__name__,
                )
                
                repair_content = repair_response.choices[0].message.content
                logger.info(f"模型纠错响应: {repair_content[:500]}...")
                
                # 对纠错后的内容进行解析
                repaired_json_str = _extract_json_from_response(repair_content)
                questions_solution = _attempt_repair_and_load(repaired_json_str)
                
                logger.info("二次解析成功！")
                ic(questions_solution)
                return ModelerToCoder(questions_solution=questions_solution)
                
            except Exception as repair_error:
                logger.error(f"二次解析也失败: {repair_error}")
                if repair_content:
                    logger.error(f"纠错后内容: {repair_content[:1000]}...")
                else:
                    logger.error("未能获取纠错后的内容")
                raise ValueError(f"JSON 解析错误（包括二次纠错）: 原始错误={e}, 纠错错误={repair_error}")
