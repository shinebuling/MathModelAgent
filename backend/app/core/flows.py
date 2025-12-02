from app.models.user_output import UserOutput
from app.tools.base_interpreter import BaseCodeInterpreter
from app.core.agents.modeler_agent import ModelerToCoder


class Flows:
    def __init__(self, questions: dict[str, str | int]):
        self.flows: dict[str, dict] = {}
        self.questions: dict[str, str | int] = questions

    def set_flows(self, ques_count: int):
        ques_str = [f"ques{i}" for i in range(1, ques_count + 1)]
        seq = [
            "firstPage",
            "RepeatQues",
            "analysisQues",
            "modelAssumption",
            "symbol",
            "eda",
            *ques_str,
            "sensitivity_analysis",
            "judge",
        ]
        self.flows = {key: {} for key in seq}

    def get_solution_flows(
        self, questions: dict[str, str | int], modeler_response: ModelerToCoder
    ):
        questions_quesx = {
            key: value
            for key, value in questions.items()
            if key.startswith("ques") and key != "ques_count"
        }
        
        # 检查建模手返回的解决方案中是否包含所有问题的答案
        from app.utils.log_util import logger
        missing_keys = []
        for key in questions_quesx.keys():
            if key not in modeler_response.questions_solution:
                missing_keys.append(key)
        
        if missing_keys:
            logger.warning(f"建模手返回的解决方案缺少以下问题的答案: {missing_keys}")
            logger.warning(f"用户问题键: {list(questions_quesx.keys())}")
            logger.warning(f"建模手返回的键: {list(modeler_response.questions_solution.keys())}")
            logger.warning(f"将为缺失的问题提供默认解决方案")
            
            # 为缺失的问题提供默认解决方案
            for missing_key in missing_keys:
                problem_text = questions_quesx.get(missing_key, f"问题{missing_key[-1]}")
                default_solution = f"针对问题'{problem_text}'，建议采用数学建模方法进行求解，包括数据预处理、模型构建、参数优化和结果验证等步骤。可视化方案：绘制相关图表展示分析结果。"
                modeler_response.questions_solution[missing_key] = default_solution
                logger.info(f"已为{missing_key}提供默认解决方案")
        
        ques_flow = {
            key: {
                "coder_prompt": f"""
                        参考建模手给出的解决方案{modeler_response.questions_solution[key]}
                        完成如下问题{value}
                    """,
            }
            for key, value in questions_quesx.items()
            if key in modeler_response.questions_solution  # 额外保护
        }
        # 检查必需的键是否存在
        required_keys = ["eda", "sensitivity_analysis"]
        for req_key in required_keys:
            if req_key not in modeler_response.questions_solution:
                logger.warning(f"建模手返回的解决方案缺少必需的键: {req_key}，将提供默认方案")
                
                # 提供默认方案
                if req_key == "eda":
                    default_eda = "进行探索性数据分析：1)数据概览和基本统计；2)缺失值和异常值检测；3)变量分布可视化；4)相关性分析；5)数据清洗和预处理。可视化方案：绘制直方图、箱线图、散点图、相关性热力图等。"
                    modeler_response.questions_solution[req_key] = default_eda
                elif req_key == "sensitivity_analysis":
                    default_sensitivity = "对模型关键参数进行敏感性分析：1)识别关键输入参数；2)设定参数变化范围(±10%,±20%)；3)分析参数变化对结果的影响；4)评估模型稳定性。可视化方案：绘制龙卷风图、蜘蛛图展示参数敏感性。"
                    modeler_response.questions_solution[req_key] = default_sensitivity
                
                logger.info(f"已为{req_key}提供默认解决方案")
        
        flows = {
            "eda": {
                # TODO ： 获取当前路径下的所有数据集
                "coder_prompt": f"""
                        参考建模手给出的解决方案{modeler_response.questions_solution["eda"]}
                        对当前目录下数据进行EDA分析(数据清洗,可视化),清洗后的数据保存当前目录下,**不需要复杂的模型**
                    """,
            },
            **ques_flow,
            "sensitivity_analysis": {
                "coder_prompt": f"""
                        参考建模手给出的解决方案{modeler_response.questions_solution["sensitivity_analysis"]}
                        完成敏感性分析
                    """,
            },
        }
        return flows

    def get_write_flows(
        self, user_output: UserOutput, config_template: dict, bg_ques_all: str
    ):
        model_build_solve = user_output.get_model_build_solve()
        flows = {
            "firstPage": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{config_template["firstPage"]}，撰写标题，摘要，关键词""",
            "RepeatQues": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{config_template["RepeatQues"]}，撰写问题重述""",
            "analysisQues": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{config_template["analysisQues"]}，撰写问题分析""",
            "modelAssumption": f"""问题背景{bg_ques_all},不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{config_template["modelAssumption"]}，撰写模型假设""",
            "symbol": f"""不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{config_template["symbol"]}，撰写符号说明部分""",
            "judge": f"""不需要编写代码,根据模型的求解的信息{model_build_solve}，按照如下模板撰写：{config_template["judge"]}，撰写模型的评价部分""",
        }
        return flows

    def get_writer_prompt(
        self,
        key: str,
        coder_response: str,
        code_interpreter: BaseCodeInterpreter,
        config_template: dict,
    ) -> str:
        """根据不同的key生成对应的writer_prompt

        Args:
            key: 任务类型
            coder_response: 代码执行结果

        Returns:
            str: 生成的writer_prompt
        """
        code_output = code_interpreter.get_code_output(key)

        questions_quesx_keys = self.get_questions_quesx_keys()
        bgc = self.questions["background"]
        quesx_writer_prompt = {
            key: f"""
                    问题背景{bgc},不需要编写代码,代码手得到的结果{coder_response},{code_output},按照如下模板撰写：{config_template[key]}
                """
            for key in questions_quesx_keys
        }

        writer_prompt = {
            "eda": f"""
                    问题背景{bgc},不需要编写代码,代码手得到的结果{coder_response},{code_output},按照如下模板撰写：{config_template["eda"]}
                """,
            **quesx_writer_prompt,
            "sensitivity_analysis": f"""
                    问题背景{bgc},不需要编写代码,代码手得到的结果{coder_response},{code_output},按照如下模板撰写：{config_template["sensitivity_analysis"]}
                """,
        }

        if key in writer_prompt:
            return writer_prompt[key]
        else:
            raise ValueError(f"未知的任务类型: {key}")

    def get_questions_quesx_keys(self) -> list[str]:
        """获取问题1,2...的键"""
        return list(self.get_questions_quesx().keys())

    def get_questions_quesx(self) -> dict[str, str]:
        """获取问题1,2,3...的键值对"""
        # 获取所有以 "ques" 开头的键值对
        questions_quesx = {
            key: value
            for key, value in self.questions.items()
            if key.startswith("ques") and key != "ques_count"
        }
        return questions_quesx

    def get_seq(self, ques_count: int) -> dict[str, str]:
        ques_str = [f"ques{i}" for i in range(1, ques_count + 1)]
        seq = [
            "firstPage",
            "RepeatQues",
            "analysisQues",
            "modelAssumption",
            "symbol",
            "eda",
            *ques_str,
            "sensitivity_analysis",
            "judge",
        ]
        return {key: "" for key in seq}
