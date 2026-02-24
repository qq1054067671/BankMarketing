# LangChain Agent Skills 通用 Demo（可动态扩展 Skills）

本示例实现了可扩展的技能目录约定：

```text
skills/user/<skill-name>/
├── SKILL.md       # 技能定义（领域知识 + 工作流）
├── tools.py       # 给模型调用的 @tool 能力
```

当前示例内置技能（你可以新增更多业务技能）：

```text
skills/user/web-research/
├── SKILL.md
└── tools.py
```

## 动态加载规则

`code/agent_skills_weather_demo.py` 会扫描 `skills/user/*`，自动加载满足以下条件的技能目录：

1. 必须存在 `SKILL.md`
2. 必须存在 `tools.py`
3. `tools.py` 必须实现 `build_tools()`，并返回 `@tool` 对象列表

因此新增技能时，只需新增一个新目录并遵守上述约定，无需改主程序。

## 安装依赖

```bash
pip install langchain langchain-openai requests
```

## 环境变量

```bash
export OPENAI_API_KEY="你的Key"
# 可选
export OPENAI_MODEL="gpt-4o-mini"
```

## 运行

```bash
python code/agent_skills_weather_demo.py "请用当前技能帮我完成一个任务"
```


## 提示词策略

主程序会把所有已发现 Skill 的 `SKILL.md` 内容动态拼接进 system prompt，
让 Agent 在运行时按技能定义选择工具和执行流程，因此不再绑定单一“天气场景”。
