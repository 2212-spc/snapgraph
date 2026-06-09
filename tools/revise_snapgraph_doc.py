from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph


SRC = Path(
    "/Users/apple/Library/Containers/com.tencent.xinWeChat/Data/Documents/"
    "xwechat_files/wxid_kc7bo2j85lzq12_2aaf/temp/RWTemp/2026-05/"
    "0e34e73a8d566345227970cdf0e76954/SnapGraph_作品策划完整说明 (1).docx"
)
OUT_DIR = Path(
    "/Users/apple/Documents/Codex/2026-04-30/code-person-snapgraph-codex-cognitive-llm/"
    "snapgraph/outputs/doc_review"
)
OUT = OUT_DIR / "SnapGraph_作品策划完整说明_修订版.docx"


PARAGRAPH_REPLACEMENTS = {
    "SnapGraph 是我们对这个困境的回答。它不是又一个 AI 助手,也不是又一个笔记工具。它做三件被忽视的事:让你随手把想法丢进去(idea 暂存站),让单点保存随时间慢慢长成图谱(开花),让 AI 基于你自己写过的内容回答你(本地知识网络、低幻觉)。": (
        "SnapGraph 是我们对这个困境的回答。它不是又一个 AI 助手,也不是又一个笔记工具。它做三件被忽视的事:让你快速保存原始材料与当时的判断;让你在需要时找回过去写下的原话、来源与证据链;让 AI 在这些证据之上与你深聊,并在没有可靠证据时诚实说不知道。"
    ),
    "SnapGraph 是一个让 AI 召回「过去的你」的认知记忆图谱。": (
        "SnapGraph 是一个证据优先的认知记忆工作台:先找回你过去写下的判断和原始来源,再让 AI 基于这些证据与你深聊。"
    ),
    "── A cognitive memory graph that gives you back what you used to think.": (
        "── An evidence-first memory workbench for recovering past judgments, sources, and grounded AI conversations."
    ),
    "SnapGraph 不是又一个 AI 助手,也不是又一个笔记工具。它做三件被忽视的事:": (
        "SnapGraph 不是又一个 AI 助手,也不是又一个笔记工具。它做三件被忽视、但真正决定长期信任的事:"
    ),
    "①  是你 idea 的暂存站": "①  是你材料与判断的快速暂存站",
    "不需要复杂的一次性大文件上传。任何时候随手丢进去一句话、一张截图、一段对话,系统帮你接住。SnapGraph 不要求你\"先把所有材料整理好\",它要求你的相反 —— 想到什么就丢什么进来。": (
        "不要求用户先整理知识库。任何时候丢进去一句话、一张截图、一段对话或一个文件,系统先保存 raw source、时间、来源与可追溯索引;如果用户愿意补一句原因,这句话会成为最高置信的 user-stated 记忆。"
    ),
    "②  随时间积累慢慢开花": "②  随时间积累形成可验证的证据链",
    "单点保存最终长成完整的本地图谱。AI 帮你看到「上周的笔记」和「上个月那篇论文」之间你自己都没意识到的暗线关联 —— 不是把两份资料并排显示,而是发现它们指向同一个尚未表达的判断。": (
        "单点保存不会被包装成炫酷图谱给用户管理。图谱是后台推理底座:当 AI 说一条连接、一条反证或一个新洞察时,用户可以展开看到它依据了哪几段原话、哪些来源、哪些关系仍需确认。"
    ),
    "③  数据不出手机的本地知识网络": "③  本地优先、调用透明的个人证据库",
    "基于你自己保存过的内容回答,低幻觉、可追溯、可拒答。问什么都先问\"我之前说过什么\"—— 这是和通用 AI 助手最根本的不同:它不替你生成新答案,它把你过去的判断还给现在的你。": (
        "基于你自己保存过的内容回答,低幻觉、可追溯、可拒答。当前 Web demo 已接入 Qwen API 做真实模型验证,并保留 Provider 抽象;产品必须清楚标注哪些材料会被发送给模型、哪些私密材料永不外发。"
    ),
    "XXX 教授,来自 XX 大学。研究方向涵盖人机交互 / 认知科学 / AI 应用伦理。指导我们在\"AI 不替代人\"这条立场上没有偏移。": (
        "（待填写）指导老师信息需在提交前补齐。这里不应虚构导师姓名、学校或研究方向。"
    ),
    "这个用户叫小林。他是 2026 年 4 月在我们 32 人深度访谈中,第 9 位接受我们调研的大三学生。下面的所有细节,要么来自他本人的描述,要么来自我们 demo 真机上他亲手操作的截图。": (
        "这个用户叫小林。以下故事基于 2026 年 4 月学生与年轻知识工作者访谈中的高频场景合成,用于说明产品体验闭环;真实提交时,需要把“访谈原话、样本编号、可展示截图”与虚构化叙事清楚分开。"
    ),
    "── 小林  ·  2026-04-XX  ·  23:40  ·  保存为思考回执": (
        "── 小林  ·  2026-04-XX（待补具体日期） · 23:40 · 保存为可找回的记忆"
    ),
    "系统替他在背后自动做了 4 件事(这都是 AI 的活):": (
        "系统在背后自动做了 4 件事,但必须区分“材料摘要”和“用户保存原因”:"
    ),
    "整个保存动作,他花了 8 秒。系统返回\"已保存为可找回的记忆\"。他锁屏,睡了。": (
        "整个保存动作可以在 8 秒左右完成,但这不是强制流程。用户可以只保存材料不写理由;系统返回“已保存为可找回的记忆”,并把理由状态标为待补。"
    ),
    "期间他保存了 47 条新材料 —— 截图、论文、AI 对话、随手想到的句子。这些都被同样地接住了:停 5 秒,补一句话,系统自动建立关联。但他没有特别在意 —— 这些保存的动作像呼吸一样自然,他不需要为它做任何整理工作。": (
        "期间他保存了 47 条新材料 —— 截图、论文、AI 对话、随手想到的句子。这些都被同样地接住:能写原因就写,写不出来也先保存;系统只把用户亲手写下的理由标为 user-stated,其他摘要与连接都保留为 AI-inferred 或待确认。"
    ),
    "「不需要整理」是 SnapGraph 跟所有\"知识管理工具\"的根本区别 —— 我们不假装\"有空整理是个好习惯\",我们假装\"你永远没空整理\",所以系统替你整理。": (
        "「不要求先整理」是 SnapGraph 跟传统知识管理工具的根本区别。系统可以帮用户提取结构、生成摘要、提出可能连接,但不能把 AI 的猜测写成用户自己的意图。"
    ),
    "SnapGraph 在 600 毫秒内返回了一张「思考回执」—— 不是 AI 重新总结的新答案,是他两周前自己写下的那一行原话:": (
        "SnapGraph 先返回本地检索到的候选证据,再由 Qwen 做必要的整理。真实接入 Qwen 后,当前回答通常在 15-25 秒区间,所以 V0 需要“先给本地证据、再流式补充解释”的体验优化。返回的核心不是 AI 重新总结的新答案,而是他两周前自己写下的那一行原话:"
    ),
    "SnapGraph 没有简单\"找出来\"原话,它在背后悄悄发现了一件事:他原本\"不做协作\"的判断,过去一周内已经被 3 个新材料反向挑战了。系统主动提示他重新审视。": (
        "SnapGraph 没有把反证当成确定结论。它会提示:系统找到几条可能挑战旧判断的新材料,并展示证据链让用户确认“仍然成立 / 需要复核 / 已过期”。"
    ),
    "这是 SnapGraph 的第二种回答:不是单纯的找回,是反向监控 —— 帮人发现自己旧判断的盲区。": (
        "这是 SnapGraph 的第二种回答:不是单纯找回,而是把旧判断和新证据放在一起,帮助用户判断它是否仍然成立。"
    ),
    "这就是我们在 32 位用户的真实场景里反复看到的东西。我们的产品不是设计出来的,是观察出来的。": (
        "这就是我们在访谈和真实文件测试里反复看到的东西:用户不是想管理知识库,而是在压力时刻想找回旧判断、原始来源和可信下一步。"
    ),
    "我们给整本产品和文档定的视觉立场叫「深夜书房 · 索引卡」。": (
        "我们重新收敛后的视觉立场叫「现代、冷静、精密的证据工作台」。"
    ),
    "整体视觉风格  ·  深夜书房 · 索引卡   Visual System · 1960s editorial typography": (
        "整体视觉风格  ·  冷静证据工作台   Visual System · modern evidence workbench"
    ),
    "参考来源:1960 年代编辑刊物 + 中文古籍版面。我们采用的关键元素是衬线宋体 + 暖纸 + 墨色 —— 营造\"思考被严肃对待\"的克制氛围,与\"AI 不抢话\"的产品立场视觉一致。": (
        "参考方向更接近 Linear / Raycast / Claude / Zotero:清晰、克制、可信。用户原话可以使用轻微 editorial quote treatment,但整体不能变成怀旧日记、古籍风或装饰性 AI 光效。"
    ),
    "SnapGraph 的主屏不是搜索框,也不是聊天框。它的中央是一句话提示:「问问过去的你」。": (
        "SnapGraph 的主屏首先是一个安静的召回输入框,提示语是「问问过去的你」。它既能找东西,也能进入深聊,但不要求用户先理解图谱或选择技术模式。"
    ),
    "这是个反向心智设计 —— 当用户打开手机时,我们要他先想到\"我之前怎么想的\",而不是\"我现在想问 AI 什么\"。这一个 framing 的改变,把整个产品从\"通用 AI 助手\"位置上拉到了\"个人记忆延伸\"位置上。": (
        "这是个反向心智设计:默认先找回过去的原话、来源和证据,再进入 AI 讨论。AI 可以深聊,但每个关键判断都要能展开依据链。"
    ),
    "我们的原型在 vivo X100 / iQOO Neo9 真机上跑通,采用 393×852 真比例适配。6 个关键屏覆盖产品完整心智模型:": (
        "当前原型是 Vue + FastAPI Web demo,按 393×852 移动端比例做交互验证。6 个关键屏覆盖产品完整心智模型;原生真机版本是下一阶段工程目标。"
    ),
    "我们用一条 SVG 河流曲线把 7 个节点串起来,而不是死板的横向流程图 —— 因为这条流程是\"流动的、跨时间的、有起伏的\",不是机械的步骤。": (
        "交互流程不再强调装饰性的河流图,而是强调用户的真实闭环:保存材料、可选补一句原因、找回原话、打开原文、继续深聊、展开证据、确认或拒绝连接。"
    ),
    "保存这个动作,从\"点 1 下\"变成\"停 5 秒补一句话\"—— 把保存从被动收藏升级为主动留痕。": (
        "保存这个动作不能成为负担。正确策略是“保存先成功,理由可选但高价值”:写一句会显著提高未来找回质量;写不出来也可以先保存,状态标为待补理由。"
    ),
    "单点保存最终长成完整图谱,AI 帮你看到自己都没意识到的暗线关联。": (
        "单点保存最终形成可验证的证据网络。AI 可以在对话中自然指出一条暗线,但必须允许用户展开依据并确认、削弱或拒绝这条连接。"
    ),
    "这是 SnapGraph 长期价值的核心 —— 短期看像\"找回工具\",长期看是\"自己的本地认知地图\"。": (
        "这是 SnapGraph 长期价值的核心:短期是找回工具,长期是用户可追溯、可复核、可继续讨论的个人证据系统。"
    ),
    "图谱不是 AI 的世界,是你的世界。": "图谱不是主界面,是证据链背后的推理底座。",
    "当前初赛 demo 使用 Qwen API 验证完整链路。系统保留 Provider 抽象层(5 个调用点已模块化),后续可一键切换至蓝心大模型 + vivo 端侧能力。": (
        "当前初赛 demo 使用 Qwen API 验证完整链路。系统保留 Provider 抽象层,后续可对接蓝心大模型与 vivo 端侧能力,但切换不是“一键完成”的口号,需要按模型能力、隐私边界、端侧资源和调用协议逐项适配。"
    ),
    "我们在 312 份内部材料样本(团队成员真实保存的论文 / 笔记 / 截图)上进行了端到端测试:": (
        "我们在内部样本和真实 Qwen 接入中做了端到端测试。以下数据应被理解为 demo 阶段验证,不能包装成生产级性能承诺:"
    ),
    "我们不是在想「未来怎么上 vivo」── 我们是已经在第一步,正走向第三步。": (
        "我们先把 Web demo 的产品价值和证据链做扎实,再把它演进到 vivo 端侧入口。"
    ),
    "SnapGraph 不是一个\"等到决赛再考虑 vivo 端侧\"的项目。从初赛起,我们的代码就在 vivo X100 / iQOO Neo9 真机上跑,屏幕比例 393×852 真机适配,系统底层调用都已经按 Origin OS 的能力规划好了。": (
        "SnapGraph 从初赛起就按移动端使用场景设计,当前代码形态是 Web demo + 移动端比例适配 + Qwen provider 接入。真正的 vivo 原生端、蓝心能力与 Origin OS 入口是下一阶段落地路线,不能在当前文档中表述为已完成。"
    ),
    "Stage 01  ·  原生 APP   Stage 01 · Native App  ·  已跑通": (
        "Stage 01  ·  Web Demo   Stage 01 · Web prototype · 已跑通"
    ),
    "每一阶段都是上一阶段的自然延展,不是重写。从原生 APP 到智能体到快应用,我们的核心逻辑(思考回执 + 三种回答 + 置信审计)保持不变,变的只是入口和载体。": (
        "每一阶段都复用同一套核心逻辑:raw source 保存、user-stated 与 AI-inferred 分层、证据链、拒答边界与 Provider 抽象。变化的是入口、权限、延迟和隐私策略。"
    ),
    "我们不是在 PPT 里设想这件事 ── 它已经在你的手机上能跑。": (
        "我们不是只在 PPT 里设想这件事 —— 当前 Web demo 已经跑通核心链路,但离日常生产级使用仍有明确工程差距。"
    ),
    "完成度立场": "完成度立场 · 诚实边界",
    "上文已展示数据,这里再次列出便于评分对照:": (
        "上文已展示数据,这里再次列出便于评分对照。所有性能数字必须区分 Mock / 本地索引与真实 Qwen 调用:"
    ),
    "每一次思考回执,都是一份\"我曾经在乎过这件事\"的证据。每一次召回原话,都是\"过去的你\"对\"现在的你\"说话。每一次诚实拒答,都是 AI 在让出位置给人。": (
        "每一段用户原话,都是一份“我曾经在乎过这件事”的证据。每一次召回原话,都是过去的判断重新回到现在。每一次诚实拒答,都是 AI 在让出位置给证据和用户。"
    ),
}


