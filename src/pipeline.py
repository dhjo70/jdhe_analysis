import time
from pathlib import Path

from src.pdf_utils import extract_text_from_pdf, get_exact_title
from src.llm_client import analyze_paper_with_retry
from src.tracker import ExecutionTracker

def run_local_analysis(target_dir_name: str, output_file_name: str, header_title: str = None):
    """
    주어진 데스크탑 내 디렉토리의 PDF 파일들을 읽어들여 AI 논문 분석을 수행하는 메인 파이프라인 함수입니다.
    
    1. 이어하기(Resume) 기능: 이미 작성된 결과 파일(output_file_name)을 스캔하여 완료된 논문은 건너뜁니다.
    2. 추출 및 요청: 각 PDF에서 텍스트를 추출하고 LLM API (llm_client)에 분석을 요청합니다.
    3. 기록: 분석에 성공하면 즉시 마크다운(MD) 파일에 결과를 덧붙이고, Tracker를 통해 상태를 저장합니다.
    """
    target_dir = Path(target_dir_name)
    output_file = Path(output_file_name)
    
    pdf_files = sorted(target_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"{target_dir} 폴더에 PDF 파일이 없습니다.")
        return

    print(f"전체 {len(pdf_files)}편의 논문에 대해 분석 및 검증을 처음부터 끝까지 수행합니다.")
    
    display_title = header_title if header_title else target_dir.name
    tracker = ExecutionTracker(total_files=len(pdf_files), target_name=display_title)
    
    # 이미 분석된 논문 목록 확인 (재개/이어하기용)
    processed_titles = set()
    file_mode = "w"
    if output_file.exists():
        file_mode = "a"
        with output_file.open("r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("## "):
                    processed_titles.add(line[3:].strip())
        print(f"기존 분석 결과 발견: {len(processed_titles)}편 건너뜀")

    with output_file.open(file_mode, encoding="utf-8") as f:
        if file_mode == "w":
            f.write(f"# JDHE Analysis - {display_title}\n\n")
        
        for i, pdf_path in enumerate(pdf_files, 1):
            title_to_check = get_exact_title(pdf_path)
            
            if title_to_check in processed_titles:
                print(f"\n[{i}/{len(pdf_files)}] 건너뜀 (이미 분석됨): {pdf_path.name}")
                tracker.add_paper_result(pdf_path.name, i, "SKIPPED", 0, 0, 0, 0)
                continue
                
            print(f"\n[{i}/{len(pdf_files)}] 진행 시작: {pdf_path.name}")
            
            paper_text = extract_text_from_pdf(pdf_path)
            
            if not paper_text.strip():
                print(f"텍스트를 추출할 수 없습니다: {pdf_path.name}")
                tracker.add_paper_result(pdf_path.name, i, "FAILED (No text)", 0, 0, 0, 0)
                continue
            
            analysis_result, a_in, a_out, v_in, v_out = analyze_paper_with_retry(paper_text)
            
            status = "SUCCESS" if "분석 실패" not in analysis_result else "FAILED"
            
            if status == "SUCCESS":
                title = get_exact_title(pdf_path)
                f.write(f"## {title}\n\n")
                f.write(f"{analysis_result}\n\n")
                f.write("---\n\n")
                f.flush()
                
            # (Ultra/Advanced 유료 요금제 사용 및 APIError(429) 재시도 로직이 확보되었으므로 인위적인 지연 배제)
            
    print(f"\n모든 분석이 완료되었습니다. 결과는 {output_file} 파일에 저장되었습니다.")
    tracker.conclude_and_print_summary()
