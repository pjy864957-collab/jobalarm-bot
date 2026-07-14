import requests
from bs4 import BeautifulSoup
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime
import hashlib

# -----------------------------------------------------------------
# 1. 파이어베이스 초기화 (프로그램 실행 시 딱 1번만 수행)
# -----------------------------------------------------------------
# 주의: 아래 json 파일 이름을 본인이 다운받은 키 파일 이름으로 반드시 변경하세요!
key_file_name = "job-alarm-b2c48-firebase-adminsdk-fbsvc-848e62ba18.json"

if not firebase_admin._apps:
    cred = credentials.Certificate(key_file_name)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# 공통 헤더 설정 (브라우저 위장)
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


# -----------------------------------------------------------------
# 2. 사람인(Saramin) 크롤링 함수
# -----------------------------------------------------------------
def scrape_saramin():
    print("\n[시작] 사람인 채용 공고 수집 중...")
    url = "https://www.saramin.co.kr/zf_user/search/recruit?searchword=로스터"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("❌ 사람인 접속 실패")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    job_cards = soup.select(".item_recruit")

    count = 0
    for card in job_cards:
        try:
            # 상표명 추출
            company_tag = card.select_one(".corp_name a")
            if not company_tag:
                company_tag = card.select_one(".corp_name")
            brand_name = company_tag.text.strip() if company_tag else "알수없음"

            # 제목 및 링크 추출
            title_tag = card.select_one(".job_tit a")
            title = title_tag.text.strip() if title_tag else "제목없음"

            if title_tag and 'href' in title_tag.attrs:
                link = title_tag['href']
                full_link = "https://www.saramin.co.kr" + link if link.startswith('/') else link
            else:
                continue

            # 파이어베이스 저장 (함수로 분리)
            save_to_firebase(brand_name, title, full_link, "사람인")
            count += 1

        except Exception as e:
            continue

    print(f"✅ 사람인 수집 완료: 총 {count}건 처리됨")


# -----------------------------------------------------------------
# 3. 잡코리아(JobKorea) 크롤링 함수
# -----------------------------------------------------------------
def scrape_jobkorea():
    print("\n[시작] 잡코리아 채용 공고 수집 중...")
    url = "https://www.jobkorea.co.kr/Search/?stext=로스터"

    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print("❌ 잡코리아 접속 실패")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    job_cards = soup.select(".list-default .list-post")

    count = 0
    for card in job_cards:
        try:
            # 상표명 추출
            company_tag = card.select_one(".post-list-corp a")
            brand_name = company_tag.text.strip() if company_tag else "알수없음"

            # 제목 및 링크 추출
            title_tag = card.select_one(".post-list-info a.title")
            title = title_tag.text.strip() if title_tag else "제목없음"

            if title_tag and 'href' in title_tag.attrs:
                link = title_tag['href']
                full_link = "https://www.jobkorea.co.kr" + link if link.startswith('/') else link
            else:
                continue

            # 파이어베이스 저장 (함수로 분리)
            save_to_firebase(brand_name, title, full_link, "잡코리아")
            count += 1

        except Exception as e:
            continue

    print(f"✅ 잡코리아 수집 완료: 총 {count}건 처리됨")


# -----------------------------------------------------------------
# 4. 파이어베이스 저장 전용 함수 (중복 처리 포함)
# -----------------------------------------------------------------
def save_to_firebase(brand_name, title, link, source):
    # DB에 저장할 데이터 구조
    job_data = {
        "상표명": brand_name,
        "공고명": title,
        "링크": link,
        "출처": source,  # 어느 사이트에서 가져왔는지 표시
        "수집일시": datetime.now(),
        "AI분석여부": False
    }

    # 링크를 해시화하여 고유 문서 ID 생성 (중복 방지)
    doc_id = hashlib.md5(link.encode('utf-8')).hexdigest()

    # 저장 실행
    db.collection('jobs').document(doc_id).set(job_data)


# -----------------------------------------------------------------
# 5. 메인 실행 블록 (여기서 순서대로 실행시킵니다)
# -----------------------------------------------------------------
if __name__ == "__main__":
    print("🚀 통합 크롤러 작동을 시작합니다...")

    scrape_saramin()  # 사람인 먼저 수집
    scrape_jobkorea()  # 이어서 잡코리아 수집

    print("\n🎉 모든 사이트의 크롤링 및 DB 업데이트가 완료되었습니다!")