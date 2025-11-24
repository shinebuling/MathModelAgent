from app.core.agents.agent import Agent
from app.core.llm.llm import LLM
from app.core.prompts import COORDINATOR_PROMPT
import json
import re
from app.utils.log_util import logger
from app.schemas.A2A import CoordinatorToModeler


class CoordinatorAgent(Agent):
    def __init__(
        self,
        task_id: str,
        model: LLM,
        max_chat_turns: int = 30,
    ) -> None:
        super().__init__(task_id, model, max_chat_turns)
        self.system_prompt = COORDINATOR_PROMPT
    
    def _extract_json_from_response(self, content: str) -> str:
        """从响应内容中提取JSON字符串"""
        if not content:
            return ""
        
        # 移除think标签
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        
        # 移除代码块标记
        content = content.replace("```json", "").replace("```", "")
        
        # 尝试找到JSON对象
        json_match = re.search(r'{.*}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = content
        
        # 清理控制字符
        json_str = re.sub(r"[\x00-\x1F\x7F]", "", json_str)
        
        # 移除多余的空格和换行
        json_str = json_str.strip()
        
        logger.debug(f"清理后JSON: {json_str[:200]}...")
        return json_str

    async def run(self, ques_all: str) -> CoordinatorToModeler:
        """用户输入问题 使用LLM 格式化 questions"""
        await self.append_chat_history(
            {"role": "system", "content": self.system_prompt}
        )
        await self.append_chat_history({"role": "user", "content": ques_all})
        max_retries = 3
        attempt = 0
        while attempt <= max_retries:
            try:
                response = await self.model.chat(
                    history=self.chat_history,
                    agent_name=self.__class__.__name__,
                )
                json_str = response.choices[0].message.content
                logger.debug(f"原始响应内容: {json_str[:200]}...")

                # 增强JSON字符串清理
                json_str = self._extract_json_from_response(json_str)

                if not json_str:
                    raise ValueError("返回的 JSON 字符串为空")

                questions = json.loads(json_str)
                ques_count = questions["ques_count"]
                logger.info(f"questions:{questions}")
                return CoordinatorToModeler(questions=questions, ques_count=ques_count)
                
            except (json.JSONDecodeError, ValueError, KeyError) as e:
                attempt += 1
                logger.warning(f"解析失败 (尝试 {attempt}/{max_retries}): {str(e)}")
                logger.debug(f"问题内容: {json_str[:500]}")
                
                if attempt > max_retries:
                    logger.error(f"超过最大重试次数，放弃解析")
                    logger.error(f"最终失败的内容: {json_str}")
                    raise RuntimeError(f"无法解析模型响应: {str(e)}\n原始内容: {json_str[:200]}")
                    
                # 添加更具体的错误反馈提示
                if "Expecting value" in str(e):
                    error_prompt = "⚠️ JSON格式错误：响应必须是纯JSON对象，请移除所有<think>标签和其他非JSON内容，只输出{}格式的JSON。"
                elif "JSONDecodeError" in str(e):
                    error_prompt = "⚠️ JSON语法错误：请检查括号、引号、逗号是否正确匹配。"
                else:
                    error_prompt = f"⚠️ 解析错误: {str(e)}。请输出标准JSON格式。"
                    
                await self.append_chat_history({
                    "role": "system", 
                    "content": error_prompt
                })
        
        # 永远不会执行到这里
        raise RuntimeError("意外的流程终止")