SUBSTRING_REPLACEMENTS = {
    "深夜书房 · 索引卡": "冷静证据工作台",
    "Visual System · 1960s editorial typography": "Visual System · modern evidence workbench",
    "它已经在手机上能跑": "Web demo 已跑通,边界清楚",
    "running on real phones": "running web demo with clear limits",
    "移动端原生 APP · 智能体 · 快应用 / 插件": "Web 原型 · 移动端比例适配 · 后续智能体 / 快应用 / 插件",
    "团队名称 XXXXX · 指导老师 XXX 教授": "团队名称（待填写）· 指导老师（待填写）",
    "真机已跑通": "Web demo 已跑通,原生真机待验证",
    "vivo X100 / iQOO Neo9 真机已跑通": "按 vivo X100 / iQOO Neo9 比例验证,原生真机待跑通",
    "离线可用 · 数据不出手机": "本地优先保存;真实模型调用需明确隐私边界",
    "本地存储不依赖云端 · 数据不出手机": "本地优先保存 raw source 与索引;Qwen 调用需明确排除私密材料",
    "冷启动 1.8s · 找回响应 <600ms · 全链路保存→找回成功率 96%": "冷启动与本地检索可继续优化;真实 Qwen 回答当前约 15-25s,需异步/流式体验",
    "平均找回响应 | <600ms": "真实 Qwen 回答 | 当前约 15-25s",
    "<600ms": "Mock/本地检索可亚秒;Qwen 当前约 15-25s",
    "96%": "演示集核心链路可跑通",
    "78%": "需扩大样本验证",
    "24%": "方向已验证,需更多样本",
    "11%": "需阈值校准",
    "100%": "规则上强制区分",
    "99%": "当前足以展示核心价值,但不是生产完成度",
    "AI 替你保存\"为什么\"": "AI 可以总结材料,但不能替用户写“为什么”",
    "强制问\"为什么要保存\"": "温和询问“为什么要保存”,允许留空",
    "停 5 秒,补一句话": "可选补一句话",
    "停 5 秒补一句话": "可选补一句话",
    "图谱时 | 用于审计与导航": "证据链 | 用于审计与导航",
    "图谱不是 AI 的世界,是你的世界。": "图谱不是主界面,是证据链背后的推理底座。",
    "图谱入口": "证据链入口",
    "关联图谱入口": "证据链入口",
    "每日推送\"过去的你说过的话\"": "在用户请求或合适场景下召回“过去的你说过的话”",
    "已对接 2 所高校,准备小范围 beta 测试": "高校内测计划待确认,不得写成已对接事实",
    "当前版本已经可以作为正式提交": "当前版本可以支撑 demo 展示,提交材料需标注边界",
    "初赛 demo 已完成 · 团队成员日常使用中": "初赛 Web demo 可展示 · 正在内部测试与性能修正",
    "复赛接蓝心 · 一键切换 · 5 个调用点已模块化": "复赛接蓝心 · Provider 层适配 · 调用点已模块化",
    "原生 APP → 智能体 → 快应用": "Web Demo → 智能体 → 快应用 / 插件",
    "完成度足以进入复赛 demo": "复赛 demo 可行性",
    "6 屏关键界面 + 7 节点交互流程图 + 真机截图": "6 屏关键界面 + 证据优先交互流程 + Web 截图/录屏",
    "vivo X100 / iQOO Neo9 真机演示 + GitHub 仓库可运行代码": "Web demo 演示 + GitHub 仓库可运行代码;原生真机演示待补",
    "7 节点河流闭环": "证据优先闭环",
    "7 节点交互流程图": "证据优先交互流程图",
    "6 屏真机展现": "6 屏 Web 原型展现",
    "真截图": "Web 截图",
    "Qwen → 蓝心": "Qwen 验证 → 蓝心适配",
}


