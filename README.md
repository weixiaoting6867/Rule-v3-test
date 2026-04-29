# Rule-v3-test
This repo is a sample of extraction relations of 500 README
第一部分：抽取逻辑与步骤解析
当前代码的知识抽取引擎工作流主要包含以下 六大核心步骤：
1. 文档切分与预处理 (Parsing & Preprocessing)
   结构化切块：将 README 文本切分为 YAML 头部信息（Frontmatter）和 Markdown 主体段落，主体段落按照 Markdown 标题级数（# 至 ######）切分为多个独立的 Section。
   噪音清除：在进入主体匹配前，强制全局清除类似于 [...](https://github.com/...) 以及裸露的 Github 链接 URL，防止将 GitHub 仓库误认为 Hugging Face 仓库。
2. YAML 元数据抽取 (YAML Frontmatter Extraction)
   Task (任务)：利用正则直接捕获 pipeline_tag 或 pipeline，并在本地维护的 54 种标准任务字典中进行全小写的模糊包含匹配，匹配成功则直接建立 applied_for 关系。
   Base Model (基础模型)：匹配 base_model 字段下的合法 HF ID，建立 derived from 关系（若带有 datasets/ 前缀则强制转为 trained on 数据集关系）。
   Dataset (数据集)：匹配 datasets 字段下的合法 HF ID，建立 trained on 关系。
3. 实体深度清洗与拦截 (Entity Validation Engine)
   对于正则 [HF_ID] 提取到的每一个候选实体，执行严格的离线校验：
     标点裁剪：剥离尾部多余的 . , ; : ! ? ' " 标点。硬核拦截：直接拦截候选词 "SFT/DPO"。
     格式断言：必须由前后两部分组成（包含 / 且两边字符数均 $\ge 2$）。
     上下文环境拦截：如果候选词后缀紧跟图像/视频/文档扩展名（如 .png, .mp4, .md），或者前缀紧挨着外部域名（如 github.com, wandb.ai, gitee.com），直接抛弃该实体。
4. 细粒度模型/数据关系抽取 (M2M & M2D Extraction)
   对于过滤后的合法实体，以其位置为基准：
     后置校验 (Suffix)：如果实体后方 30 个字符内紧跟单词 dataset 或 datasets，或者满足 on the [HF_ID] dataset 的句式，直接赋予 trained on 关系。
     前置寻优 (Prefix)：截取实体前方 150 个字符作为窗口，逆向寻找字典中配置的 Trigger 触发词。如果有多个触发词，取位置距离实体最近的那一个作为最终匹配关系。
5. 离线增强版论文抽取 (M2P Extraction)
   正则捕获：提取所有 ArXiv 编号和 DOI 编号并去重。
   环保规避：若当前 Section 标题含有 "environmental impact"，则整段抛弃，不提取任何论文。
   Title/Cite 强规则：若 Section 标题满足单词边界正则 \b(cite|citations?|bibtex)\b，且该段落内只提及了一篇唯一的论文，则该论文建立最高优先级的 Official Technical Paper。
   兜底策略：所有未能满足上述条件的论文实体，一律作为 Base Architecture。
6. 全局去重与细粒度模型关系覆写 (Deduplication & Relation Override)
   优先级去重：对于同一个 Target，按照 priority_map（finetuned/quantized/adapter/trained/Official 均为 100 分 > Base Architecture 为 50 分 > derived from 10 分）保留最高分关系。
   全局同化拦截 (Global M2M Override)：在最终清洗阶段，如果整个 README 中提取到了任何一条“高价值细粒度模型关系”（如 quantized from, adapter for, merged from, finetuned from），系统将强制把当前 Repo 所有的模型衍生关系全部覆写统一为该最高优先级关系。
