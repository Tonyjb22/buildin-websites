# 🚀 빌딘 컨텐츠 자동화 시스템 - 설정 가이드

## 📋 전체 구조

```
매주 월요일 오전 9시 자동 실행 (GitHub Actions)
    │
    ├── STEP 1: 데이터 수집
    │   ├── Instagram API → 조회수, 좋아요, 저장, 댓글, 공유
    │   ├── YouTube API → 조회수, 좋아요, 댓글
    │   └── TikTok, 스레드, X → 수동 입력 유지
    │
    ├── STEP 2: Notion DB 업데이트
    │   ├── 컨텐츠 목록 DB에 자동 저장/갱신
    │   └── 주차별 정리 DB 자동 업데이트
    │
    └── STEP 3: 주간 분석 페이지 자동 생성
        ├── 전주 대비 성과 비교표
        ├── 플랫폼별 상세 분석
        ├── 상위 성과 컨텐츠 TOP 5
        ├── 주요 인사이트 (자동 생성)
        ├── 개선 포인트 (자동 생성)
        └── 다음주 컨텐츠 방향 제안
```

---

## 🔧 설정 순서 (약 30분 소요)

### STEP 1: Notion API 설정 (10분)

Notion API는 외부 프로그램이 노션 데이터를 읽고 쓸 수 있게 해주는 "통로"입니다.

**1-1. Integration 만들기**
1. https://www.notion.so/my-integrations 접속
2. "새 인테그레이션(New integration)" 클릭
3. 이름: `빌딘 자동화` 입력
4. 연결할 워크스페이스 선택
5. 기능(Capabilities)에서 다음을 체크:
   - ✅ 콘텐츠 읽기 (Read content)
   - ✅ 콘텐츠 업데이트 (Update content)  
   - ✅ 콘텐츠 삽입 (Insert content)
6. "제출(Submit)" 클릭
7. **시크릿 토큰 복사** (secret_xxx... 형태) → 안전한 곳에 저장!

**1-2. 노션 DB에 연결하기**
1. 기존 "컨텐츠 성과 추적" 데이터베이스 페이지 열기
2. 우측 상단 `...` → "연결(Connections)" → "빌딘 자동화" 선택
3. "주차별 정리" 데이터베이스에도 동일하게 연결
4. 주간 분석 리포트를 생성할 상위 페이지에도 연결

**1-3. 데이터베이스 ID 찾기**
노션 DB를 열었을 때 URL이 이렇게 됩니다:
```
https://www.notion.so/workspace/abc123def456...?v=...
                              ^^^^^^^^^^^^^^^^
                              이 부분이 DB ID (32자리)
```

필요한 ID 3개:
- `NOTION_CONTENT_DB_ID`: 컨텐츠 목록 DB의 ID
- `NOTION_WEEKLY_DB_ID`: 주차별 정리 DB의 ID  
- `NOTION_ANALYSIS_PAGE_ID`: 주간 분석 리포트를 넣을 페이지의 ID

---

### STEP 2: Instagram API 설정 (10분)

Instagram 비즈니스 계정의 데이터를 자동으로 가져오기 위한 설정입니다.

**2-1. Facebook 개발자 계정**
1. https://developers.facebook.com 접속 및 로그인
2. "내 앱(My Apps)" → "앱 만들기(Create App)"
3. 앱 타입: "비즈니스(Business)" 선택
4. 앱 이름: `빌딘 컨텐츠 자동화`

**2-2. Instagram Graph API 설정**
1. 앱 대시보드 → "제품 추가(Add Products)" → "Instagram Graph API" 설정
2. "도구(Tools)" → "Graph API 탐색기(Graph API Explorer)"
3. 권한 추가:
   - `instagram_basic`
   - `instagram_manage_insights`
   - `pages_show_list`
   - `pages_read_engagement`
4. "액세스 토큰 생성(Generate Access Token)" 클릭