TABLE_CELL_REPLACEMENTS = {
    "保存时\n让你停 5 秒。系统问\"为什么要保存它\",生成思考回执 —— 用户原话 + AI 摘要 + 关联问题 + 证据路径,一键四份留痕。": (
        "保存时\n先保存成功,再温和询问“为什么要保存它”。用户写下的理由标为 user-stated;写不出来也可以留空,系统只生成材料摘要、可能问题与待确认连接。"
    ),
    "暂 存\n保存动作不能是负担 —— 8 秒一句话,不要求格式整理。": (
        "暂 存\n保存动作不能是负担 —— 先保存原始材料,理由可选,不要求格式整理。"
    ),
    "留 痕\nAI 替你保存\"为什么\",而不是只保存\"是什么\"。": (
        "留 痕\n只有用户能写“为什么”。AI 负责摘要材料、标出来源、提出可复核连接。"
    ),
    "1. 收集时\n强制问\"为什么要保存\",先思考一次,而非无脑收藏。": (
        "1. 收集时\n温和询问“为什么要保存”,但允许留空。降低保存摩擦,不把 AI 猜测写成用户意图。"
    ),
    "2. 存储时\n用户原话优先于 AI 总结 —— 你的话比 AI 的猜更重要。": (
        "2. 存储时\n用户原话优先于 AI 总结。user-stated 与 AI-inferred 永远分层保存、分层展示。"
    ),
    "5. 图谱时\n用于审计与导航,而非炫技 —— 透明高于炫酷。": (
        "5. 证据链\n图谱不做主界面,只在用户要验证“为什么这么说”时展开。透明高于炫酷。"
    ),
    "6. 存放时\n本地保存,思考痕迹属于用户,不属于平台。": (
        "6. 存放时\n本地优先保存,真实模型调用透明可控。私密材料默认不进入外部模型请求。"
    ),
    "05\n原型设计 Prototype · 6 screens + 7-node river loop": (
        "06\n原型设计 Prototype · 6 screens + evidence-first loop"
    ),
    "底 部\n三 tab:对话 / 空间 / 保存。永远在视野,保存按钮永远可达。": (
        "底 部\n主入口保持轻:召回 / 深聊 / 保存。库、待补理由、证据链在需要时出现,不抢主屏。"
    ),
    "4\nAI 后台 · 解析 / 摘要 / 推断 / 关联\n+0.5s": (
        "4\nAI 后台 · 解析 / 摘要 / 候选关联 / 隐私检查\n后台异步"
    ),
    "5\n入图谱 · 节点写入 + 关联建立 + Provenance\n+1s": (
        "5\n写入证据库 · raw source + wiki + graph.json + provenance\n后台完成"
    ),
    "7\n三种回答 · 找到原话 / 反证提示 / 拒答(★ 关键节点)\n+0.6s": (
        "7\n三种回答 · 找到原话 / 反证提示 / 拒答(★ 关键节点)\n本地先返回,Qwen 解释随后补齐"
    ),
    "1\n内 容 理 解\n摘要资料 / 提取关键细节 / 识别主题": (
        "1\n内 容 理 解\n摘要资料 / 提取关键细节 / 识别主题 / 标注解析状态"
    ),
    "2\n判 断 留 痕\n保留用户原话 / 必要时生成低置信推断": (
        "2\n判 断 留 痕\n保留用户原话;没有用户理由时标为待补,不由 AI 填写"
    ),
    "初 赛\nQwen API · Provider 抽象就位 · 完整链路验证": (
        "初 赛\nQwen API · Provider 抽象就位 · Web demo 核心链路验证"
    ),
    "决 赛\nvivo 端侧能力接入 · 离线优先 · Origin OS 桌面卡片 · 浏览器分享面板一键保存": (
        "决 赛\nvivo 端侧能力接入 · 本地优先 · Origin OS 入口 · 浏览器/系统分享面板一键保存"
    ),
}


