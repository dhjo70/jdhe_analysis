import time
import json
from google import genai
from google.genai import types
from google.genai.errors import APIError

from src.config import (
    GEMINI_API_KEY, MODEL_NAME, 
    MAX_RETRIES, RETRY_DELAY_SECONDS, 
    ANALYSIS_PROMPT_TEMPLATE, VALIDATION_PROMPT
)

# Initialize the Gemini GenAI client
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다. .env 파일에 추가해주세요.")
    
client = genai.Client(api_key=GEMINI_API_KEY)


def validate_analysis_result(analysis_text: str):
    """
    Gemini API를 호출하여 생성된 분석 결과(analysis_text)가 사전에 정의된 9가지 검증 기준을 완벽하게 통과하는지 평가합니다.
    결과는 JSON 포맷으로 강제 반환되며, 통과 여부(is_valid)와 실패 시 그 사유(reason)를 함께 반환합니다.
    (반환값: is_valid, reason, val_in_tokens, val_out_tokens)
    """
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Gemini API로 결과 검증 중... (시도 {attempt+1}/{MAX_RETRIES})")
            validation_response = client.models.generate_content(
                model=MODEL_NAME,
                contents=VALIDATION_PROMPT.format(analysis_text=analysis_text),
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            # 토큰 사용량 가져오기
            try:
                val_prompt_tokens = validation_response.usage_metadata.prompt_token_count
                val_candidate_tokens = validation_response.usage_metadata.candidates_token_count
            except Exception:
                val_prompt_tokens = 0
                val_candidate_tokens = 0
                
            try:
                result = json.loads(validation_response.text)
            except json.JSONDecodeError:
                result = {"is_valid": False, "reason": "검증 결과를 파싱할 수 없습니다."}
                
            return result.get("is_valid", False), result.get("reason", "알 수 없는 오류"), val_prompt_tokens, val_candidate_tokens
            
        except APIError as e:
            if e.code == 429:
                print(f"API 할당량 초과(429) (검증 중). {RETRY_DELAY_SECONDS}초 대기 후 재시도합니다... 에러메시지: {e}")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print(f"API 오류 발생 (검증 중): {e}")
                time.sleep(RETRY_DELAY_SECONDS)
        except Exception as e:
            print(f"예상치 못한 검증 오류 발생: {e}")
            return False, str(e), 0, 0
            
    return False, "검증 실패: 최대 재시도 횟수 초과", 0, 0


def analyze_paper_with_retry(paper_text: str):
    """
    주어진 논문 전체 텍스트를 Gemini API에 전달하여 분석을 요청합니다.
    분석이 수행되면 자동 검증(validate_analysis_result)을 거치며, 검증 실패 시 
    해당 실패 사유를 첨부하여 최대 MAX_RETRIES 만큼 자동으로 재작성을 지시합니다.
    (반환값: analysis_text, prompt_tokens, candidate_tokens, val_in_tokens, val_out_tokens)
    """
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(paper_text=paper_text)
    
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Gemini API로 분석 요청 중... (시도 {attempt+1}/{MAX_RETRIES})")
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )
            
            # 토큰 사용량 가져오기
            try:
                prompt_tokens = response.usage_metadata.prompt_token_count
                candidate_tokens = response.usage_metadata.candidates_token_count
            except Exception:
                prompt_tokens = 0
                candidate_tokens = 0
                
            analysis_text = response.text
            
            # 검증 로직 실행
            is_valid, reason, val_in_tokens, val_out_tokens = validate_analysis_result(analysis_text)
            
            if is_valid:
                return analysis_text, prompt_tokens, candidate_tokens, val_in_tokens, val_out_tokens
            else:
                print(f"결과 검증 실패. 재작성을 요청합니다 (시도 {attempt+1}/{MAX_RETRIES}). 사유: {reason}")
                # 프롬프트에 실패 사유 추가하여 재요청 유도
                prompt = ANALYSIS_PROMPT_TEMPLATE.format(paper_text=paper_text) + \
                         f"\n\n이전 생성 결과가 다음 이유로 검증을 통과하지 못했습니다. 이 부분을 반드시 수정해서 다시 작성해 주세요:\n{reason}"
                time.sleep(15)  # 잠시 대기
                continue
                
        except APIError as e:
            if e.code == 429:
                print(f"API 할당량 초과(429). {RETRY_DELAY_SECONDS}초 대기 후 재시도합니다... 에러메시지: {e}")
                time.sleep(RETRY_DELAY_SECONDS)
            else:
                print(f"API 오류 발생: {e}")
                time.sleep(RETRY_DELAY_SECONDS)
        except Exception as e:
            print(f"예상치 못한 오류 발생: {e}")
            return f"분석 실패: {e}", 0, 0, 0, 0
            
    return "분석 실패: 최대 재시도 횟수를 초과했습니다 (API 연동 문제 지속).", 0, 0, 0, 0
