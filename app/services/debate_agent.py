"""
多智能体辩论引擎 - LangGraph 版本
基于 LangGraph 状态机实现《逆转裁判》风格的法庭辩论
支持流式输出和动作标签注入
"""

import asyncio
import json
import re
from typing import Dict, List, TypedDict, Annotated, Literal
from operator import add
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.core.config import settings
from app.core.logger import app_logger
from app.llm.factory import LLMFactory
from app.models.response import DebateResponse, AgentArgument


# ==================== 状态定义 ====================

class DebateState(TypedDict):
    """辩论状态"""
    case_description: str
    messages: Annotated[List[Dict], add]
    plaintiff_argument: str
    plaintiff_legal_basis: List[str]
    plaintiff_key_points: List[str]
    defendant_argument: str
    defendant_legal_basis: List[str]
    defendant_key_points: List[str]
    judge_opinion: str
    judge_legal_basis: List[str]
    judge_key_points: List[str]
    win_probability: Dict[str, float]
    current_speaker: str
    action_tags: List[Dict[str, str]]  # 动作标签序列


# ==================== 动作标签定义 ====================

ACTION_TAGS = {
    "OBJECTION": "异议！",
    "HOLD_IT": "等等！",
    "TAKE_THAT": "看招！",
    "SLAM": "拍桌",
    "THINK": "思考",
    "POINT": "指证",
    "CONFIDENT": "自信",
    "NERVOUS": "紧张",
    "GAVEL": "法槌",
}


# ==================== Prompt 模板（注入动作标签） ====================

PLAINTIFF_PROMPT = """你是一位经验丰富的原告方律师，专门代理劳动争议、合同纠纷等案件，擅长维护弱势方权益。

【重要】动作标签系统：
在你的回复中，如果情绪激烈或需要强调，请在句子开头使用以下动作标签：
- [OBJECTION] - 当你要提出强烈异议时
- [HOLD_IT] - 当你要打断对方或提出质疑时
- [TAKE_THAT] - 当你要出示关键证据时
- [SLAM] - 当你要拍桌强调时
- [POINT] - 当你要指证对方漏洞时
- [CONFIDENT] - 当你对论点非常自信时

示例：
"[OBJECTION] 被告的说法完全站不住脚！根据《劳动合同法》第39条..."
"[TAKE_THAT] 我这里有关键证据！公司的规章制度从未公示..."

你的任务是：
1. 仔细分析案情，找出对原告有利的事实和证据
2. 寻找适用的法律法规和司法解释
3. 构建完整的诉讼理由和索赔依据
4. 预判被告可能的抗辩，提前准备反驳
5. 在关键论点前使用动作标签增强表现力

输出要求：
- 论点要清晰有力，逻辑严密
- 法律依据要准确具体（引用《法律名称》第X条）
- 关键要点要突出重点
- 语气要坚定但专业
- 适当使用动作标签

案情描述：
{case_description}

请以原告律师的身份，提出起诉理由和索赔依据。"""


DEFENDANT_PROMPT = """你是一位经验丰富的被告方律师，擅长企业法务和诉讼抗辩，善于寻找法律漏洞和程序瑕疵。

【重要】动作标签系统：
在你的回复中，如果情绪激烈或需要强调，请在句子开头使用以下动作标签：
- [OBJECTION] - 当你要提出强烈异议时
- [HOLD_IT] - 当你要打断对方或提出质疑时
- [TAKE_THAT] - 当你要出示关键证据时
- [SLAM] - 当你要拍桌强调时
- [POINT] - 当你要指证对方漏洞时
- [CONFIDENT] - 当你对论点非常自信时

示例：
"[OBJECTION] 原告的指控毫无根据！"
"[HOLD_IT] 请等一下，原告律师的逻辑存在明显漏洞..."

你的任务是：
1. 分析原告的诉讼请求和理由，找出漏洞和不足
2. 寻找对被告有利的事实和证据
3. 提出法律上的抗辩理由
4. 质疑原告证据的合法性和关联性
5. 在反驳时使用动作标签增强气势

输出要求：
- 抗辩要有理有据，针对性强
- 法律依据要准确具体
- 关键要点要突出防御重点
- 语气要专业但不失礼
- 适当使用动作标签

案情描述：
{case_description}

原告方论点：
{plaintiff_argument}

请以被告律师的身份，提出抗辩理由和反驳意见。"""


