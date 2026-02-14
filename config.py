"""
빌딘 컨텐츠 자동화 시스템 - 설정 모듈
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Notion
    NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN")
    NOTION_CONTENT_DB_ID = os.getenv("NOTION_CONTENT_DB_ID")
    NOTION_WEEKLY_DB_ID = os.getenv("NOTION_WEEKLY_DB_ID")
    NOTION_ANALYSIS_PAGE_ID = os.getenv("NOTION_ANALYSIS_PAGE_ID")

    # Instagram
    INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    INSTAGRAM_MAGAZINE_ACCOUNT_ID = os.getenv("INSTAGRAM_MAGAZINE_ACCOUNT_ID")

    # YouTube
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID")

    # ── 평가 기준 (4단계: 최상/상/중/하) ──
    # 평가1: 조회수 (바이럴)
    VIEWS_BEST = int(os.getenv("VIEWS_BEST", "10000"))     # 최상: 알고리즘 노출 성공
    VIEWS_HIGH = int(os.getenv("VIEWS_HIGH", "3000"))      # 상: 탐색 탭 노출 시작
    VIEWS_MID = int(os.getenv("VIEWS_MID", "1000"))        # 중: 팔로워 및 해시태그 유입
    # 하: 1000 미만 → 노출 실패

    # 평가2: 참여율 (컨텐츠 매력도)
    ENGAGEMENT_BEST = float(os.getenv("ENGAGEMENT_BEST", "5.0"))   # 최상: 찐팬 형성
    ENGAGEMENT_HIGH = float(os.getenv("ENGAGEMENT_HIGH", "3.0"))   # 상: 타겟 안정적 반응
    ENGAGEMENT_MID = float(os.getenv("ENGAGEMENT_MID", "1.0"))     # 중: 나쁘지 않음
    # 하: 1% 미만 → 이탈률 높음

    # ── 총평 매트릭스 (조회수-참여율 조합 → 액션플랜) ──
    RATING_ACTION_MAP = {
        # (조회수등급, 참여율등급): (이모지, 총평명, 액션)
        ("최상", "최상"): ("👑", "최상-최상 (광고집행!!)", "반응/노출 완벽함. 유료 광고 태워서 매출 극대화."),
        ("최상", "상"):   ("🔥", "최상-상 (상단고정)", "우리 브랜드를 대표하는 효자 컨텐츠. 프로필 상단 고정."),
        ("상", "최상"):   ("💎", "상-최상 (구매전환)", "찐팬 반응 폭발. 공구/이벤트 진행 시 전환율 높음."),
        ("상", "상"):     ("⭐", "상-상 (모범답안)", "우리 브랜드 컨텐츠의 '정석'. 이 톤앤매너 유지."),
        ("중", "최상"):   ("🔍", "중-최상 (재업로드)", "컨텐츠는 완벽함. 시기만 잘 맞춰서 그대로 재업로드."),
        ("하", "최상"):   ("🤯", "하-최상 (썸네일교체)", "클릭을 안 해서 못 본 것. 썸네일/제목만 자극적으로 수정 후 재업로드."),
        ("하", "상"):     ("🎨", "하-상 (포장실패)", "기획 의도는 좋으나 첫인상이 약함. 도입부/커버 보완 필요."),
        ("최상", "하"):   ("🚨", "최상-하 (내실부족)", "어그로는 성공했으나 알맹이가 없음. 다음 기획 시 내용 보강 필수."),
        ("상", "하"):     ("📋", "상-하 (이탈원인체크)", "초반 이탈이 높음. 영상 길이가 너무 길거나 지루하지 않은지 점검."),
        ("중", "하"):     ("💤", "중-하 (지루함)", "임팩트가 약함. 숏폼 호흡을 더 빠르게 가져갈 것."),
        ("최상", "중"):   ("🎉", "최상-중 (대중성확보)", "반응은 평범하지만 널리 퍼짐. 브랜드 인지도용으로 적합."),
        ("중", "상"):     ("🌟", "중-상 (매니아층)", "소수지만 확실한 타겟층이 존재함. 소통 강화."),
        ("상", "중"):     ("🙂", "상-중", "특이사항 없는 평타 컨텐츠."),
        ("중", "중"):     ("😐", "중-중", "특이사항 없는 평타 컨텐츠."),
        ("하", "중"):     ("⛏️", "하-중 (개선필요)", "주제 선정부터 다시 고민 필요."),
        ("하", "하"):     ("🐱", "하-하 (개선시급)", "유입도 반응도 없음. 미련 갖지 말고 빠르게 폐기 후 다음 기획 집중."),
    }

    # ── 채널/유형 매핑 (6가지) ──
    CHANNEL_TYPES = {
        "instagram_feed": "인스타그램 피드",
        "instagram_reels": "인스타그램 릴스",
        "youtube_long": "유튜브 롱폼",
        "youtube_shorts": "유튜브 숏츠",
        "tiktok_feed": "틱톡 피드",
        "tiktok_reels": "틱톡 릴스",
    }

    # ── 경로(계정) 매핑 ──
    ROUTE_MAP = {
        "official": "빌딘 오피셜",
        "magazine": "빌딘 매거진",
    }

    # ── 운영 계정 정보 ──
    ACCOUNTS = {
        "instagram_official": "buildin_official",
        "instagram_magazine": "buildin_mag",
        "youtube": "@buildin_kr",
        "tiktok": "buildin_official",
    }

    @classmethod
    def validate(cls):
        """필수 설정값 검증"""
        required = [
            ("NOTION_API_TOKEN", cls.NOTION_API_TOKEN),
            ("NOTION_CONTENT_DB_ID", cls.NOTION_CONTENT_DB_ID),
        ]
        missing = [name for name, val in required if not val]
        if missing:
            raise ValueError(f"필수 환경변수가 설정되지 않았습니다: {', '.join(missing)}")
        return True
