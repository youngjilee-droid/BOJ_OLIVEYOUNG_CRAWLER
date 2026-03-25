🌞 올리브영 선케어 랭킹 트래커
GitHub Actions로 1시간마다 자동 수집 + GitHub Pages로 대시보드 제공
---
📁 파일 구조
```
oliveyoung-dashboard/
├── .github/workflows/crawl.yml  ← GitHub Actions 자동 스케줄러
├── crawler.py                   ← 랭킹 수집 코드
├── dashboard.html               ← 대시보드 화면
└── data.json                    ← 자동 생성/업데이트됨
```
---
🚀 설정 방법 (처음 한 번만)
1단계: GitHub 저장소 만들기
https://github.com 로그인
우측 상단 `+` → `New repository`
Repository name: `oliveyoung-dashboard`
Public 선택 (GitHub Pages 무료 사용을 위해)
`Create repository` 클릭
2단계: 파일 업로드
crawler.py, dashboard.html, data.json을 드래그 업로드.
crawl.yml은 `Add file → Create new file`에서 파일명에
`.github/workflows/crawl.yml` 직접 입력 후 내용 붙여넣기.
3단계: Actions 권한 설정 ⚠️ 중요!
Settings → Actions → General → Workflow permissions →
`Read and write permissions` 선택 → Save
4단계: GitHub Pages 활성화
Settings → Pages → Branch: main / root → Save
→ https://[내아이디].github.io/oliveyoung-dashboard/dashboard.html 접속
---
✏️ 추적 상품 변경
crawler.py 상단의 TARGET_PRODUCTS 리스트를 원하는 키워드로 교체하세요.
▶️ 수동 실행
Actions 탭 → 올리브영 랭킹 수집 → Run workflow
