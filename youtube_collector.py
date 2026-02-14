"""
빌딘 컨텐츠 자동화 시스템 - YouTube 데이터 수집기
YouTube Data API v3를 사용하여 채널의 동영상 데이터를 수집합니다.
"""
import requests
from datetime import datetime, timedelta
from config import Config


class YouTubeCollector:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self):
        self.api_key = Config.YOUTUBE_API_KEY
        self.channel_id = Config.YOUTUBE_CHANNEL_ID

    def _get(self, endpoint, params=None):
        """YouTube Data API GET 요청"""
        if params is None:
            params = {}
        params["key"] = self.api_key

        resp = requests.get(f"{self.BASE_URL}/{endpoint}", params=params)
        if resp.status_code != 200:
            print(f"❌ YouTube API 오류 [{resp.status_code}]: {resp.text[:300]}")
        resp.raise_for_status()
        return resp.json()

    def get_recent_videos(self, days_back=7, max_results=50):
        """최근 N일간 업로드된 동영상 검색"""
        published_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z"

        data = self._get("search", {
            "channelId": self.channel_id,
            "part": "snippet",
            "type": "video",
            "order": "date",
            "publishedAfter": published_after,
            "maxResults": max_results,
        })

        videos = []
        for item in data.get("items", []):
            video_id = item["id"]["videoId"]
            snippet = item["snippet"]
            videos.append({
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "published_at": snippet.get("publishedAt", ""),
                "description": snippet.get("description", ""),
            })

        return videos

    def get_video_details(self, video_ids):
        """동영상 상세 정보 (통계 포함) 조회"""
        if not video_ids:
            return []

        # 최대 50개씩 배치 처리
        all_details = []
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            data = self._get("videos", {
                "id": ",".join(batch),
                "part": "snippet,statistics,contentDetails",
            })
            all_details.extend(data.get("items", []))

        return all_details

    def _parse_duration(self, duration_str):
        """ISO 8601 duration을 초 단위로 변환 (예: PT1M30S → 90)"""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    def _is_shorts(self, duration_seconds):
        """숏츠 여부 판단 (60초 이하)"""
        return duration_seconds <= 60

    def collect_weekly_data(self, days_back=7):
        """최근 N일간의 유튜브 데이터 수집
        
        Returns:
            list[dict]: 수집된 컨텐츠 데이터 리스트
        """
        print(f"📺 YouTube 데이터 수집 중...")

        # 1. 최근 동영상 검색
        recent_videos = self.get_recent_videos(days_back=days_back)
        if not recent_videos:
            print("📺 YouTube: 최근 업로드된 동영상이 없습니다.")
            return []

        # 2. 상세 정보 조회
        video_ids = [v["video_id"] for v in recent_videos]
        details = self.get_video_details(video_ids)

        all_content = []
        for detail in details:
            video_id = detail["id"]
            stats = detail.get("statistics", {})
            content_details = detail.get("contentDetails", {})
            snippet = detail.get("snippet", {})

            # 숏츠 여부 판단
            duration = self._parse_duration(content_details.get("duration", "PT0S"))
            is_shorts = self._is_shorts(duration)

            # 채널 유형 결정
            channel_type = "유튜브 숏츠" if is_shorts else "유튜브 롱폼"

            # 링크 생성
            if is_shorts:
                link = f"youtube.com/sho...{video_id[:6]}"
                full_link = f"https://www.youtube.com/shorts/{video_id}"
            else:
                link = f"youtube.com/wat...{video_id[:6]}"
                full_link = f"https://www.youtube.com/watch?v={video_id}"

            published = snippet.get("publishedAt", "")[:10]

            content = {
                "upload_date": published,
                "route": "빌딘 오피셜",  # 기본값, 필요시 수정
                "content_link": full_link,
                "channel_type": channel_type,
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "saves": 0,  # YouTube API에서 저장 수 미제공
                "comments": int(stats.get("commentCount", 0)),
                "shares": 0,  # YouTube API에서 공유 수 미제공 (Analytics API 필요)
                "platform": "youtube",
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "duration_seconds": duration,
            }
            all_content.append(content)
            print(f"  ✅ [{channel_type}] {snippet.get('title', '')[:30]}... (조회: {content['views']})")

        print(f"📺 YouTube 총 {len(all_content)}개 컨텐츠 수집 완료")
        return all_content


def test_youtube_connection():
    """YouTube API 연결 테스트"""
    collector = YouTubeCollector()
    try:
        data = collector._get("channels", {
            "id": collector.channel_id,
            "part": "snippet,statistics",
        })
        items = data.get("items", [])
        if items:
            ch = items[0]
            name = ch["snippet"]["title"]
            subs = ch["statistics"].get("subscriberCount", "비공개")
            videos = ch["statistics"].get("videoCount", 0)
            print(f"✅ YouTube 연결 성공: {name} (구독자: {subs}, 동영상: {videos}개)")
        else:
            print("❌ YouTube: 채널을 찾을 수 없습니다. CHANNEL_ID를 확인하세요.")
    except Exception as e:
        print(f"❌ YouTube 연결 실패: {e}")


if __name__ == "__main__":
    test_youtube_connection()
