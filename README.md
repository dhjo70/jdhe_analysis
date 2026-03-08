# JDHE Analysis Pipeline

JDHE Analysis Pipeline은 [Google Gemini API](https://ai.google.dev/) (신규 `google-genai` SDK)를 활용하여 대량의 학술 논문(PDF)을 분석하고, 사전에 정의된 형태의 마크다운(Markdown) 리포트를 자동으로 추출하는 파이썬 기반 데이터 파이프라인입니다. Google Drive와 완벽히 연동되어 원격지 볼륨(Volume)별로 자동 다운로드와 추론 및 검증(Validation) 로직을 일괄 수행할 수 있습니다.

---

## 🚀 주요 기능

- **자동 PDF 텍스트 추출**: `PyMuPDF`를 사용하여 대상 PDF에서 분석을 위한 원문 텍스트를 안정적으로 파싱합니다.
- **LLM 기반 자동 분석 (Gemini API 템플릿화)**: 논문의 *연구 주제, 연구 참여자, 이론적 틀, 연구 방법론, 데이터 수집 방법, 데이터 분석 방법, 키워드, 게재 연도*를 일관성 있는 마크다운 양식으로 자동 요약합니다.
- **포맷팅 자가 검증 (Validation Loop)**: Gemini가 생성한 결과물이 정확한 8개 항목의 મા크다운 헤더 형식을 준수하고 사족(Conversational fillers)이 없는지 내부적으로 한 번 더 LLM을 통해 검사하고, 실패 시 자동 재작성(Auto-Retry)을 요청합니다.
- **Google Drive Batch 동기화 지원**: `OAuth 2.0` 기반으로 구글 드라이브 지정 폴더(Volume/Issue)를 스캔하고, 로컬로 없는 파일만 스마트하게 미러링 다운로드하여 분석합니다.
- **실행 재개 (Resume Checkpoint)**: 분석 중 중단(Rate Limit 또는 프로세스 종료)되더라도 이미 결과(`results/*.md`)에 작성된 논문은 식별하여 스킵(Skip)하는 이어하기 기능을 내장했습니다.
- **랜덤 샘플링 테스트**: 전체 스캔에 앞서 파이프라인 건전성과 프롬프트 동작 상태를 가볍게 확인하도록 "무작위 단일 Issue 1건 추출 런" 메뉴를 지원합니다.

---

## 🛠️ 프로젝트 구조

```text
jdhe_analysis/
├── main.py                     # 파이프라인 메인 실행기 (CLI 인터페이스 제공)
├── src/
│   ├── config.py               # API 설정, Prompt 템플릿, 검증 로직 규칙 정의
│   ├── drive_client.py         # Google Drive API 인증 및 폴더 트리/파일 동기화
│   ├── llm_client.py           # Gemini 모델 통신 객체 및 재시도(Retry) 검증 루프 구현
│   ├── pdf_utils.py            # PyMuPDF 텍스트 추출기 및 파일/메타데이터 제목 유추
│   ├── pipeline.py             # 오케스트레이션 로직, 이어하기, 결과 출력(md) 연결
│   └── tracker.py              # 분석 건수 세기, 누적 토큰(Token) 사용량 계산, 비용 추산
├── pyproject.toml              # UV 기반 프로젝트 디펜던시 명세
└── .env                        # [중요] API 키 및 Drive 대상 아이디 (Git 제외 대상)
```

---

## ⚙️ 사전 요구사항 & 설치 방법

본 프로젝트는 고속 패키지 매니저인 [`uv`](https://github.com/astral-sh/uv)를 통해 의존성을 관리하고 실행됩니다.

1. **저장소 클론하기**
   ```bash
   git clone https://github.com/dhjo70/jdhe_analysis.git
   cd jdhe_analysis
   ```

2. **환경변수 세팅하기 (`.env`)**
   프로젝트 루트 디렉토리에 `.env` 파일을 만들고 아래 코드를 채워주세요.
   ```env
   # API 키 입력 필수
   GEMINI_API_KEY="AIzaSy...당신의_제미나이_키를_입력하세요"
   
   # [선택] 구글 드라이브 타겟 최상위 폴더 ID (작성 안할시 기본 ID 이용)
   DRIVE_ROOT_FOLDER_ID="YOUR_DRIVE_FOLDER_ID_HERE"
   ```

3. **구글 드라이브 OAuthentication 자격증명 투입하기**
   구글 GCP에서 OAuth 클라이언트용 `credentials.json` 파일을 발급받아 프로젝트 루트 디렉토리에 넣어주세요. 최초 실행 시 브라우저가 열리며 권한 취득 후 `token.json`이 자동 생성됩니다.

4. **패키지 동기화 및 실행 준비**
   ```bash
   # uv가 .python-version 과 pyproject.toml을 읽어 가상환경 및 의존성을 자동 구성합니다.
   uv sync
   ```

---

## 📖 사용 방법

1. 터미널 명령어를 입력하여 파이프라인을 기동시킵니다.
   ```bash
   uv run python main.py
   ```

2. 콘솔에 출력된 **메인 메뉴**에서 번호를 선택하여 진행합니다.
   - **1번 메뉴**: 연결된 드라이브의 방대한 Volume 중 무작위 1개 Issue만 쏙 빼와서 단일 점검 테스트를 쾌속으로 돌립니다.
   - **2번 메뉴**: 모든 Volume의 순차 Batch 다운로드 및 분석을 진행합니다. 1개 Volume 작업이 끝날 때마다 비용과 상황을 보고받은 후, 사용자의 Enter 입력을 기다리는 휴식시간(Checkpoint)을 갖습니다.
   - **3번 메뉴**: 즉시 프로그램을 종료합니다.

---

## 🔒 보안 및 기여 (Security Notes)

> **주의:**
> `.env` (API Keys), `credentials.json` (Google OAuth Client ID Secret), `token.json` (Refreshed Client Tokens) 및 실 데이터베이스격인 `papers/`, `results/` 폴더는 모두 `.gitignore`에 등록되어 깃허브 원격 저장소에 업로드되지 않도록 블로킹 상태입니다.
> 퍼블릭 저장소 포크 시 절대 본인만의 키나 토큰 정보를 하드코딩해서 커밋(Commit)하지 않도록 유의해 주세요.
