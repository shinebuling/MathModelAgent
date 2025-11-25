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
        
        try:
            questions_solution = json.loads(json_str)
            ic(questions_solution)
            return ModelerToCoder(questions_solution=questions_solution)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败，原始内容: {content[:500]}...")
            logger.error(f"清理后内容: {json_str[:500]}...")
            raise ValueError(f"JSON 解析错误: {e}")
