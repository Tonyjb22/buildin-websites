"""
빌딘 컨텐츠 자동화 시스템 - YouTube Analytics 수집기
채널 소유자 OAuth 인증을 통해 상세 분석 데이터를 수집합니다.

수집 가능 데이터:
- 영상별 시청 지속시간 (averageViewDuration)
- 시청자 유지율 (audienceWatchRatio) - 어느 구간에서 이탈하는지
- 트래픽 소스 (검색, 추천, 외부 등)
- 시청자 연령/성별 분포
- 구독자 vs 비구독자 비율
"""
import requests
from datetime import datetime, timedelta
from config import Config


class YouTubeAnalyticsCollector:
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"

    def __init__(self):
        self.client_id = Config.YOUTUBE_OAUTH_CLIENT_ID
        self.client_secret = Config.YOUTUBE_OAUTH_CLIENT_SECRET
        self.refresh_token = Config.YOUTUBE_OAUTH_REFRESH_TOKEN
        self.access_token = None

    def _get_access_token(self):
        """Refresh token으로 access token 발급"""
        if self.access_token:
            return self.access_token

        resp = requests.post(self.TOKEN_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        })

        if resp.status_code != 200:
            print(f"❌ OAuth 토큰 갱신 실패 [{resp.status_code}]: {resp.text[:300]}")
            resp.raise_for_status()

        self.access_token = resp.json()["access_token"]
        return self.access_token

    def _query(self, params):
        """YouTube Analytics API 쿼리"""
        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params["ids"] = "channel==MINE"

        resp = requests.get(self.ANALYTICS_URL, headers=headers, params=params)
        if resp.status_code != 200:
            print(f"❌ Analytics API 오류 [{resp.status_code}]: {resp.text[:300]}")
            resp.raise_for_status()

        return resp.json()

    # ═══════════════════════════════════════
    # 영상별 기본 분석 데이터
    # ═══════════════════════════════════════

    def get_video_analytics(self, video_id, start_date, end_date):
        """개별 영상의 상세 분석 데이터
        
        Returns:
            dict: {
                views, estimatedMinutesWatched, averageViewDuration,
                averageViewPercentage, likes, comments, shares,
                subscribersGained, subscribersLost
            }
        """
        data = self._query({
            "startDate": start_date,
            "endDate": end_date,
            "metrics": ",".join([
                "views",
                "estimatedMinutesWatched",
                "averageViewDuration",
                "averageViewPercentage",
                "likes",
                "comments",
                "shares",
                "subscribersGained",
                "subscribersLost",
            ]),
            "filters": f"video=={video_id}",
        })

        rows = data.get("rows", [])
        headers = [col["name"] for col in data.get("columnHeaders", [])]

        if not rows:
            return None

        result = dict(zip(headers, rows[0]))
        return result

    # ═══════════════════════════════════════
    # 트래픽 소스 (어디서 유입되었는지)
    # ═══════════════════════════════════════

    def get_traffic_sources(self, video_id, start_date, end_date):
        """영상별 트래픽 소스 분석
        
        Returns:
            list[dict]: [
                {"source": "SUGGESTED", "views": 500, "pct": 45.2},
                {"source": "YT_SEARCH", "views": 300, "pct": 27.1},
                ...
            ]
        """
        data = self._query({
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "insightTrafficSourceType",
            "metrics": "views,estimatedMinutesWatched",
            "filters": f"video=={video_id}",
            "sort": "-views",
        })

        rows = data.get("rows", [])
        total_views = sum(row[1] for row in rows) if rows else 0

        sources = []
        source_names = {
            "SUGGESTED": "추천 동영상",
            "YT_SEARCH": "YouTube 검색",
            "EXT_URL": "외부 웹사이트/앱",
            "BROWSE": "탐색 기능",
            "NOTIFICATION": "알림",
            "SHORTS": "Shorts 피드",
            "NO_LINK_OTHER": "기타",
            "CHANNEL": "채널 페이지",
            "PLAYLIST": "재생목록",
            "END_SCREEN": "최종 화면",
            "SUBSCRIBER": "구독 피드",
            "HASHTAGS": "해시태그",
            "ANNOTATION": "카드/주석",
        }

        for row in rows:
            source_key = row[0]
            views = row[1]
            pct = round(views / total_views * 100, 1) if total_views > 0 else 0
            sources.append({
                "source_key": source_key,
                "source": source_names.get(source_key, source_key),
                "views": views,
                "watch_minutes": round(row[2], 1),
                "pct": pct,
            })

        return sources

    # ═══════════════════════════════════════
    # 시청자 연령/성별 분포
    # ═══════════════════════════════════════

    def get_demographics(self, video_id, start_date, end_date):
        """영상별 시청자 연령/성별 분포
        
        Returns:
            dict: {
                "age_groups": {"18-24": 32.5, "25-34": 28.1, ...},
                "gender": {"male": 45.2, "female": 54.8},
                "top_age_group": "18-24",
                "top_gender": "female"
            }
        """
        data = self._query({
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "ageGroup,gender",
            "metrics": "viewerPercentage",
            "filters": f"video=={video_id}",
        })

        rows = data.get("rows", [])
        
        age_groups = {}
        gender = {"male": 0, "female": 0}

        for row in rows:
            age = row[0]  # e.g., "age18-24"
            gen = row[1]  # "male" or "female"
            pct = row[2]

            # 연령대 정리
            age_label = age.replace("age", "")
            if age_label not in age_groups:
                age_groups[age_label] = 0
            age_groups[age_label] += pct

            # 성별 합산
            if gen in gender:
                gender[gen] += pct

        top_age = max(age_groups, key=age_groups.get) if age_groups else "N/A"
        top_gender_key = max(gender, key=gender.get) if gender else "N/A"
        top_gender_label = "남성" if top_gender_key == "male" else "여성"

        return {
            "age_groups": {k: round(v, 1) for k, v in sorted(age_groups.items())},
            "gender": {k: round(v, 1) for k, v in gender.items()},
            "top_age_group": top_age,
            "top_gender": top_gender_label,
        }

    # ═══════════════════════════════════════
    # 시청자 유지율 (이탈 구간 분석)
    # ═══════════════════════════════════════

    def get_audience_retention(self, video_id, start_date, end_date):
        """영상별 시청자 유지율 곡선
        
        Returns:
            dict: {
                "retention_data": [(0, 100.0), (10, 85.2), (20, 72.1), ...],
                "drop_points": [
                    {"position_pct": 15, "retention": 62.0, "drop": 23.2, "severity": "심각"},
                ],
                "avg_view_pct": 45.2,
                "summary": "15% 지점에서 23.2% 급감 (심각)"
            }
        """
        # audienceWatchRatio는 0~100% 구간별 유지율
        try:
            data = self._query({
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": "elapsedVideoTimeRatio",
                "metrics": "audienceWatchRatio",
                "filters": f"video=={video_id}",
            })
        except Exception as e:
            print(f"   ⚠️ 유지율 데이터 없음: {e}")
            return None

        rows = data.get("rows", [])
        if not rows:
            return None

        # 유지율 데이터 정리 (0~100% 구간)
        retention_data = []
        for row in rows:
            position_pct = round(row[0] * 100, 1)
            retention = round(row[1] * 100, 1)
            retention_data.append((position_pct, retention))

        # 이탈 구간 감지 (5% 이상 급감 지점)
        drop_points = []
        for i in range(1, len(retention_data)):
            prev_ret = retention_data[i-1][1]
            curr_ret = retention_data[i][1]
            drop = round(prev_ret - curr_ret, 1)

            if drop >= 5:  # 5% 이상 급감
                severity = "심각" if drop >= 15 else "주의" if drop >= 10 else "경미"
                drop_points.append({
                    "position_pct": retention_data[i][0],
                    "retention": curr_ret,
                    "drop": drop,
                    "severity": severity,
                })

        # 평균 시청 비율
        avg_retention = round(sum(r[1] for r in retention_data) / len(retention_data), 1) if retention_data else 0

        # 요약 생성
        summary_parts = []
        for dp in sorted(drop_points, key=lambda x: -x["drop"])[:3]:
            summary_parts.append(f"{dp['position_pct']}% 지점에서 {dp['drop']}% 급감 ({dp['severity']})")
        
        summary = " / ".join(summary_parts) if summary_parts else "특이 이탈 구간 없음"

        return {
            "retention_data": retention_data,
            "drop_points": drop_points,
            "avg_view_pct": avg_retention,
            "summary": summary,
        }

    # ═══════════════════════════════════════
    # 구독자 vs 비구독자
    # ═══════════════════════════════════════

    def get_subscriber_status(self, video_id, start_date, end_date):
        """구독자/비구독자 시청 비율
        
        Returns:
            dict: {"subscribed": 35.2, "unsubscribed": 64.8}
        """
        data = self._query({
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": "subscribedStatus",
            "metrics": "views",
            "filters": f"video=={video_id}",
        })

        rows = data.get("rows", [])
        total = sum(row[1] for row in rows) if rows else 0

        result = {"subscribed": 0, "unsubscribed": 0}
        for row in rows:
            status = row[0]  # "SUBSCRIBED" or "UNSUBSCRIBED"
            views = row[1]
            pct = round(views / total * 100, 1) if total > 0 else 0
            if status == "SUBSCRIBED":
                result["subscribed"] = pct
            else:
                result["unsubscribed"] = pct

        return result

    # ═══════════════════════════════════════
    # 통합 분석 (영상 1개에 대한 전체 데이터)
    # ═══════════════════════════════════════

    def get_full_video_analysis(self, video_id, upload_date):
        """영상 하나에 대한 전체 Analytics 데이터 수집
        
        Args:
            video_id: YouTube 영상 ID
            upload_date: 업로드 날짜 (YYYY-MM-DD)
        
        Returns:
            dict: 모든 분석 데이터 통합
        """
        # 분석 기간: 업로드일 ~ +6일
        start_date = upload_date
        end_dt = datetime.strptime(upload_date, "%Y-%m-%d") + timedelta(days=6)
        end_date = end_dt.strftime("%Y-%m-%d")

        print(f"   📊 Analytics 수집: {video_id} ({start_date} ~ {end_date})")

        result = {
            "video_id": video_id,
            "period": f"{start_date} ~ {end_date}",
        }

        # 기본 지표
        try:
            basic = self.get_video_analytics(video_id, start_date, end_date)
            if basic:
                result["basic"] = basic
                print(f"      ✅ 기본 지표 (평균 시청: {basic.get('averageViewDuration', 0)}초, "
                      f"시청 비율: {basic.get('averageViewPercentage', 0):.1f}%)")
        except Exception as e:
            print(f"      ⚠️ 기본 지표 실패: {e}")

        # 트래픽 소스
        try:
            traffic = self.get_traffic_sources(video_id, start_date, end_date)
            if traffic:
                result["traffic_sources"] = traffic
                top_source = traffic[0] if traffic else {}
                print(f"      ✅ 트래픽 소스 (1위: {top_source.get('source', 'N/A')} {top_source.get('pct', 0)}%)")
        except Exception as e:
            print(f"      ⚠️ 트래픽 소스 실패: {e}")

        # 시청자 연령/성별
        try:
            demo = self.get_demographics(video_id, start_date, end_date)
            if demo and demo.get("age_groups"):
                result["demographics"] = demo
                print(f"      ✅ 인구통계 (주요: {demo['top_gender']} {demo['top_age_group']}세)")
        except Exception as e:
            print(f"      ⚠️ 인구통계 실패: {e}")

        # 시청자 유지율
        try:
            retention = self.get_audience_retention(video_id, start_date, end_date)
            if retention:
                result["retention"] = retention
                print(f"      ✅ 유지율 (평균: {retention['avg_view_pct']}%, 이탈: {retention['summary']})")
        except Exception as e:
            print(f"      ⚠️ 유지율 실패: {e}")

        # 구독자 비율
        try:
            subs = self.get_subscriber_status(video_id, start_date, end_date)
            if subs:
                result["subscriber_status"] = subs
                print(f"      ✅ 구독자: {subs['subscribed']}% / 비구독자: {subs['unsubscribed']}%")
        except Exception as e:
            print(f"      ⚠️ 구독자 비율 실패: {e}")

        return result


def test_analytics_connection():
    """YouTube Analytics API 연결 테스트"""
    try:
        analytics = YouTubeAnalyticsCollector()
        token = analytics._get_access_token()
        if token:
            print(f"✅ YouTube Analytics 연결 성공 (토큰 발급 완료)")
            
            # 최근 7일 채널 전체 통계 테스트
            today = datetime.now().strftime("%Y-%m-%d")
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            data = analytics._query({
                "startDate": week_ago,
                "endDate": today,
                "metrics": "views,estimatedMinutesWatched,averageViewDuration",
            })
            
            rows = data.get("rows", [])
            if rows:
                print(f"   최근 7일: 조회 {rows[0][0]}회, 시청 {round(rows[0][1])}분, 평균 {rows[0][2]}초")
        else:
            print("❌ YouTube Analytics: 토큰 발급 실패")
    except Exception as e:
        print(f"❌ YouTube Analytics 연결 실패: {e}")