def set_paragraph_text(paragraph: Paragraph, text: str) -> None:
    """Replace paragraph text while preserving paragraph style."""
    for run in list(paragraph.runs):
        run._element.getparent().remove(run._element)
    if "\n" not in text:
        paragraph.add_run(text)
        return
    parts = text.split("\n")
    for idx, part in enumerate(parts):
        paragraph.add_run(part)
        if idx != len(parts) - 1:
            paragraph.add_run().add_break(WD_BREAK.LINE)


def insert_paragraph_after(paragraph: Paragraph, text: str = "", style: str | None = None) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    if style:
        try:
            new_para.style = style
        except KeyError:
            style_obj = None
            wanted_id = style.replace(" ", "")
            for candidate in new_para.part.styles:
                if candidate.name == style or candidate.style_id == wanted_id:
                    style_obj = candidate
                    break
            if style_obj is not None:
                new_para.style = style_obj
    if text:
        new_para.add_run(text)
    return new_para


def replace_text(text: str) -> str:
    if text in PARAGRAPH_REPLACEMENTS:
        return PARAGRAPH_REPLACEMENTS[text]
    if text in TABLE_CELL_REPLACEMENTS:
        return TABLE_CELL_REPLACEMENTS[text]
    new_text = text
    for old, new in SUBSTRING_REPLACEMENTS.items():
        new_text = new_text.replace(old, new)
    return new_text


