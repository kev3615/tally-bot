# Tally Bot AI Core Service

## 개요 🌟

이 프로젝트는 대화 내용에서 금액과 통화 정보를 추출하고 원화로 변환하는 FastAPI 기반 AI 엔진 서비스입니다. 

## 설치 및 실행 방법 🚀

### 환경 설정

1. Python 3.8 이상이 필요합니다.
2. 가상 환경 생성 및 활성화:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   .venv\Scripts\activate     # Windows
   ```

3. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```

4. 환경 변수 설정:
   ```
   OPENAI_API_KEY=sk-your-api-key
   LANGSMITH_API_KEY=ls-your-api-key
   ```

### 서버 실행

```bash
# 개발 모드
uvicorn main:app --reload
nohup uvicorn main:app --host 0.0.0.0 --port 8000 &

# 프로덕션 모드
# PowerShell 방식 (한 줄씩 실행)
$env:APP_ENV = "production"
uvicorn main:app --host 0.0.0.0 --port 8000

```

### 로그 확인

```bash
tail -f nohup.out
```

## API 엔드포인트 📡

```bash
http://tally-bot-ai-backend-alb-2092930451.ap-northeast-2.elb.amazonaws.com/api/process
```

#### 1. 기본 상태 확인
- **GET /** - 서비스 상태 확인

#### 2. 대화 내용 처리
- **POST /api/process** - JSON 형식의 대화 내용을 직접 전송하여 처리
- **POST /api/process-file** - 파일에서 대화 내용을 로드하여 처리

## 프로젝트 구조 🏗️

```text
ai-core-service/
├── config/                    # 애플리케이션 설정 파일
│   ├── app_config.py         # FastAPI 앱 설정
│   └── service_config.py     # AI 서비스 환경 설정
├── handlers/                  # API 요청 처리 핸들러
│   └── process_handler.py    # 대화 처리 로직 핸들러
├── load/                     # 프롬프트 및 대화 로딩 모듈
├── models/                   # 데이터 모델 정의
│   └── conversation.py       # 대화 요청/응답 모델
├── resources/                # 프롬프트 및 샘플 대화 파일
├── services/                 # 핵심 비즈니스 로직 서비스
│   ├── ai_service.py         # AI 모델 호출 서비스
│   ├── chain_ai_service.py   # 체인 기반 AI 서비스
│   └── result_processor.py   # 결과 처리 서비스 
├── utils/                    # 유틸리티 모듈
│   ├── advanced_metrics.py   # 고급 평가 지표 유틸리티
│   ├── calculation_helper.py # 계산 로직 유틸리티
│   ├── currency_converter.py # 통화 변환 유틸리티
│   ├── json_filter.py        # JSON 필터링 유틸리티
│   ├── logging_utils.py      # 로깅 유틸리티
│   ├── message_merger.py     # 메시지 병합 유틸리티
│   └── settlement_evaluator.py # 정산 평가 유틸리티
├── main.py                   # FastAPI 서버 메인 파일
├── requirements.txt          # 의존성 목록
└── README.md                 # 프로젝트 설명
```

## 사용 예시 💡

### 1. 기본 대화 처리

```python
import requests

# 대화 처리 요청
response = requests.post("http://tally-bot-ai-backend-alb-2092930451.ap-northeast-2.elb.amazonaws.com/api/process", json={
    "chatroom_name": "여행 정산방",
    "members": [{"0":"지훈", "1":"준호", "2":"소연"}],
    "messages": [
        {"speaker": "준호", "message_content": "택시비 19유로 냈어요."}
    ]
})

result = response.json()
print(result)
```

### 프로덕션 서버
```bash
http://tally-bot-ai-backend-alb-2092930451.ap-northeast-2.elb.amazonaws.com
```

서버는 기본적으로 http://localhost:8000 에서 실행됩니다.

## API 문서

FastAPI는 자동으로 API 문서를 생성합니다:

### 개발 환경 (로컬)
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 의존성 📦

주요 의존성:
- `fastapi==0.115.12` - 웹 프레임워크
- `uvicorn==0.34.2` - ASGI 서버
- `langchain==0.3.25` - LLM 체인 구성
- `langchain-core==0.3.59` - LangChain 핵심 모듈
- `langchain-openai==0.3.16` - OpenAI LangChain 통합
- `langchain-text-splitters==0.3.8` - 텍스트 분할 유틸리티
- `openai==1.79.0` - OpenAI API 클라이언트
- `pydantic==2.11.4` - 데이터 검증 라이브러리
- `pydantic_core==2.33.2` - Pydantic 핵심 모듈
- `boto3==1.38.23` - AWS SDK
- `aiofiles==24.1.0` - 비동기 파일 처리
- `pytest==8.0.0` - 테스트 프레임워크
- `pytest-asyncio==0.24.0` - 비동기 테스트 지원