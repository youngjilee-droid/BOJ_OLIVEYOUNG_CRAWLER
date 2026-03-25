import requests
from bs4 import BeautifulSoup
import json
import schedule
import time
from datetime import datetime

# =============================================
# 여기에 추적하고 싶은 상품 이름을 입력하세요
# (올리브영 상품 페이지에 표시되는 이름과 동일하게)
# =============================================
TARGET_PRODUCTS = [
    "조선미녀 맑은쌀 선크림",
    "라로슈포제 선크림",
    "아니스프리 선크림",
    "바이오더마 선크림",
    "스킨아쿠아 선크림",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 올리브영 선케어 랭킹 URL (1~5페이지)
BASE_URL = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do"
PARAMS = {
    "dispCatNo": "100000100010013",  # 선케어 카테고리 번호
    "fltDispCatNo": "",
    "prdSort": "01",  # 01 = 랭킹순
    "pageIdx": "1",
    "rowsPerPage": "24",
    "searchTypeSort": "btn_thumb",
    "plusButtonFlag": "N",
}

DATA_FILE = "data.json"


def fetch_ranking():
    """올리브영 선케어 랭킹을 크롤링해서 반환"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 크롤링 시작...")

    all_products = []

    try:
        for page in range(1, 6):  # 1~5페이지 (최대 120개 상품)
            PARAMS["pageIdx"] = str(page)
            response = requests.get(BASE_URL, params=PARAMS, headers=HEADERS, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.select("li.flag.new, li.prod-item")  # 상품 리스트 항목

            if not items:
                # 선택자가 맞지 않을 경우를 대비한 대체 선택자
                items = soup.select(".prd_info")

            for item in items:
                try:
                    rank_tag = item.select_one(".rank")
                    name_tag = item.select_one(".tx_name, .prd_name")

                    if not name_tag:
                        continue

                    rank = rank_tag.get_text(strip=True) if rank_tag else str(len(all_products) + 1)
                    name = name_tag.get_text(strip=True)

                    all_products.append({"rank": int(rank.replace("위", "")), "name": name})

                except Exception:
                    continue

            time.sleep(1)  # 서버 부하 방지

    except Exception as e:
        print(f"  ❌ 크롤링 오류: {e}")
        return None

    print(f"  ✅ 총 {len(all_products)}개 상품 수집 완료")
    return all_products


def find_target_ranks(all_products):
    """수집된 전체 랭킹에서 추적 대상 상품의 순위를 찾음"""
    results = []

    for target in TARGET_PRODUCTS:
        found = False
        for product in all_products:
            # 상품명이 일부라도 포함되면 매칭
            if any(word in product["name"] for word in target.split()):
                results.append({
                    "target": target,
                    "matched_name": product["name"],
                    "rank": product["rank"],
                })
                found = True
                break

        if not found:
            results.append({
                "target": target,
                "matched_name": None,
                "rank": None,  # 50위 밖이거나 못 찾음
            })

    return results


def load_existing_data():
    """기존 저장된 데이터 불러오기"""
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"products": {name: [] for name in TARGET_PRODUCTS}, "last_updated": None}


def save_data(data):
    """데이터를 JSON 파일로 저장"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  💾 데이터 저장 완료: {DATA_FILE}")


def run_crawl():
    """크롤링 실행 + 데이터 누적 저장"""
    all_products = fetch_ranking()
    if all_products is None:
        return

    results = find_target_ranks(all_products)
    data = load_existing_data()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    data["last_updated"] = timestamp

    for result in results:
        name = result["target"]
        rank = result["rank"]
        matched = result["matched_name"]

        print(f"  📊 {name}: {rank}위 (매칭: {matched})")

        if name not in data["products"]:
            data["products"][name] = []

        # 최근 48개 데이터 포인트만 유지 (1시간 주기 × 48 = 이틀치)
        data["products"][name].append({"time": timestamp, "rank": rank})
        if len(data["products"][name]) > 48:
            data["products"][name] = data["products"][name][-48:]

    save_data(data)
    print(f"  ✅ 완료!\n")


# =============================================
# 실행
# =============================================
if __name__ == "__main__":
    print("🚀 올리브영 선케어 랭킹 트래커 시작!")
    print(f"   추적 상품: {', '.join(TARGET_PRODUCTS)}")
    print(f"   업데이트 주기: 1시간마다\n")

    # 시작하자마자 한 번 즉시 실행
    run_crawl()

    # 이후 1시간마다 자동 실행
    schedule.every(1).hours.do(run_crawl)

    while True:
        schedule.run_pending()
        time.sleep(60)
