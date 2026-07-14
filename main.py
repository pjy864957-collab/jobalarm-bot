import requests
from bs4 import BeautifulSoup

# 검색어 '로스터'가 포함된 사람인 채용 검색 페이지 주소입니다.
url = "https://www.saramin.co.kr/zf_user/search/recruit?searchword=로스터"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')

    # 변경점: 사람인은 보통 'item_recruit'라는 이름표를 가진 큰 박스 안에 공고 1개가 들어있습니다.
    job_cards = soup.select(".item_recruit")

    print("--- ☕ 사람인 로스터 상세 채용 공고 ---\n")

    for card in job_cards:
        try:
            # 1. 회사명 찾기 (사람인은 .corp_name 이라는 구역에 회사명이 있습니다)
            company_tag = card.select_one(".corp_name a")
            if not company_tag:  # 간혹 a 태그 없이 텍스트만 있는 경우를 대비한 안전장치
                company_tag = card.select_one(".corp_name")

            company = company_tag.text.strip() if company_tag else "회사명 없음"

            # 2. 공고 제목 찾기 (사람인은 .job_tit a 이라는 구역에 제목이 있습니다)
            title_tag = card.select_one(".job_tit a")
            title = title_tag.text.strip() if title_tag else "제목 없음"

            # 3. 상세 링크 찾기
            if title_tag and 'href' in title_tag.attrs:
                link = title_tag['href']
                # 사람인 링크 역시 앞부분(https://www.saramin.co.kr)이 생략된 경우가 많아 붙여줍니다.
                if link.startswith('/'):
                    full_link = "https://www.saramin.co.kr" + link
                else:
                    full_link = link
            else:
                full_link = "링크 없음"

            # 결과 출력
            if company != "회사명 없음" and title != "제목 없음":
                print(f"🏢 회사명 : {company}")
                print(f"📝 공고명 : {title}")
                print(f"🔗 링크   : {full_link}")
                print("-" * 50)

        except Exception as e:
            # 에러가 나더라도 멈추지 않고 다음 공고로 넘어갑니다.
            continue
else:
    print(f"오류가 발생했습니다. 상태 코드: {response.status_code}")