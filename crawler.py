import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

# =============================================
# ✏️ 여기만 수정하세요: 추적할 상품 키워드 5개
# (정확한 전체 이름 말고, 핵심 키워드만 써도 됩니다)
# =============================================
TARGET_PRODUCTS = [
    "조선미녀",
    "라로슈포제",
    "아니스프리",
    "바이오더마",
    "스킨아쿠아",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.oliveyoung.co.kr",
}

# 올리브영 선케어 카테고리 (랭킹순)
BASE_URL = "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do"

DATA_FILE = "data.json"


def fetch_ranking():
    """올리브영 선케어 1~5페이지 크롤링"""
    all_products = []

    for page in range(1, 6):
        params = {
            "dispCatNo": "100000100010013",  # 선케어 카테고리
            "prdSort": "01",                 # 랭킹순
            "pageIdx": str(page),
            "rowsPerPage": "24",
        }

        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"  ⚠️ {page}페이지 요청 실패: {e}")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("ul.prod-list > li")

        if not items:
            print(f"  ⚠️ {page}페이지: 상품을 찾지 못했습니다. (사이트 구조 변경 가능성)")
            break

        for item in items:
            try:
                rank_el = item.select_one(".prod-index, .rank-num, span[class*='rank']")
                name_el = item.select_one(".prod-name, .tx_name, strong.name")

                if not name_el:
                    continue

                name = name_el.get_text(strip=True)

                if rank_el:
                    rank_text = rank_el.get_text(strip=True).replace("위", "").strip()
                    rank = int(rank_text) if rank_text.isdigit() else len(all_products) + 1
                else:
                    rank = len(all_products) + 1

                all_products.append({"rank": rank, "name": name})

            except Exception:
                continue

        print(f"  📄 {page}페이지 완료: 누적 {len(all_products)}개")
        time.sleep(2)  # 서버 부하 방지

    return all_products


def match_targets(all_products):
    """전체 목록에서 TARGET_PRODUCTS 키워드와 매칭"""
    results = {}

    for keyword in TARGET_PRODUCTS:
        matched = None
        for product in all_products:
            if keyword in product["name"]:
                matched = product
                break

        if matched:
            results[keyword] = {"matched_name": matched["name"], "rank": matched["rank"]}
            print(f"  ✅ '{keyword}' → {matched['rank']}위 ({matched['name']})")
        else:
            results[keyword] = {"matched_name": None, "rank": None}
            print(f"  ❌ '{keyword}' → 50위 밖 또는 미발견")

    return results


def load_existing():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"products": {k: [] for k in TARGET_PRODUCTS}, "last_updated": None}


def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  💾 data.json 저장 완료")


def main():
    print("=" * 50)
    print("🌞 올리브영 선케어 랭킹 수집 시작")
    print(f"   시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   추적 키워드: {TARGET_PRODUCTS}")
    print("=" * 50)

    all_products = fetch_ranking()
    if not all_products:
        print("❌ 수집 실패: 상품 목록이 비어있습니다.")
        return

    print("\n[타겟 상품 순위 확인]")
    matched = match_targets(all_products)

    data = load_existing()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    data["last_updated"] = timestamp

    for keyword, result in matched.items():
        if keyword not in data["products"]:
            data["products"][keyword] = []
        data["products"][keyword].append({"time": timestamp, "rank": result["rank"]})
        data["products"][keyword] = data["products"][keyword][-48:]  # 이틀치만 유지

    save(data)
    print("\n✅ 완료!")


if __name__ == "__main__":
    main()