**2-3. 장기 토큰 발급 (중요!)**
기본 토큰은 1시간 후 만료됩니다. 장기 토큰으로 교환하세요:
```
https://graph.facebook.com/v19.0/oauth/access_token?
  grant_type=fb_exchange_token&
  client_id={앱ID}&
  client_secret={앱시크릿}&
  fb_exchange_token={단기토큰}
```
→ 60일 유효 토큰 발급됨 (60일마다 갱신 필요)

**2-4. 비즈니스 계정 ID 찾기**
Graph API 탐색기에서:
```
GET /me/accounts?fields=instagram_business_account
```
→ `instagram_business_account.id` 값이 비즈니스 계정 ID

---

### STEP 3: YouTube API 설정 (5분)

**3-1. API 키 발급**
1. https://console.cloud.google.com 접속
2. 새 프로젝트 생성: `빌딘-자동화`
3. "API 및 서비스" → "라이브러리" → "YouTube Data API v3" 검색 → 사용 설정
4. "사용자 인증 정보" → "API 키 만들기" → 키 복사

**3-2. 채널 ID 찾기**
유튜브 채널 페이지 → URL에서 확인:
```
https://www.youtube.com/channel/UCxxxxxxxxxxxxxxxx
                                 ^^^^^^^^^^^^^^^^^^
                                 이것이 채널 ID
```
또는 https://www.youtube.com/@핸들명 인 경우:
YouTube Data API로 조회하거나, 채널 페이지 소스에서 `channelId` 검색

---

### STEP 4: GitHub 설정 및 배포 (5분)

GitHub Actions는 무료로 코드를 정해진 시간에 자동 실행해주는 서비스입니다.

**4-1. GitHub 계정 & 레포지토리**
1. https://github.com 가입 (없다면)
2. "New repository" → 이름: `buildin-automation` → Private 선택 → 생성

**4-2. 코드 업로드**
제가 제공한 파일들을 레포지토리에 업로드:
```
buildin-automation/
├── .github/workflows/weekly-automation.yml
├── config.py
├── notion_client.py
├── instagram_collector.py
├── youtube_collector.py
├── weekly_analyzer.py
├── main.py
├── requirements.txt
├── .env.example
└── README.md (이 파일)
```

**4-3. Secrets 설정 (환경변수)**
레포지토리 → Settings → Secrets and variables → Actions → "New repository secret"

아래 항목들을 하나씩 추가:

| Secret 이름 | 값 |
|---|---|
| `NOTION_API_TOKEN` | secret_xxx... (Step 1에서 복사한 값) |
| `NOTION_CONTENT_DB_ID` | 컨텐츠 목록 DB ID |
| `NOTION_WEEKLY_DB_ID` | 주차별 정리 DB ID |
| `NOTION_ANALYSIS_PAGE_ID` | 분석 리포트 상위 페이지 ID |
| `INSTAGRAM_ACCESS_TOKEN` | IG 장기 액세스 토큰 |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | IG 비즈니스 계정 ID (오피셜) |
| `INSTAGRAM_MAGAZINE_ACCOUNT_ID` | IG 비즈니스 계정 ID (매거진) |
| `YOUTUBE_API_KEY` | YouTube API 키 |
| `YOUTUBE_CHANNEL_ID` | YouTube 채널 ID |
| `VIEWS_BEST` | 10000 (조회수 '최상' 기준) |
| `VIEWS_HIGH` | 3000 (조회수 '상' 기준) |
| `VIEWS_MID` | 1000 (조회수 '중' 기준) |
| `ENGAGEMENT_BEST` | 5.0 (참여율 '최상' 기준 %) |
| `ENGAGEMENT_HIGH` | 3.0 (참여율 '상' 기준 %) |
| `ENGAGEMENT_MID` | 1.0 (참여율 '중' 기준 %) |

**4-4. 테스트 실행**
1. 레포지토리 → Actions 탭 → "빌딘 주간 컨텐츠 자동화"
2. "Run workflow" → command: `test` → 실행
3. 로그에서 각 API 연결 성공 확인

**4-5. 첫 전체 실행**
1. Actions → "Run workflow" → command: `full` → 실행
2. 노션에서 데이터가 잘 들어왔는지 확인

이후에는 **매주 월요일 오전 9시**에 자동으로 실행됩니다!

