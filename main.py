"""
JDHE Analysis Pipeline - 메인 엔트리포인트 모듈입니다.
콘솔 메뉴를 통해 사용자로부터 수행할 배치 작업을 선택받고, 
Google Drive 문서 탐색(drive_client)과 로컬 LLM 분석 파이프라인(pipeline)을 연결합니다.
"""

import sys
import random
from pathlib import Path
from src.pipeline import run_local_analysis
from src.drive_client import get_drive_service, get_subfolders, get_pdfs_in_folder, download_file
from src.config import DRIVE_ROOT_FOLDER_ID

def run_drive_batch():
    """
    Google Drive의 전체 19개 Volume을 순차적으로 탐색하며 배치(Batch) 다운로드 및 분석을 수행합니다.
    하나의 Volume(산하 모든 Issue 포함) 작업이 완료될 때마다 사용자 입력을 대기(일시정지)하여,
    토큰 사용량/비용 등 로그 확인 후 안전하게 다음 넘어갈지 여부를 결정할 수 있게 설계되었습니다.
    """
    print("\nGoogle Drive 연동을 초기화합니다...")
    try:
        service = get_drive_service()
    except Exception as e:
        print(f"인증 오류: {e}")
        return

    print("루트 폴더에서 볼륨(Volume) 목록을 스캔합니다...")
    volumes = get_subfolders(service, DRIVE_ROOT_FOLDER_ID)
    # Vol 로 시작하는 폴더만 필터링
    volumes = [v for v in volumes if v['name'].startswith('Vol')]
    if not volumes:
        print("볼륨 폴더를 찾을 수 없습니다.")
        return

    # Vol 이름을 기준으로 정렬 (예: Vol01, Vol02...)
    volumes = sorted(volumes, key=lambda x: x['name'])
    
    print(f"총 {len(volumes)}개의 볼륨이 감지되었습니다.")
    
    for vol in volumes:
        print(f"\n==================================================")
        print(f"📦 [Volume] {vol['name']} 처리 준비중...")
        print(f"==================================================")
        
        issues = get_subfolders(service, vol['id'])
        # Issue 또는 Suppl 폴더만 필터링
        issues = [i for i in issues if i['name'].startswith('Issue') or i['name'].startswith('Suppl')]
        issues = sorted(issues, key=lambda x: x['name'])
        
        for issue in issues:
            print(f"\n  └ 📂 [Issue] {issue['name']} 다운로드 및 분석 대기중...")
            
            # 구조 생성: /papers/VolXX/IssueX/
            local_issue_dir = Path(f"papers/{vol['name']}/{issue['name']}")
            local_issue_dir.mkdir(parents=True, exist_ok=True)
            
            pdfs = get_pdfs_in_folder(service, issue['id'])
            if not pdfs:
                print(f"    - PDF 파일이 없습니다.")
                continue
                
            print(f"    - {len(pdfs)}개의 PDF 발견, 로컬 다운로드 동기화 진행...")
            for pdf in pdfs:
                save_path = local_issue_dir / pdf['name']
                # 이미 로컬에 다운로드 되어있지 않은 파일만 받음
                if not save_path.exists():
                    print(f"      📥 다운로드 중: {pdf['name']}")
                    success = download_file(service, pdf['id'], str(save_path))
                    if not success:
                        print(f"      ❌ 오류: {pdf['name']} 다운로드 실패")
            
            # 파이프라인 호출 (결과 파일 경로 구성)
            print(f"    - {local_issue_dir} 폴더 분석 파이프라인 진입...")
            output_dir = Path(f"results/{vol['name']}")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 예: results/Vol15/Vol15_Issue1.md
            output_md = output_dir / f"{vol['name']}_{issue['name']}.md"
            
            header = f"{vol['name']} {issue['name']}"
            run_local_analysis(str(local_issue_dir), str(output_md), header)
            
        print(f"\n✅ {vol['name']} 볼륨 (모든 Issue 포함) 처리가 완료되었습니다.")
        
        # 체크포인트 - 사용자 확인 후 다음으로
        print("잠시 멈춥니다. 위 실행 통계와 터미널 로그를 확인해 주세요.")
        ans = input(f"다음 볼륨으로 스캔을 계속하시겠습니까? (Y/n): ")
        if ans.strip().lower() == 'n':
            print("\n🛑 사용자 요청에 의해 스캔을 중단합니다.")
            break

