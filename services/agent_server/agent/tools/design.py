from langchain_core.tools import tool
from pydantic import BaseModel, Field


class GameDesignArgs(BaseModel):
    title: str = Field(min_length=1, max_length=50, description="游戏标题")
    gameplay: str = Field(min_length=10, description="核心玩法说明")
    controls: str = Field(min_length=5, description="操作方式说明")
    win_lose: str = Field(min_length=5, description="胜负条件说明")
    difficulty: str = Field(min_length=2, description="难度设计说明")


@tool(args_schema=GameDesignArgs)
def submit_game_design(
    title: str, gameplay: str, controls: str, win_lose: str, difficulty: str
) -> str:
    return (
        "设计方案已获批，立即按以下方案生成 /workspace/work/index.html，不要再询问。\n"
        f"标题：{title}\n玩法：{gameplay}\n操作：{controls}\n"
        f"胜负：{win_lose}\n难度：{difficulty}"
    )