---

## ⚠️ 주의사항 및 FAQ

### 수동 입력이 필요한 항목
- **틱톡**: API 접근이 제한적이라 수동으로 조회수 등을 입력해야 합니다
- **스레드, X**: API 미지원으로 수동 입력
- **레퍼런스 링크**: 다음주 컨텐츠 기획의 레퍼런스는 수동으로 추가

### Instagram 토큰 갱신 (60일마다)
장기 토큰은 60일 후 만료됩니다. 만료 전에 갱신하세요:
```
https://graph.facebook.com/v19.0/oauth/access_token?
  grant_type=fb_exchange_token&
  client_id={앱ID}&
  client_secret={앱시크릿}&
  fb_exchange_token={현재토큰}
```
갱신한 토큰을 GitHub Secrets에서 `INSTAGRAM_ACCESS_TOKEN` 업데이트

### 평가 기준 조정
현재 기본값 (4단계):

**평가1 — 조회수 (바이럴)**
- 🔥 최상: 10,000회 이상 → 알고리즘 노출 성공
- ⭐ 상: 3,000~9,999회 → 탐색 탭 노출 시작
- 😐 중: 1,000~2,999회 → 팔로워/해시태그 유입 (평타)
- 👎 하: 999회 이하 → 노출 실패

**평가2 — 참여율 (컨텐츠 매력도)**
- 🔥 최상: 5% 이상 → 찐팬 형성
- ⭐ 상: 3~4.99% → 타겟 안정적 반응
- 😐 중: 1~2.99% → 나쁘지 않음
- 👎 하: 1% 미만 → 이탈률 높음

**총평은 조회수×참여율 매트릭스**로 16가지 조합에 따라 액션플랜이 자동 결정됩니다.
(예: 최상-최상 = 광고집행, 하-최상 = 썸네일교체 등)

이 기준은 GitHub Secrets의 `VIEWS_BEST`, `VIEWS_HIGH`, `VIEWS_MID`,
`ENGAGEMENT_BEST`, `ENGAGEMENT_HIGH`, `ENGAGEMENT_MID` 값을 변경하면 됩니다.

### D+6 참여율 계산 로직
기본 공식: 참여율(%) = (좋아요 + 댓글 + 저장 + 공유) ÷ 조회수 × 100

기존 노션 수식과 동일한 보정 로직도 적용되어 있습니다 (자사 직원 반응 차감):
- 유튜브 숏츠: (좋아요-1) / 조회수 × 100
- 기타: ((좋아요-3) + (저장-3) + (공유-3) + (댓글×0.5)) / 조회수 × 100
- 각 값의 최솟값은 0

### 자동화되는 것 vs 수동으로 해야 하는 것

| 항목 | 자동 | 수동 |
|------|------|------|
| Instagram 데이터 수집 (릴스/피드) | ✅ | |
| YouTube 데이터 수집 (롱폼/숏츠) | ✅ | |
| TikTok 데이터 입력 (피드/릴스) | | ✅ |
| Notion 컨텐츠 DB 업데이트 | ✅ | |
| 주차별 정리 DB 업데이트 | ✅ | |
| 전주 대비 비교 분석 | ✅ | |
| 성과 평가 (최상/상/중/하) | ✅ | |
| 총평 액션플랜 (16가지 매트릭스) | ✅ | |
| 인사이트 & 개선점 생성 | ✅ | |
| 다음주 방향 제안 | ✅ | |
| 레퍼런스 링크 추가 | | ✅ |
| 구체적 컨텐츠 기획 | | ✅ |

---

## 🔄 확장 가능성

나중에 추가할 수 있는 기능들:
1. **슬랙/카카오톡 알림**: 월요일 분석 완료 시 팀에게 자동 알림
2. **경쟁사 모니터링**: 경쟁 브랜드 계정 조회수 자동 트래킹
3. **AI 레퍼런스 추천**: 트렌드 분석 기반 자동 레퍼런스 수집
4. **TikTok 자동화**: TikTok Business API 접근 시 자동화 가능
5. **대시보드 시각화**: 별도 웹 대시보드 구축 가능
