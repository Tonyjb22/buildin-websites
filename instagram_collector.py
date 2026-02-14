"""
빌딘 컨텐츠 자동화 시스템 - Instagram 데이터 수집기
Instagram Graph API를 사용하여 비즈니스 계정의 미디어 데이터를 수집합니다.
"""
import requests
from datetime import datetime, timedelta
from config import Config


class InstagramCollector:
    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self):
        self.access_token = Config.INSTAGRAM_ACCESS_TOKEN
        self.account_ids = {}
        
        if Config.INSTAGRAM_BUSINESS_ACCOUNT_ID:
            self.account_ids["official"] = Config.INSTAGRAM_BUSINESS_ACCOUNT_ID
        if Config.INSTAGRAM_MAGAZINE_ACCOUNT_ID:
            self.account_ids["magazine"] = Config.INSTAGRAM_MAGAZINE_ACCOUNT_ID

    def _get(self, endpoint, params=None):
        """Instagram Graph API GET 요청"""
        if params is None:
            params = {}
        params["access_token"] = self.access_token
        
        resp = requests.get(f"{self.BASE_URL}{endpoint}", params=params)
        if resp.status_code != 200:
            print(f"❌ Instagram API 오류 [{resp.status_code}]: {resp.text[:300]}")
        resp.raise_for_status()
        return resp.json()

    def get_recent_media(self, account_id, limit=50):
        """최근 미디어 목록 조회"""
        data = self._get(f"/{account_id}/media", {
            "fields": "id,caption,media_type,media_url,permalink,timestamp,thumbnail_url",
            "limit": limit,
        })
        return data.get("data", [])

    def get_media_insights(self, media_id, media_type="CAROUSEL_ALBUM"):
        """개별 미디어의 인사이트(성과 지표) 조회"""
        # 미디어 타입에 따라 사용 가능한 메트릭이 다름
        if media_type == "VIDEO" or media_type == "REELS":
            metrics = "plays,likes,comments,shares,saved,reach"
        elif media_type == "CAROUSEL_ALBUM":
            metrics = "impressions,likes,comments,shares,saved,reach"
        else:  # IMAGE
            metrics = "impressions,likes,comments,shares,saved,reach"

        try:
            data = self._get(f"/{media_id}/insights", {"metric": metrics})
            insights = {}
            for item in data.get("data", []):
                name = item["name"]
                value = item["values"][0]["value"] if item.get("values") else 0
                insights[name] = value
            return insights
        except Exception as e:
            print(f"⚠️ 인사이트 조회 실패 (media_id={media_id}): {e}")
            return {}

    def get_media_basic_metrics(self, media_id):
        """기본 메트릭 조회 (인사이트 대신 사용 가능)"""
        data = self._get(f"/{media_id}", {
            "fields": "like_count,comments_count,media_type,permalink,timestamp"
        })
        return data

    def collect_weekly_data(self, days_back=7):
        """최근 N일간의 모든 계정 데이터 수집
        
        Returns:
            list[dict]: 수집된 컨텐츠 데이터 리스트
        """
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        all_content = []

        for account_key, account_id in self.account_ids.items():
            route = Config.ROUTE_MAP.get(account_key, "빌딘 오피셜")
            print(f"📸 Instagram [{route}] 데이터 수집 중...")
            
            media_list = self.get_recent_media(account_id)
            
            for media in media_list:
                # 날짜 필터링
                timestamp = media.get("timestamp", "")
                if timestamp:
                    media_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    if media_date.replace(tzinfo=None) < cutoff:
                        continue

                media_id = media["id"]
                media_type = media.get("media_type", "IMAGE")
                permalink = media.get("permalink", "")

                # 채널/유형 결정
                if media_type == "VIDEO":
                    channel_type = "인스타그램 릴스"
                elif media_type == "CAROUSEL_ALBUM":
                    channel_type = "인스타그램 피드"
                else:
                    channel_type = "인스타그램 피드"

                # 인사이트 수집
                insights = self.get_media_insights(media_id, media_type)
                basic = self.get_media_basic_metrics(media_id)

                # 조회수 결정 (릴스 = plays, 피드 = impressions)
                views = insights.get("plays") or insights.get("impressions") or insights.get("reach", 0)

                content = {
                    "upload_date": timestamp[:10],  # YYYY-MM-DD
                    "route": route,
                    "content_link": permalink,
                    "channel_type": channel_type,
                    "views": views,
                    "likes": insights.get("likes") or basic.get("like_count", 0),
                    "saves": insights.get("saved", 0),
                    "comments": insights.get("comments") or basic.get("comments_count", 0),
                    "shares": insights.get("shares", 0),
                    "platform": "instagram",
                }
                all_content.append(content)
                print(f"  ✅ {permalink[:50]}... (조회: {views}, 좋아요: {content['likes']})")

        print(f"📸 Instagram 총 {len(all_content)}개 컨텐츠 수집 완료")
        return all_content


def test_instagram_connection():
    """Instagram API 연결 테스트"""
    collector = InstagramCollector()
    for key, acc_id in collector.account_ids.items():
        try:
            data = collector._get(f"/{acc_id}", {"fields": "name,username,media_count"})
            print(f"✅ Instagram [{key}] 연결 성공: @{data.get('username')} (미디어: {data.get('media_count')}개)")
        except Exception as e:
            print(f"❌ Instagram [{key}] 연결 실패: {e}")


if __name__ == "__main__":
    test_instagram_connection()
