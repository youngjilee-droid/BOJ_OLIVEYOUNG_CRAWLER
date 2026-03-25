from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

# =============================================
# ✏️ 여기만 수정하세요: 추적할 상품 키워드 5개
# =============================================
TARGET_PRODUCTS = [
    "조선미녀",
    "라로슈포제",
    "아니스프리",
    "바이오더마",
    "스킨아쿠아",
]

# 올리브영 선케어 카테고리 URL (랭킹순)
BASE_URL = (
    "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do"
    "?dispCatNo=100000100010013&prdSort=01&rowsPerPage=24&pageIdx={page}"
)

DATA_FILE = "data.json"


def get_driver():
    """헤드리스 Chrome 드라이버 설정 (봇 감지 우회)"""
    options = Options()
    options.add_argument("--headless")           # 화면 없이 실행
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    options.add_argument("--lang=ko-KR")
    driver = webdriver.Chrome(options=options)
    # navigator.webdriver 속성 숨기기
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def fetch_ranking():
    """Selenium으로 올리브영 선케어 1~5페이지 크롤링"""
    all_products = []
    driver = get_driver()

    try:
        # 먼저 메인 페이지 방문 (자연스러운 접속처럼 보이게)
        print("  🌐 올리브영 메인 페이지 방문 중...")
        driver.get("https://www.oliveyoung.co.kr")
        time.sleep(3)

        for page in range(1, 6):
            url = BASE_URL.format(page=page)
            print(f"  📄 {page}페이지 접속 중...")
            driver.get(url)

            # 상품 목록이 로드될 때까지 최대 15초 대기
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "ul.prod-list"))
                )
            except Exception:
                print(f"  ⚠️ {page}페이지 로딩 타임아웃")
                continue

            soup = BeautifulSoup(driver.page_source, "html.parser")
            items = soup.select("ul.prod-list > li")

            if not items:
                print(f"  ⚠️ {page}페이지: 상품 없음 (마지막 페이지일 수 있음)")
                break

            for item in items:
                try:
                    rank_el = item.select_one(".prod-index")
                    name_el = item.select_one(".prod-name")

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

            print(f"     → 누적 {len(all_products)}개 수집")
            time.sleep(2)  # 페이지 간 간격

    finally:
        driver.quit()

    return all_products


def match_targets(all_products):
    results = {}
    for keyword in TARGET_PRODUCTS:
        matched = next((p for p in all_products if keyword in p["name"]), None)
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

    print(f"\n총 {len(all_products)}개 상품 수집 완료")
    print("\n[타겟 상품 순위 확인]")
    matched = match_targets(all_products)

    data = load_existing()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    data["last_updated"] = timestamp

    for keyword, result in matched.items():
        if keyword not in data["products"]:
            data["products"][keyword] = []
        data["products"][keyword].append({"time": timestamp, "rank": result["rank"]})
        data["products"][keyword] = data["products"][keyword][-48:]

    save(data)
    print("\n✅ 완료!")


if __name__ == "__main__":
    main()
