from langchain_core.runnables import RunnableConfig

from agent.factory import build_agent

# 单人游戏 graph：langgraph.json 注册为 single_player
MODE = "single_player"


async def graph(config: RunnableConfig):
    return await build_agent(MODE, config)
