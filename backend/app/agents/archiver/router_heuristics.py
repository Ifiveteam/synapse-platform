"""Router heuristic — LLM 분류 전 명확한 경로를 규칙으로 선판별."""

from __future__ import annotations

import re

from app.agents.archiver.types import ArchiverRoute

_EXPLICIT_SEARCH = re.compile(
    r"(?:"
    r"\bsearch\b|"
    r"검색(?:해|해서|으로|을)?|"
    r"구글(?:링| 검색|에서)?|"
    r"웹\s*검색|"
    r"인터넷\s*(?:에서\s*)?검색|"
    r"search(?:를|로)\s*(?:사용|써|써서)"
    r")",
    re.IGNORECASE,
)

_EXTERNAL_FACT = re.compile(
    r"(?:"
    r"(?:오늘|내일|모레)(?:\s+\S+){0,3}\s*날씨|"
    r"날씨\s*(?:알려|어때|어떤|몇)|"
    r"(?:현재|오늘|지금)\s*환율|"
    r"최신\s*(?:뉴스|트렌드|버전|정보|소식)|"
    r"(?:지금|현재|요즘)\s*(?:몇\s*도|주가|시세)"
    r")",
    re.IGNORECASE,
)

_PAGE_SCOPED = re.compile(
    r"(?:"
    r"이\s*(?:페이지|글|문서|탭|사이트|화면)|"
    r"현재\s*(?:페이지|글|탭|화면)|"
    r"여기\s*(?:적힌|나온|쓰인)"
    r")",
    re.IGNORECASE,
)

_RAG_HINT = re.compile(
    r"(?:"
    r"예전에|전에\s*(?:저장|스크랩)|"
    r"내\s*(?:보관함|기록|히스토리|아카이브)|"
    r"과거\s*(?:기록|대화|스크랩)"
    r")",
    re.IGNORECASE,
)

_GREETING_ONLY = re.compile(
    r"^(?:"
    r"안녕(?:하세요)?|"
    r"고마워(?:요)?|"
    r"감사(?:합니다|해)?|"
    r"ㅎㅎ|ㅋㅋ|"
    r"심심해"
    r")[!?.~\s]*$",
    re.IGNORECASE,
)


def detect_route_heuristic(message: str) -> ArchiverRoute | None:
    """규칙만으로 확실한 경우 route를 반환한다. 애매하면 None."""
    text = message.strip()
    if not text:
        return ArchiverRoute.GENERAL

    if _GREETING_ONLY.match(text):
        return ArchiverRoute.GENERAL

    if _EXPLICIT_SEARCH.search(text):
        return ArchiverRoute.SEARCH

    if _RAG_HINT.search(text):
        return ArchiverRoute.RAG

    page_scoped = bool(_PAGE_SCOPED.search(text))
    if not page_scoped and _EXTERNAL_FACT.search(text):
        return ArchiverRoute.SEARCH

    return None