JUDGE_PROMPT = """你是一位资深法官，具有深厚的法律功底和丰富的审判经验，秉持公正、中立、专业的原则。

你的任务是：
1. 综合分析原告和被告双方的论点
2. 评估双方证据的证明力和关联性
3. 准确适用法律法规
4. 给出中立客观的法律意见
5. 预测案件的可能判决结果和胜诉概率

【重要】你必须严格按照以下 JSON 格式输出，不要输出任何其他内容：

{{
  "plaintiff_win_rate": 65,
  "plaintiff_winning_factors": [
    "原告有利点1",
    "原告有利点2",
    "原告有利点3"
  ],
  "defendant_winning_factors": [
    "被告有利点1（原告败诉点）",
    "被告有利点2（原告败诉点）"
  ],
  "judge_summary": "## 法官综合意见\\n\\n经本院审理查明...\\n\\n### 争议焦点\\n\\n1. ...\\n\\n### 法律适用\\n\\n根据《劳动合同法》...\\n\\n### 裁判结论\\n\\n综上所述..."
}}

注意事项：
1. plaintiff_win_rate 必须是 0-100 的整数，根据案情真实分析，绝对不能总是 50
2. plaintiff_winning_factors 和 defendant_winning_factors 必须是数组，每项要具体明确
3. judge_summary 支持 Markdown 格式，可以使用 ## ### 等标题、列表、加粗等
4. 必须输出有效的 JSON，不要有任何额外的文字说明

案情描述：
{case_description}

原告方论点：
{plaintiff_argument}

被告方论点：
{defendant_argument}

请严格按照上述 JSON 格式输出。"""


# ==================== LangGraph 节点函数 ====================

