# Synapse Platform — 시작 가이드

저장소를 클론한 뒤 로컬 개발 환경을 맞추는 절차입니다.

## 사전 요구사항

- [Git](https://git-scm.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python 3.12)



## 클론 후 설정

```bash
git clone <저장소 URL>

cd backend
uv sync
uv run pre-commit install
```
여기까지하면 커밋할때 자동으로 수정된 파일에 한해서 ruff 체크를 합니다. 
`uv sync`는 백엔드 의존성과 dev 도구(ruff, pre-commit)를 설치합니다.  
`pre-commit install`은 커밋 전에 ruff·eslint 훅을 Git에 등록합니다.

이 아래는 과거 ruff 체크 안된것들이 있어 한번 돌리고 수정하는 것에 대한 가이드를 하기위해 작성한 명령어 입니다.
## 전체 파일 검사 하는 명령어
```bash
uv run pre-commit run --all-files
```
## Ruff 체크
```bash
cd backend && uv run ruff check .
```

--------------------------------------------------------------------------------------------------------------------------------------------------

개발시 어떻게 시작해서 보면 되는지에 대한 명령어 가이드 입니다. 이건 aI 물어보시고 키는방법 물어보셔도 아마 동일할거라 물어보고 하셔도 될 거예요.
## 개발할 때

```bash
# env (최초 1회)
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 터미널 1 — DB + 백엔드 (:8000)
docker compose -f docker-compose.dev.yml up --build

# 터미널 2 — 프론트 (:5173)     -->   저희 무조건 pnpm 만 사용할 겁니다.(npm 사용 안합니다.)
cd frontend
pnpm install
pnpm dev
```

- 화면: http://localhost:5173
- API: http://localhost:8000
- `frontend/.env`의 `VITE_API_BASE_URL`은 `http://localhost:8000` (`.env.example` 참고)

--------------------------------------------------------------------------------------------------------------------------------------------------


## 다음 단계

- 상세 문서: [docs/README.md](./README.md)
- 백엔드: [docs/backend/OVERVIEW.md](./backend/OVERVIEW.md)
- 프론트엔드: [docs/frontend/OVERVIEW.md](./frontend/OVERVIEW.md)

