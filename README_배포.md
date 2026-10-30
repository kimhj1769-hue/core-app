# 코어 지표 — GitHub Pages 배포

평일 KST 07:10(미국장 마감 후)·23:40(개장 직후)에 GitHub Actions가 `build_market.py`를 돌려 `site/index.html`을 만들고 Pages로 배포한다.
외부 조회(yfinance·CNN)가 실패하면 그 칸만 「확인 불가」로 표시되고 배포는 계속된다. 키·토큰·보유내역 없음(공개 저장소 안전).

## 부장 실행 명령 (이 폴더에서, gh 로그인 상태에서 한 번에 붙여 넣기)

```bash
cd "/mnt/c/Users/Kim.HJ/Desktop/my-secretary/personal/stock-trading/core-app-pages" && gh repo create kimhj1769-hue/core-app --public --source . --push && gh api -X POST repos/kimhj1769-hue/core-app/pages -f build_type=workflow && gh workflow run pages.yml -R kimhj1769-hue/core-app
```

- 2~3분 뒤 주소: https://kimhj1769-hue.github.io/core-app/
- 진행 확인: `gh run list -R kimhj1769-hue/core-app`

## 갤럭시에 앱으로 설치
1. 갤럭시에서 **크롬**으로 위 주소를 연다.
2. 오른쪽 위 **⋮ 메뉴**를 누른다.
3. **「앱 설치」** 또는 **「홈 화면에 추가」**를 누르면 홈 화면에 「코어 지표」 아이콘이 생긴다(오프라인이면 마지막 페이지 표시).

## 로컬 시험
```bash
pip install -r requirements.txt pillow
python3 make_icons.py            # 아이콘 재생성(필요 시)
python3 build_market.py          # site/index.html 생성
cd site && python3 -m http.server 8765
```
