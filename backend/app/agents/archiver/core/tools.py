"""Archiver Gemini Tool 정의 SSOT."""

from __future__ import annotations

from google.genai import types

GOOGLE_SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())

SCRAP_CURRENT_PAGE_TOOL_NAME = "scrap_current_page"

SCRAP_CURRENT_PAGE_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name=SCRAP_CURRENT_PAGE_TOOL_NAME,
            description=(
                "유저가 현재 웹페이지를 저장, 보관, 스크랩하거나 나중에 보겠다고 요청할 때 호출합니다. "
                "현재 열려 있는 브라우저 탭의 페이지를 스크랩 저장소에 등록합니다. "
                "유저가 'XX 카테고리에 저장해줘', '쇼핑 리스트에 킵해줘'처럼 특정 카테고리를 명시했다면 "
                "해당 카테고리 이름(예: '레시피 카테고리' → '레시피')을 user_specified_category 인자에 넣으세요."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "user_specified_category": types.Schema(
                        type=types.Type.STRING,
                        description=(
                            "유저가 명시한 스크랩 보관 카테고리. "
                            "예: '레시피 카테고리에 저장' → '레시피'. "
                            "카테고리를 지정하지 않았으면 생략합니다."
                        ),
                    ),
                },
            ),
        )
    ]
)
