"""서브에이전트 공통 배관 — LangGraph RunnableConfig에 store(Port)를 주입/추출한다.

각 서브에이전트의 store.py가 자기 키로 이 헬퍼를 재사용한다.
(노드가 DB를 직접 모르고 service가 주입하는 Port 패턴의 공통 부분)
"""

from __future__ import annotations

from langchain_core.runnables import RunnableConfig


def build_run_config(key: str, store: object | None) -> RunnableConfig:
    """store를 config["configurable"][key]에 담아 그래프 실행 설정을 만든다."""
    return {"configurable": {key: store}}


def get_store(key: str, config: RunnableConfig | None) -> object | None:
    """config["configurable"][key]에서 주입된 store를 꺼낸다 (없으면 None)."""
    if not config:
        return None
    return config.get("configurable", {}).get(key)
