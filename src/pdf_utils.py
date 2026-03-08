import fitz  # PyMuPDF
import re

def clean_metadata_title(title: str) -> str:
    """
    PDF 메타데이터에 포함된 불필요한 XML 태그나 개행 문자를 제거하여 깔끔한 문자열로 반환합니다.
    """
    if not title:
        return ""
    title = re.sub(r'<\?[^>]+\?>', '', title)
    title = re.sub(r'<[^>]+>', '', title)
    title = title.replace('\n', ' ').replace('\r', '')
    title = re.sub(r'\s+', ' ', title).strip()
    return title

def get_exact_title(pdf_path) -> str:
    """
    PDF 파일에서 논문 제목을 추출합니다.
    먼저 내부 메타데이터('title')를 확인하여 추출을 시도하고, 
    만약 유효하지 않거나 비어있다면 파일명(stem)을 기반으로 제목을 유추하여 반환합니다.
    """
    try:
        with fitz.open(pdf_path) as doc:
            meta_title = clean_metadata_title(doc.metadata.get('title', ''))
            if meta_title and len(meta_title) > 10 and "untitled" not in meta_title.lower():
                return meta_title
            
            base = pdf_path.stem
            clean_base = base.replace("- ", ": ").replace(" -", ":").replace("_", "?")
            return clean_base
    except Exception:
        return pdf_path.stem

def extract_text_from_pdf(pdf_path) -> str:
    """
    PyMuPDF(fitz)를 이용하여 주어진 PDF 파일 경로에서 모든 페이지의 텍스트를 추출하여 반환합니다.
    추출 중 오류가 발생하면 빈 문자열을 반환합니다.
    """
    print(f"텍스트 추출 중: {pdf_path}")
    text = ""
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"PDF 텍스트 추출 중 오류 발생 ({pdf_path}): {e}")
    return text