class AceAttorneyDebateAgent:
    """《逆转裁判》风格的辩论引擎"""
    
    def __init__(self):
        """初始化辩论引擎"""
        self.llm = LLMFactory.create_llm()
        self.checkpointer = self._create_checkpointer()
        self.graph = self._build_graph()
        app_logger.info("⚖️  AceAttorneyDebateAgent 初始化完成（LangGraph 版本）")

    def _create_checkpointer(self):
        try:
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver
            saver = AsyncRedisSaver.from_conn_string(settings.REDIS_URL)
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._setup_async_checkpointer(saver))
            except RuntimeError:
                asyncio.run(self._setup_async_checkpointer(saver))
            return saver
        except Exception as e:
            app_logger.warning(f"DebateAgent Redis Checkpointer 不可用，回退 MemorySaver: {str(e)}")
            return MemorySaver()

    async def _setup_async_checkpointer(self, saver) -> None:
        setup = getattr(saver, "setup", None)
        if callable(setup):
            await setup()
    
    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 状态机"""
        workflow = StateGraph(DebateState)
        
        # 添加节点
        workflow.add_node("plaintiff", self._plaintiff_node)
        workflow.add_node("defendant", self._defendant_node)
        workflow.add_node("judge", self._judge_node)
        
        # 定义流转
        workflow.set_entry_point("plaintiff")
        workflow.add_edge("plaintiff", "defendant")
        workflow.add_edge("defendant", "judge")
        workflow.add_edge("judge", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
    
    async def _plaintiff_node(self, state: DebateState) -> Dict:
        """原告律师节点"""
        app_logger.info("👨‍⚖️ 原告律师正在准备论点...")
        
        prompt = PLAINTIFF_PROMPT.format(case_description=state["case_description"])
        response = await self.llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        # 提取动作标签
        action_tags = self._extract_action_tags(content)
        
        # 解析论点
        parsed = self._parse_agent_output(content, "原告律师")
        
        return {
            "plaintiff_argument": content,
            "plaintiff_legal_basis": parsed["legal_basis"],
            "plaintiff_key_points": parsed["key_points"],
            "current_speaker": "plaintiff",
            "action_tags": action_tags,
            "messages": [{"role": "plaintiff", "content": content, "actions": action_tags}]
        }
    
    async def _defendant_node(self, state: DebateState) -> Dict:
        """被告律师节点"""
        app_logger.info("👨‍💼 被告律师正在准备抗辩...")
        
        prompt = DEFENDANT_PROMPT.format(
            case_description=state["case_description"],
            plaintiff_argument=state["plaintiff_argument"]
        )
        response = await self.llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        # 提取动作标签
        action_tags = self._extract_action_tags(content)
        
        # 解析论点
        parsed = self._parse_agent_output(content, "被告律师")
        
        return {
            "defendant_argument": content,
            "defendant_legal_basis": parsed["legal_basis"],
            "defendant_key_points": parsed["key_points"],
            "current_speaker": "defendant",
            "action_tags": action_tags,
            "messages": [{"role": "defendant", "content": content, "actions": action_tags}]
        }
    
    async def _judge_node(self, state: DebateState) -> Dict:
        """法官节点 - 强制 JSON 输出"""
        app_logger.info("👨‍⚖️ 法官正在综合评议...")
        
        prompt = JUDGE_PROMPT.format(
            case_description=state["case_description"],
            plaintiff_argument=state["plaintiff_argument"],
            defendant_argument=state["defendant_argument"]
        )
        response = await self.llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        
        # 提取 JSON
        try:
            # 尝试直接解析
            judge_data = json.loads(content)
        except json.JSONDecodeError:
            # 如果失败，尝试提取 JSON 部分
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                judge_data = json.loads(json_match.group())
            else:
                # 如果还是失败，使用默认值
                app_logger.warning("⚠️  法官输出不是有效的 JSON，使用默认值")
                judge_data = {
                    "plaintiff_win_rate": 50,
                    "plaintiff_winning_factors": ["原告论点有一定道理"],
                    "defendant_winning_factors": ["被告抗辩也有依据"],
                    "judge_summary": content
                }
        
        # 确保 plaintiff_win_rate 是整数
        plaintiff_win_rate = int(judge_data.get("plaintiff_win_rate", 50))
        plaintiff_win_rate = max(0, min(100, plaintiff_win_rate))
        
        win_probability = {
            "plaintiff": plaintiff_win_rate / 100.0,
            "defendant": (100 - plaintiff_win_rate) / 100.0
        }
        
        return {
            "judge_opinion": judge_data.get("judge_summary", content),
            "judge_legal_basis": [],
            "judge_key_points": judge_data.get("plaintiff_winning_factors", []) + judge_data.get("defendant_winning_factors", []),
            "win_probability": win_probability,
            "current_speaker": "judge",
            "action_tags": [],
            "messages": [{
                "role": "judge",
                "content": content,
                "actions": [],
                "structured_result": {
                    "plaintiff_win_rate": plaintiff_win_rate,
                    "plaintiff_winning_factors": judge_data.get("plaintiff_winning_factors", []),
                    "defendant_winning_factors": judge_data.get("defendant_winning_factors", []),
                    "judge_summary": judge_data.get("judge_summary", content)
                }
            }]
        }
    
    def _extract_action_tags(self, content: str) -> List[Dict[str, str]]:
        """提取动作标签"""
        tags = []
        for tag, label in ACTION_TAGS.items():
            pattern = rf"\[{tag}\]"
            matches = re.finditer(pattern, content)
            for match in matches:
                tags.append({
                    "action": tag,
                    "label": label,
                    "position": match.start()
                })
        
        # 按位置排序
        tags.sort(key=lambda x: x["position"])
        return tags
    
    def _parse_agent_output(self, content: str, role: str) -> Dict:
        """解析智能体输出"""
        # 移除动作标签后再提取
        clean_content = re.sub(r'\[(?:OBJECTION|HOLD_IT|TAKE_THAT|SLAM|THINK|POINT|CONFIDENT|NERVOUS|GAVEL)\]', '', content)
        
        legal_basis = self._extract_legal_basis(clean_content)
        key_points = self._extract_key_points(clean_content)
        
        return {
            "legal_basis": legal_basis,
            "key_points": key_points
        }
    
    def _extract_legal_basis(self, content: str) -> List[str]:
        """提取法律依据"""
        patterns = [
            r"《[^》]+》第?\s*\d+\s*条",
            r"《[^》]+》",
        ]
        
        legal_basis = []
        for pattern in patterns:
            matches = re.findall(pattern, content)
            legal_basis.extend(matches)
        
        seen = set()
        unique_basis = []
        for item in legal_basis:
            if item not in seen:
                seen.add(item)
                unique_basis.append(item)
        
        return unique_basis[:5]
    
    def _extract_key_points(self, content: str) -> List[str]:
        """提取关键要点"""
        patterns = [
            r"(?:^|\n)\d+[.、]\s*([^\n]+)",
            r"(?:^|\n)[一二三四五六七八九十]+[.、]\s*([^\n]+)",
            r"(?:^|\n)[-•]\s*([^\n]+)",
        ]
        
        key_points = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            key_points.extend(matches)
        
        if not key_points:
            sentences = re.split(r"[。！？]", content)
            key_points = [s.strip() for s in sentences if len(s.strip()) > 10][:5]
        
        key_points = [p.strip() for p in key_points if len(p.strip()) > 5]
        return key_points[:5]
    
    def _extract_win_probability(self, content: str) -> Dict[str, float]:
        """提取胜诉概率"""
        patterns = [
            r"原告胜诉概率[：:为]\s*(\d+(?:\.\d+)?)",
            r"原告.*?(\d+)%",
            r"(\d+(?:\.\d+)?)\s*的概率.*?原告",
        ]
        
        plaintiff_prob = 0.5
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                prob_str = match.group(1)
                prob = float(prob_str)
                
                if prob > 1:
                    prob = prob / 100
                
                plaintiff_prob = prob
                break
        
        plaintiff_prob = max(0.0, min(1.0, plaintiff_prob))
        
        return {
            "plaintiff": plaintiff_prob,
            "defendant": 1.0 - plaintiff_prob
        }
    
    async def simulate_debate(self, case_description: str) -> DebateResponse:
        """模拟辩论（传统接口）"""
        if not case_description or len(case_description.strip()) < 20:
            raise ValueError("案情描述过短或为空，请提供详细的案情信息")
        
        app_logger.info(f"⚖️  开始模拟辩论（LangGraph），案情长度: {len(case_description)} 字符")
        
        try:
            # 初始化状态
            initial_state: DebateState = {
                "case_description": case_description,
                "messages": [],
                "plaintiff_argument": "",
                "plaintiff_legal_basis": [],
                "plaintiff_key_points": [],
                "defendant_argument": "",
                "defendant_legal_basis": [],
                "defendant_key_points": [],
                "judge_opinion": "",
                "judge_legal_basis": [],
                "judge_key_points": [],
                "win_probability": {"plaintiff": 0.5, "defendant": 0.5},
                "current_speaker": "",
                "action_tags": []
            }
            
            # 执行图流转
            final_state = await self.graph.ainvoke(initial_state)
            
            # 构建响应
            response = DebateResponse(
                case_description=case_description,
                plaintiff_argument=AgentArgument(
                    agent_role="原告律师",
                    argument=final_state["plaintiff_argument"],
                    legal_basis=final_state["plaintiff_legal_basis"],
                    key_points=final_state["plaintiff_key_points"]
                ),
                defendant_argument=AgentArgument(
                    agent_role="被告律师",
                    argument=final_state["defendant_argument"],
                    legal_basis=final_state["defendant_legal_basis"],
                    key_points=final_state["defendant_key_points"]
                ),
                judge_opinion=AgentArgument(
                    agent_role="法官",
                    argument=final_state["judge_opinion"],
                    legal_basis=final_state["judge_legal_basis"],
                    key_points=final_state["judge_key_points"]
                ),
                win_probability=final_state["win_probability"]
            )
            
            app_logger.info(f"✅ 辩论模拟完成，原告胜诉概率: {final_state['win_probability']['plaintiff']:.0%}")
            
            return response
        
        except Exception as e:
            app_logger.error(f"❌ 辩论模拟失败: {str(e)}")
            raise Exception(f"辩论模拟失败: {str(e)}")
    
    async def simulate_debate_stream(self, case_description: str, custom_config: Dict = None):
        """流式模拟辩论（SSE）"""
        if not case_description or len(case_description.strip()) < 20:
            raise ValueError("案情描述过短或为空")
        
        app_logger.info(f"⚖️  开始流式辩论，案情长度: {len(case_description)} 字符")
        
        # 如果提供了自定义配置，临时替换 LLM
        original_llm = None
        if custom_config and custom_config.get("api_key"):
            app_logger.info(f"🔧 使用自定义 LLM 配置进行辩论")
            original_llm = self.llm
            self.llm = LLMFactory.create_llm(
                api_key=custom_config.get("api_key"),
                base_url=custom_config.get("base_url"),
                model=custom_config.get("model"),
                temperature=custom_config.get("temperature"),
                max_tokens=custom_config.get("max_tokens")
            )
            # 重新构建图（因为节点使用了 self.llm）
            self.graph = self._build_graph()
        
        try:
            # 初始化状态
            initial_state: DebateState = {
                "case_description": case_description,
                "messages": [],
                "plaintiff_argument": "",
                "plaintiff_legal_basis": [],
                "plaintiff_key_points": [],
                "defendant_argument": "",
                "defendant_legal_basis": [],
                "defendant_key_points": [],
                "judge_opinion": "",
                "judge_legal_basis": [],
                "judge_key_points": [],
                "win_probability": {"plaintiff": 0.5, "defendant": 0.5},
                "current_speaker": "",
                "action_tags": []
            }
            
            # 流式执行
            async for event in self.graph.astream(initial_state):
                for node_name, node_output in event.items():
                    if node_name in ["plaintiff", "defendant", "judge"]:
                        # 提取消息
                        if "messages" in node_output and node_output["messages"]:
                            message = node_output["messages"][0]
                            role = message["role"]
                            
                            # 发送角色切换事件
                            yield {
                                "role": role,
                                "event": "start"
                            }
                            
                            # 如果是法官，直接发送结构化结果
                            if role == "judge" and "structured_result" in message:
                                yield {
                                    "role": "judge",
                                    "event": "result",
                                    "result": message["structured_result"]
                                }
                            else:
                                # 发送动作标签
                                for action in message.get("actions", []):
                                    yield {
                                        "role": role,
                                        "event": "action",
                                        "action": action["action"],
                                        "label": action["label"]
                                    }
                                
                                # 模拟打字机效果（分段发送）
                                content = message["content"]
                                # 移除动作标签
                                clean_content = re.sub(r'\[(?:OBJECTION|HOLD_IT|TAKE_THAT|SLAM|THINK|POINT|CONFIDENT|NERVOUS|GAVEL|EVIDENCE)\]\s*', '', content)
                                
                                # 按句子分割
                                sentences = re.split(r'([。！？\n])', clean_content)
                                current_chunk = ""
                                
                                for i, part in enumerate(sentences):
                                    current_chunk += part
                                    if part in ['。', '！', '？', '\n'] or i == len(sentences) - 1:
                                        if current_chunk.strip():
                                            yield {
                                            "role": role,
                                            "event": "content",
                                            "content": current_chunk.strip()
                                        }
                                    current_chunk = ""
                        
                        # 发送完成事件
                        yield {
                            "role": role,
                            "event": "end"
                        }
        finally:
            # 恢复原始 LLM
            if original_llm:
                self.llm = original_llm
                self.graph = self._build_graph()
                app_logger.info("🔄 已恢复默认 LLM 配置")


# 全局单例
_debate_agent_instance = None


def get_debate_agent() -> AceAttorneyDebateAgent:
    """获取辩论引擎实例"""
    global _debate_agent_instance
    
    if _debate_agent_instance is None:
        _debate_agent_instance = AceAttorneyDebateAgent()
    
    return _debate_agent_instance
