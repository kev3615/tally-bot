# 알려진 이슈 및 주의사항

## 외화 처리 흐름

LLM 프롬프트는 외화를 원화로 변환하지 말라고 지시 → LLM이 `amount: 23, currency: "EUR"` 형태로 출력.  
이후 `utils/currency_converter.py`에서 하드코딩된 환율로 KRW 변환:

```python
EXCHANGE_RATES = {
    "EUR": 1400, "USD": 1300, "JPY": 9, "CNY": 180, "GBP": 1650
}
```

변환 후 `currency` 필드 제거. 지원하지 않는 통화는 변환 없이 그대로 유지.

---

## 금액 방향 오류 (gpt-3.5-turbo에서 빈번)

`"허원혁 25000 보내라"` (speaker: "2") → 화살표 방향 오류 발생 가능.  
올바른 해석: `허원혁 → speaker(2)` / 잘못된 해석: `speaker(2) → 허원혁`

---

## 중복 요청 방지 비활성화

`main.py`의 `generate_request_hash()`에 `time.time()` + 랜덤값 포함 → 매번 다른 해시 생성.  
실운영 배포 시 이 부분을 제거하여 실제 중복 방지 활성화 필요.

---

## 긴 대화 청킹

`CHUNKING_THRESHOLD = 15` (사용자 메시지 기준). 초과 시 10개씩 청크 분리 후 병렬 처리.  
청킹 로직: `handlers/process_handler.py`의 `process_conversation_with_simplified_chain()`.

---

## 프롬프트 파일 보안

`load/prompt_loader.py`가 path traversal 공격 방어 + 화이트리스트 검증.  
새 프롬프트 파일 추가 시 반드시 `_ALLOWED_PROMPT_FILES`에 등록 필요.