def run_random_drive_issue():
    """
    전체 19개 Volume 및 하위 Issue 중 하나를 무작위(Random)로 선택하여 단일 테스트 환경을 제공합니다.
    선택된 Issue 내부의 PDF 파일들만 로컬에 동기화하고, 즉시 분석을 진행합니다.
    프롬프트 조정 혹은 API 통신 상태 점검 시 유용하게 사용됩니다.
    """
    print("\nGoogle Drive 연동을 초기화합니다...")
    try:
        service = get_drive_service()
    except Exception as e:
        print(f"인증 오류: {e}")
        return

    print("루트 폴더에서 볼륨(Volume) 목록을 스캔합니다...")
    volumes = get_subfolders(service, DRIVE_ROOT_FOLDER_ID)
    # Vol 로 시작하는 폴더만 필터링
    volumes = [v for v in volumes if v['name'].startswith('Vol')]
    if not volumes:
        print("볼륨 폴더를 찾을 수 없습니다.")
        return

    # 무작위 Volume 하나 선택
    random_vol = random.choice(volumes)
    print(f"\n🎲 무작위로 선택된 Volume: {random_vol['name']}")
    
    issues = get_subfolders(service, random_vol['id'])
    # Issue 또는 Suppl 폴더만 필터링
    issues = [i for i in issues if i['name'].startswith('Issue') or i['name'].startswith('Suppl')]
    if not issues:
        print(f"{random_vol['name']} 내에 하위 Issue 폴더를 찾을 수 없습니다.")
        return
        
    # 선택된 Volume 내에서 무작위 Issue 하나 선택
    random_issue = random.choice(issues)
    print(f"🎲 무작위로 선택된 Issue: {random_issue['name']}")
    
    # 구조 생성: /papers/VolXX/IssueX/
    local_issue_dir = Path(f"papers/{random_vol['name']}/{random_issue['name']}")
    local_issue_dir.mkdir(parents=True, exist_ok=True)
    
    pdfs = get_pdfs_in_folder(service, random_issue['id'])
    if not pdfs:
        print(f"    - PDF 파일이 없습니다.")
        return
        
    print(f"    - {len(pdfs)}개의 PDF 발견, 로컬 다운로드 동기화 진행...")
    for pdf in pdfs:
        save_path = local_issue_dir / pdf['name']
        if not save_path.exists():
            print(f"      📥 다운로드 중: {pdf['name']}")
            success = download_file(service, pdf['id'], str(save_path))
            if not success:
                print(f"      ❌ 오류: {pdf['name']} 다운로드 실패")
    
    # 파이프라인 호출
    print(f"\n    - {local_issue_dir} 폴더 분석 파이프라인 진입...")
    output_dir = Path(f"results/{random_vol['name']}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_md = output_dir / f"{random_vol['name']}_{random_issue['name']}.md"
    header = f"{random_vol['name']} {random_issue['name']}"
    run_local_analysis(str(local_issue_dir), str(output_md), header)
    
    print(f"\n✅ {random_vol['name']} {random_issue['name']} 단일 랜덤 분석 처리가 완료되었습니다.")

def main():
    """
    스크립트 실행 시 사용자에게 제공되는 간단한 CLI 형태의 인터페이스 메뉴 체계입니다.
    """
    print("=========================================")
    print(" JDHE Analysis Pipeline - 메인 메뉴")
    print("=========================================")
    print("1. Google Drive 기반 무작위 1개 Issue 테스트 (Random Pickup)")
    print("2. Google Drive 전체 Batch 실행 (19개 Volume 순차 처리)")
    print("3. 종료")
    
    choice = input("\n메뉴 번호를 선택하세요: ")
    
    if choice == '1':
        run_random_drive_issue()
    elif choice == '2':
        run_drive_batch()
    else:
        print("종료합니다.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] 사용자에 의해 실행이 중단되었습니다.")
        sys.exit(130)
