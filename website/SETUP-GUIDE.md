# BUILDIN English Website - Setup Guide
# 빌딘 영문 웹사이트 - 준비물 가이드

---

## 준비해야 할 소스 목록

### 1. 이미지 파일 (website/assets/images/ 폴더에 넣기)

| 파일명 | 용도 | 권장 사이즈 | 비고 |
|--------|------|-------------|------|
| `hero.jpg` | 메인 히어로 배경 | 1920x1080px | 브랜드 대표 이미지 (제품+분위기) |
| `brand-story.jpg` | 브랜드 스토리 섹션 | 600x800px | 브랜드/창업자/제조공정 사진 |
| `product-1.jpg` | 제품1 이미지 | 500x500px | 흰 배경 제품 컷 |
| `product-2.jpg` | 제품2 이미지 | 500x500px | 흰 배경 제품 컷 |
| `product-3.jpg` | 제품3 이미지 | 500x500px | 흰 배경 제품 컷 |
| `favicon.ico` | 브라우저 탭 아이콘 | 32x32px | 로고 심볼 |
| `og-image.jpg` | SNS 공유 썸네일 | 1200x630px | 링크 공유시 미리보기 |

> 이미지는 JPG 또는 PNG, 용량은 각 500KB 이하 권장

---

### 2. 텍스트 내용 (영문으로 준비)

#### Brand Story (브랜드 스토리)
- [ ] 브랜드 설립 배경/스토리 (영문 3~5문장)
- [ ] 브랜드 미션/비전 (영문 1~2문장)
- [ ] 설립연도
- [ ] 보유 인증 (GMP, HACCP, KFDA, ISO 등 해당되는 것)

#### Products (제품 소개) - 제품당
- [ ] 제품명 (영문)
- [ ] 제품 카테고리 (예: Inner Beauty, Immunity, Gut Health)
- [ ] 제품 설명 (영문 2~3문장)
- [ ] 주요 성분 3개 (영문)
- [ ] 제품 이미지

#### Company Info (회사 정보)
- [ ] 회사 영문명
- [ ] 영문 주소
- [ ] 대표 이메일
- [ ] 전화번호 (국제전화 형식: +82-XX-XXXX-XXXX)
- [ ] 사업자등록번호 (선택)

#### SNS 채널 링크
- [ ] Instagram URL
- [ ] YouTube URL
- [ ] TikTok URL
- [ ] 기타 SNS (있으면)

---

### 3. 브랜드 핵심가치 (아래 4개를 영문으로 작성하거나 기존 것 수정)

현재 기본값:
1. **Korean Heritage** - 한국 전통 웰니스
2. **Science-Backed** - 과학적 근거 기반
3. **Global Standards** - 국제 품질 기준
4. **Clean Beauty** - 클린 뷰티 (무첨가)

> 브랜드 핵심가치가 다르면 알려주세요!

---

## 배포 방법 (GitHub Pages)

1. 이 레포지토리 Settings → Pages
2. Source: "GitHub Actions" 선택
3. `website/` 폴더 내용이 자동 배포됨
4. URL: `https://[username].github.io/buildin-automation/`

### 커스텀 도메인 연결 (선택)
1. 도메인 구매 (예: buildin.co.kr, buildin.com)
2. DNS에 CNAME 레코드 추가: `[username].github.io`
3. Settings → Pages → Custom domain에 입력
4. "Enforce HTTPS" 체크

---

## 이미지 교체 방법

### hero.jpg (메인 배경)
`website/assets/css/style.css` 파일에서:
```css
.hero {
    /* 이 줄의 주석을 해제하고 경로 수정 */
    background: url('../images/hero.jpg') center/cover no-repeat;
}
```

### 제품/브랜드 이미지
`website/index.html`에서 `image-placeholder` div를 `<img>` 태그로 교체:
```html
<!-- 변경 전 -->
<div class="image-placeholder">...</div>

<!-- 변경 후 -->
<img src="assets/images/product-1.jpg" alt="Product Name">
```

---

## 문의 폼 연동 (선택)

기본적으로 폼은 UI만 있고 실제 이메일 전송은 안 됩니다.
무료 서비스 연동 방법:

### Formspree (추천, 무료 월 50건)
1. https://formspree.io 가입
2. 새 폼 생성 → 폼 ID 복사
3. `index.html`에서 form 태그 수정:
```html
<form action="https://formspree.io/f/YOUR_FORM_ID" method="POST">
```
