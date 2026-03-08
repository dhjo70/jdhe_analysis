import datetime
from pathlib import Path

from src.config import INPUT_PRICE_PER_M, OUTPUT_PRICE_PER_M

class ExecutionTracker:
    """
    배치 분석 작업 동안의 처리 결과, 토큰 사용량, 소요 시간 및 예상 비용을 추적하는 클래스입니다.
    분석 상태를 콘솔에 출력하고, 영구적인 로그 파일(run_history.log)에 기록을 남깁니다.
    """
    def __init__(self, total_files: int, target_name: str, log_file: str = "run_history.log"):
        self.total_files = total_files
        self.target_name = target_name
        self.log_file = Path(log_file)
        self.start_time = datetime.datetime.now()
        
        self.total_analysis_in = 0
        self.total_analysis_out = 0
        self.total_val_in = 0
        self.total_val_out = 0
        self.analyzed_count = 0
        
        self._write_log_header()
        
    def _write_log_header(self):
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(f"\n[{self.start_time.isoformat()}] ===== 실행 시작: {self.target_name} =====\n")
            f.write(f"Target PDFs: {self.total_files}\n\n")
            
    def add_paper_result(self, pdf_name: str, index: int, status: str, a_in: int, a_out: int, v_in: int, v_out: int):
        """
        개별 논문의 처리 결과를 추적기에 추가합니다. 
        성공 여부 및 API 토큰 사용량(분석 입/출력, 검증 입/출력)을 집계합니다.
        """
        self.total_analysis_in += a_in
        self.total_analysis_out += a_out
        self.total_val_in += v_in
        self.total_val_out += v_out
        
        if status == "SUCCESS":
            self.analyzed_count += 1
            
        print(f"[{index}/{self.total_files}] 처리 완료 ({status}). (분석 In:{a_in}/Out:{a_out} | 검증 In:{v_in}/Out:{v_out})")
        
        with self.log_file.open("a", encoding="utf-8") as lf:
            lf.write(f"[{datetime.datetime.now().isoformat()}] [{index}/{self.total_files}] {pdf_name} | Status: {status} | Tokens (A_in:{a_in}, A_out:{a_out}, V_in:{v_in}, V_out:{v_out})\n")
    
    def conclude_and_print_summary(self):
        """
        모든 작업이 끝난 후 총 소요 시간, 토큰 사용량 및 Gemini API 기준 예상 과금액을 계산하여 
        터미널에 출력하고 로그 파일에 저장합니다.
        """
        end_time = datetime.datetime.now()
        duration = end_time - self.start_time
        
        if self.analyzed_count == 0:
            print("\n분석된 논문이 없습니다.")
            return

        total_in = self.total_analysis_in + self.total_val_in
        total_out = self.total_analysis_out + self.total_val_out
        
        total_cost = (total_in / 1_000_000 * INPUT_PRICE_PER_M) + (total_out / 1_000_000 * OUTPUT_PRICE_PER_M)
        avg_cost_per_paper = total_cost / self.analyzed_count if self.analyzed_count else 0
        total_est_cost_800 = avg_cost_per_paper * 800
        
        summary_msg = f"""
{"="*50}
📊 [실행 완료 통계]
실행 시간: {duration}
분석된 논문 수: {self.analyzed_count} / {self.total_files}
총 사용 토큰: 입력 {total_in:,} (분석 {self.total_analysis_in:,} + 검증 {self.total_val_in:,}) / 출력 {total_out:,} (분석 {self.total_analysis_out:,} + 검증 {self.total_val_out:,})
이번 실행 총 청구 비용 (Gemini Pro 기준): ${total_cost:.4f}
논문 1개당 평균 예상 비용: ${avg_cost_per_paper:.4f}
{"-"*50}
🚀 [800편 전체 분석 시 예상 총 비용]: 약 ${total_est_cost_800:.2f} USD
{"="*50}"""
        print(summary_msg)
        
        with self.log_file.open("a", encoding="utf-8") as lf:
            lf.write(summary_msg + "\n")
