"""LangChain + Agent Skills 通用 Demo（支持动态加载多 Skills）。"""

from __future__ import annotations

import argparse
import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

SKILLS_ROOT = Path("skills/user")


@dataclass
class LoadedSkill:
    name: str
    definition: str
    tools: List[BaseTool]


def _load_module(module_path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块：{module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_skills(skills_root: Path = SKILLS_ROOT) -> List[LoadedSkill]:
    if not skills_root.exists():
        raise FileNotFoundError(f"Skills 根目录不存在：{skills_root}")

    loaded: List[LoadedSkill] = []
    for skill_dir in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        skill_md = skill_dir / "SKILL.md"
        tools_py = skill_dir / "tools.py"

        if not skill_md.exists() or not tools_py.exists():
            continue

        definition = skill_md.read_text(encoding="utf-8")
        tools_module = _load_module(tools_py, f"{skill_dir.name}_tools")

        if not hasattr(tools_module, "build_tools"):
            raise AttributeError(f"{tools_py} 缺少 build_tools() 函数")

        tools = tools_module.build_tools()
        loaded.append(LoadedSkill(name=skill_dir.name, definition=definition, tools=tools))

    if not loaded:
        raise RuntimeError("未发现可用 Skill。请至少提供包含 SKILL.md 与 tools.py 的技能目录。")

    return loaded


def build_agent() -> AgentExecutor:
    skills = discover_skills()

    all_tools: List[BaseTool] = []
    definitions: List[str] = []
    for skill in skills:
        all_tools.extend(skill.tools)
        definitions.append(f"## Skill: {skill.name}\n{skill.definition}")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个通用 AI 助手。你可以使用动态加载的 Skills 来完成不同领域任务。\n"
                "请先判断用户目标，再选择最相关的技能与工具；在需要外部数据或可执行能力时优先调用工具。\n"
                "严格遵循对应 Skill 中定义的工作流、边界与失败处理策略。\n\n"
                "以下是当前动态加载的 Skills 规范：\n\n"
                + "\n\n".join(definitions),
            ),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )

    llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    agent = create_openai_tools_agent(llm=llm, tools=all_tools, prompt=prompt)
    return AgentExecutor(agent=agent, tools=all_tools, verbose=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Skills 通用 Demo（动态 Skills）")
    parser.add_argument("query", nargs="?", default="请基于可用技能帮我完成一个示例任务")
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("请先设置 OPENAI_API_KEY 环境变量。")

    result = build_agent().invoke({"input": args.query})
    print("\n=== Final Answer ===")
    print(result["output"])


if __name__ == "__main__":
    main()
