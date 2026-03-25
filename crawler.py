import requests
import json
import os
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

# Apify Actor ID (올리브영 스크래퍼)
ACTOR_ID = "styleindexamerica~kr-oliveyoung-scraper"

# GitHub Actions Secret에서 API 토큰 읽기
APIFY_TOKEN = os.environ.get("APIFY_TOKEN")

DATA_FILE = "data.json"


def run_apify_actor():
    """Apify Actor를 실행하고 결과 데이터를 반환"""
    if not APIFY_TOKEN:
        print("❌ APIFY_TOKEN 환경변수가 없습니다.")
        print("   GitHub → Settings → Secrets → APIFY_TOKEN 을 등록해주세요.")
        return None

    print("🚀 Apify Actor 실행 중...")

    # Actor 실행 요청 (선케어 카테고리, 랭킹순, 1~5페이지)
    run_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items"
    params = {"token": APIFY_TOKEN}
    payload = {
        "categoryUrl": (
            "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do"
            "?dispCatNo=100000100010013&prdSort=01&rowsPerPage=24"
        ),
        "maxPages": 5,
    }

    try:
        # 동기 실행 (완료될 때까지 대기, 최대 5분)
        resp = requests.post(run_url, params=params, json=payload, timeout=300)
        resp.raise_for_status()
        items = resp.json()
        print(f"  ✅ {len(items)}개 상품 데이터 수신")
        return items

    except requests.exceptions.Timeout:
        print("  ⚠️ 타임아웃 - Actor 실행 시간이 너무 깁니다. 비동기 방식으로 재시도...")
        return run_apify_async()
    except Exception as e:
        print(f"  ❌ Apify 호출 실패: {e}")
        return None


def run_apify_async():
    """비동기 방식: Actor 실행 → 완료 대기 → 결과 수집"""
    print("  🔄 비동기 방식으로 실행 중...")

    # 1. Actor 실행 시작
    start_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs"
    params = {"token": APIFY_TOKEN}
    payload = {
        "categoryUrl": (
            "https://www.oliveyoung.co.kr/store/display/getMCategoryList.do"
            "?dispCatNo=100000100010013&prdSort=01&rowsPerPage=24"
        ),
        "maxPages": 5,
    }

    try:
        resp = requests.post(start_url, params=params, json=payload, timeout=30)
        resp.raise_for_status()
        run_id = resp.json()["data"]["id"]
        print(f"  ▶️ 실행 ID: {run_id}")
    except Exception as e:
        print(f"  ❌ Actor 시작 실패: {e}")
        return None

    # 2. 완료될 때까지 폴링 (최대 5분)
    status_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs/{run_id}"
    for i in range(30):  # 10초 간격 × 30 = 5분
        time.sleep(10)
        try:
            resp = requests.get(status_url, params=params, timeout=15)
            status = resp.json()["data"]["status"]
            print(f"  ⏳ 상태: {status} ({(i+1)*10}초 경과)")
            if status == "SUCCEEDED":
                break
            elif status in ("FAILED", "ABORTED", "TIMED-OUT"):
                print(f"  ❌ Actor 실패: {status}")
                return None
        except Exception:
            continue
    else:
        print("  ❌ 5분 초과 - 타임아웃")
        return None

    # 3. 결과 데이터 수집
    dataset_url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/runs/{run_id}/dataset/items"
    try:
        resp = requests.get(dataset_url, params=params, timeout=30)
        resp.raise_for_status()
        items = resp.json()
        print(f"  ✅ {len(items)}개 상품 데이터 수신")
        return items
    except Exception as e:
        print(f"  ❌ 데이터 수집 실패: {e}")
        return None


def extract_rank_and_name(item):
    """Apify 결과 아이템에서 순위와 상품명 추출"""
    # Actor마다 필드명이 다를 수 있으므로 여러 가능성 시도
    name = (
        item.get("productName") or
        item.get("name") or
        item.get("title") or
        item.get("productTitle") or
        ""
    )
    rank = (
        item.get("rank") or
        item.get("ranking") or
        item.get("rankingPosition") or
        None
    )
    return name, rank


def match_targets(items):
    """수신된 데이터에서 TARGET_PRODUCTS 키워드 매칭"""
    results = {}

    # 순위가 없으면 리스트 순서로 대체
    for idx, item in enumerate(items):
        name, rank = extract_rank_and_name(item)
        if rank is None:
            item["_computed_rank"] = idx + 1
        else:
            item["_computed_rank"] = int(rank)

    for keyword in TARGET_PRODUCTS:
        matched = next(
            (item for item in items if keyword in extract_rank_and_name(item)[0]),
            None
        )
        if matched:
            name, _ = extract_rank_and_name(matched)
            rank = matched["_computed_rank"]
            results[keyword] = {"matched_name": name, "rank": rank}
            print(f"  ✅ '{keyword}' → {rank}위 ({name})")
        else:
            results[keyword] = {"matched_name": None, "rank": None}
            print(f"  ❌ '{keyword}' → 범위 밖 또는 미발견")

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
    print("🌞 올리브영 선케어 랭킹 수집 시작 (Apify)")
    print(f"   시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   추적 키워드: {TARGET_PRODUCTS}")
    print("=" * 50)

    items = run_apify_actor()
    if not items:
        print("❌ 데이터 수집 실패")
        return

    print(f"\n[타겟 상품 순위 확인]")
    matched = match_targets(items)

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