def all_paragraphs(doc: Document):
    for paragraph in doc.paragraphs:
        yield paragraph
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    yield paragraph


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc = Document(SRC)

    inserted_boundary = False
    for paragraph in list(doc.paragraphs):
        if (
            not inserted_boundary
            and paragraph.text
            == "基于你自己保存过的内容回答,低幻觉、可追溯、可拒答。问什么都先问\"我之前说过什么\"—— 这是和通用 AI 助手最根本的不同:它不替你生成新答案,它把你过去的判断还给现在的你。"
        ):
            inserted_boundary = True

    for paragraph in all_paragraphs(doc):
        original = paragraph.text
        revised = replace_text(original)
        if revised != original:
            set_paragraph_text(paragraph, revised)

    # Add an early, explicit implementation boundary after the core innovation section.
    target = None
    for paragraph in doc.paragraphs:
        if paragraph.text.startswith("基于你自己保存过的内容回答,低幻觉、可追溯、可拒答。当前 Web demo"):
            target = paragraph
            break
    if target is not None:
        p4 = insert_paragraph_after(
            target,
            "不夸大:当前不是生产级原生 APP,不承诺完全离线,不把真实 Qwen 响应写成 <600ms。",
            "List Paragraph",
        )
        p3 = insert_paragraph_after(
            target,
            "正在补齐:真实批量导入速度、no-match 阈值、异步队列、原文定位、移动端原生入口、私密材料外部调用边界。",
            "List Paragraph",
        )
        p2 = insert_paragraph_after(
            target,
            "已完成:Vue + FastAPI Web demo、Qwen provider 接入、Markdown/TXT/HTML/PDF文本/图片识别验证、raw source 保存、wiki/graph/SQLite 工作区、用户原话与 AI 推断标签。",
            "List Paragraph",
        )
        p1 = insert_paragraph_after(target, "当前实现边界", "Heading 2")
        # Insertion after the same paragraph reverses order, so move them into the intended order.
        # The helper adds each new paragraph immediately after target; recreating in reverse keeps reading order correct.
        _ = (p1, p2, p3, p4)

    # Repair order of the inserted block if Word XML inserted it in reverse.
    # The block is short enough that repeated exact replacements are safer than a larger XML shuffle.
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                cell_text = "\n".join(p.text for p in cell.paragraphs)
                revised = replace_text(cell_text)
                if revised != cell_text and len(cell.paragraphs) == 1:
                    set_paragraph_text(cell.paragraphs[0], revised)

    # Rewrite metrics tables that would otherwise retain misleading numbers.
    for table in doc.tables:
        headers = [cell.text.strip() for cell in table.rows[0].cells] if table.rows else []
        if headers == ["指 标", "值", "说 明"]:
            rows = [
                ("指 标", "当前口径", "说明"),
                ("核心链路", "演示集可跑通", "保存 raw source、生成 wiki/graph、Qwen 回答、证据分层已验证。"),
                ("本地/Mock 性能", "亚秒级", "仅代表本地索引与 MockLLM,不能等同真实模型体验。"),
                ("真实 Qwen 回答", "约 15-25s", "已测真实 API;需要异步队列、流式反馈和阶段性结果。"),
                ("批量导入", "10 文件约 104.7s", "当前串行调用过慢,100 文件需要后台任务与并发限制。"),
                ("no-match", "高风险待修", "语料变大后可能检出无关来源,必须加入阈值和拒答策略。"),
                ("分层标签", "规则上强制", "user-stated / AI-inferred / no-evidence 必须在 UI 与数据层分开。"),
            ]
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    if i < len(table.rows) and j < len(table.rows[i].cells):
                        table.rows[i].cells[j].text = value
        elif headers == ["指 标", "数 值", "语 义"]:
            rows = [
                ("指 标", "当前状态", "语义"),
                ("核心保存→找回", "demo 可跑通", "足以展示价值,未证明生产稳定性。"),
                ("模糊召回", "需扩大样本验证", "当前能演示,还需真实用户样本。"),
                ("反证/过期判断", "方向验证中", "需要更强阈值与用户确认闭环。"),
                ("无证据拒答", "必须强化", "no-match 是最高优先级风险。"),
                ("真实响应", "Qwen 约 15-25s", "需要先本地证据、后模型解释的体验。"),
                ("分层标签", "规则上强制", "产品立场不破例。"),
            ]
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    if i < len(table.rows) and j < len(table.rows[i].cells):
                        table.rows[i].cells[j].text = value

    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
