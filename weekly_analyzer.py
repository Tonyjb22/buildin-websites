"""
빌딘 컨텐츠 자동화 시스템 - 주간 분석 생성기
매주 컨텐츠 성과를 분석하고 Notion 페이지로 리포트를 생성합니다.
"""
from datetime import datetime, timedelta
from collections import defaultdict
from config import Config
from notion_client import NotionClient, parse_notion_content


class WeeklyAnalyzer:
    def __init__(self):
        self.notion = NotionClient()
        self.analytics = None
        
        # YouTube Analytics 사용 가능 여부 확인
        if Config.YOUTUBE_OAUTH_REFRESH_TOKEN:
            try:
                from youtube_analytics import YouTubeAnalyticsCollector
                self.analytics = YouTubeAnalyticsCollector()
                print("📊 YouTube Analytics 연동 활성화")
            except Exception as e:
                print(f"⚠️ YouTube Analytics 비활성: {e}")
        else:
            print("⏭️ YouTube Analytics 미설정 - 기본 분석만 실행")

    def get_week_range(self, target_date=None):
        """주차 날짜 범위 계산 (월~일 기준)"""
        if target_date is None:
            target_date = datetime.now()
        
        days_since_monday = target_date.weekday()
        last_monday = target_date - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        
        return {
            "start": last_monday.strftime("%Y-%m-%d"),
            "end": last_sunday.strftime("%Y-%m-%d"),
            "label": f"{last_monday.month}/{last_monday.day}-{last_sunday.month}/{last_sunday.day}",
            "start_dt": last_monday,
            "end_dt": last_sunday,
        }

    def get_prev_week_range(self, target_date=None):
        """전전주 날짜 범위"""
        if target_date is None:
            target_date = datetime.now()
        days_since_monday = target_date.weekday()
        prev_monday = target_date - timedelta(days=days_since_monday + 14)
        prev_sunday = prev_monday + timedelta(days=6)
        return {
            "start": prev_monday.strftime("%Y-%m-%d"),
            "end": prev_sunday.strftime("%Y-%m-%d"),
            "label": f"{prev_monday.month}/{prev_monday.day}-{prev_sunday.month}/{prev_sunday.day}",
        }

    def analyze_content_list(self, content_list):
        """컨텐츠 리스트 분석 - 플랫폼별 통계 산출"""
        stats = {
            "total": {"count": 0, "views": 0, "likes": 0, "saves": 0, "comments": 0, "shares": 0},
            "인스타": {"count": 0, "views": 0, "likes": 0, "saves": 0, "comments": 0, "shares": 0},
            "유튜브": {"count": 0, "views": 0, "likes": 0, "saves": 0, "comments": 0, "shares": 0},
            "틱톡": {"count": 0, "views": 0, "likes": 0, "saves": 0, "comments": 0, "shares": 0},
        }

        top_content = []

        for item in content_list:
            ch = item.get("channel_type", "")
            
            if "인스타" in ch:
                platform = "인스타"
            elif "유튜브" in ch:
                platform = "유튜브"
            elif "틱톡" in ch:
                platform = "틱톡"
            else:
                platform = None

            stats["total"]["count"] += 1
            stats["total"]["views"] += item.get("views", 0)
            stats["total"]["likes"] += item.get("likes", 0)
            stats["total"]["saves"] += item.get("saves", 0)
            stats["total"]["comments"] += item.get("comments", 0)
            stats["total"]["shares"] += item.get("shares", 0)

            if platform and platform in stats:
                stats[platform]["count"] += 1
                stats[platform]["views"] += item.get("views", 0)
                stats[platform]["likes"] += item.get("likes", 0)
                stats[platform]["saves"] += item.get("saves", 0)
                stats[platform]["comments"] += item.get("comments", 0)
                stats[platform]["shares"] += item.get("shares", 0)

            top_content.append(item)

        for key in stats:
            count = stats[key]["count"]
            stats[key]["avg_views"] = round(stats[key]["views"] / count) if count > 0 else 0

        for key in stats:
            views = stats[key]["views"]
            if views > 0:
                engagement = stats[key]["likes"] + stats[key]["saves"] + stats[key]["comments"] + stats[key]["shares"]
                stats[key]["engagement_rate"] = round(engagement / views * 100, 2)
            else:
                stats[key]["engagement_rate"] = 0

        top_content.sort(key=lambda x: x.get("views", 0), reverse=True)

        return stats, top_content[:5]

    def calculate_engagement_d6(self, item):
        """D+6 참여율 계산"""
        channel_type = item.get("channel_type", "")
        is_shorts = channel_type == "유튜브 숏츠"
        views = item.get("views", 0)
        
        if views == 0:
            return None

        likes = max(0, (item.get("likes", 0) - 1) if is_shorts else (item.get("likes", 0) - 3))
        saves = 0 if is_shorts else max(0, item.get("saves", 0) - 3)
        shares = 0 if is_shorts else max(0, item.get("shares", 0) - 3)
        comments = max(0, item.get("comments", 0) * 0.5)

        rate = (likes + saves + shares + comments) / views * 100
        return round(rate, 2)

    def rate_views(self, views):
        """조회수 평가 (4단계)"""
        if views >= Config.VIEWS_BEST:
            return "최상", "🔥", "알고리즘 노출 성공. 외부 유입 폭발."
        elif views >= Config.VIEWS_HIGH:
            return "상", "⭐", "탐색 탭 노출 시작. 유의미한 도달."
        elif views >= Config.VIEWS_MID:
            return "중", "😐", "팔로워 및 해시태그 유입. (평타)"
        else:
            return "하", "👎", "노출 실패."

    def rate_engagement(self, engagement_rate):
        """참여율 평가 (4단계)"""
        if engagement_rate >= Config.ENGAGEMENT_BEST:
            return "최상", "🔥", "찐팬 형성. 컨텐츠 매력도 매우 높음."
        elif engagement_rate >= Config.ENGAGEMENT_HIGH:
            return "상", "⭐", "우리 타겟이 선호하는 안정적 반응."
        elif engagement_rate >= Config.ENGAGEMENT_MID:
            return "중", "😐", "나쁘지 않음."
        else:
            return "하", "👎", "이탈률 높음. 내용 보완 필요."

    def get_overall_rating(self, views_grade, eng_grade):
        """총평 산출"""
        key = (views_grade, eng_grade)
        if key in Config.RATING_ACTION_MAP:
            emoji, label, action = Config.RATING_ACTION_MAP[key]
            return emoji, label, action
        return "😐", f"{views_grade}-{eng_grade}", "특이사항 없음."

    def rate_single_content(self, item):
        """개별 컨텐츠 평가"""
        views = item.get("views", 0)
        engagement = self.calculate_engagement_d6(item)
        
        views_grade, _, _ = self.rate_views(views)
        eng_grade = "하"
        if engagement is not None:
            eng_grade, _, _ = self.rate_engagement(engagement)
        
        emoji, label, action = self.get_overall_rating(views_grade, eng_grade)
        
        return {
            "views_grade": views_grade,
            "engagement_grade": eng_grade,
            "engagement_value": engagement,
            "overall_emoji": emoji,
            "overall_label": label,
            "action": action,
        }

    def compare_weeks(self, this_week_stats, prev_week_stats):
        """전주 대비 변화 분석"""
        comparisons = {}
        for platform in ["total", "인스타", "유튜브", "틱톡"]:
            this_w = this_week_stats.get(platform, {})
            prev_w = prev_week_stats.get(platform, {})
            
            comparisons[platform] = {}
            for metric in ["views", "avg_views", "count", "engagement_rate"]:
                this_val = this_w.get(metric, 0)
                prev_val = prev_w.get(metric, 0)
                
                if prev_val > 0:
                    change_pct = round((this_val - prev_val) / prev_val * 100, 1)
                else:
                    change_pct = 100 if this_val > 0 else 0

                if this_val > prev_val:
                    direction = "증가"
                elif this_val < prev_val:
                    direction = "감소"
                else:
                    direction = "유지"

                comparisons[platform][metric] = {
                    "this_week": this_val,
                    "prev_week": prev_val,
                    "change_pct": change_pct,
                    "direction": direction,
                }

        return comparisons

    def generate_analysis_blocks(self, week_range, stats, top_content, comparisons, prev_week_range):
        """Notion 페이지용 분석 블록 생성"""
        blocks = []
        nc = NotionClient

        # ── 헤더 ──
        blocks.append(nc.callout_block(
            f"📊 {week_range['label']} 주간 컨텐츠 분석 리포트\n"
            f"자동 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            emoji="📊"
        ))
        blocks.append(nc.divider_block())

        # ── 전주 대비 요약 ──
        blocks.append(nc.heading_block("📈 전주 대비 요약", level=2))
        
        summary_rows = [
            ["구분", "컨텐츠 수", "총 조회수", "증감", "평균 조회수", "증감", "참여율", "증감"]
        ]
        for platform_label, platform_key in [("총", "total"), ("인스타", "인스타"), ("유튜브", "유튜브"), ("틱톡", "틱톡")]:
            s = stats.get(platform_key, {})
            c = comparisons.get(platform_key, {})
            
            views_dir = c.get("views", {}).get("direction", "-")
            avg_dir = c.get("avg_views", {}).get("direction", "-")
            eng_dir = c.get("engagement_rate", {}).get("direction", "-")
            
            summary_rows.append([
                platform_label,
                str(s.get("count", 0)),
                f"{s.get('views', 0):,}",
                views_dir,
                f"{s.get('avg_views', 0):,}",
                avg_dir,
                f"{s.get('engagement_rate', 0)}%",
                eng_dir,
            ])

        blocks.append(nc.table_block(summary_rows))

        # ── 주요 인사이트 ──
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("💡 주요 인사이트", level=2))

        insights = self._generate_insights(stats, comparisons)
        for insight in insights:
            blocks.append(nc.bulleted_list_block(insight))

        # ── 상위 컨텐츠 ──
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("🏆 상위 성과 컨텐츠 (조회수 기준 TOP 5)", level=2))

        if top_content:
            top_rows = [["순위", "채널", "링크", "조회수", "좋아요", "참여율"]]
            for i, item in enumerate(top_content, 1):
                eng = self.calculate_engagement_d6(item)
                eng_str = f"{eng}%" if eng is not None else "N/A"
                link = item.get("content_link", "")
                if len(link) > 40:
                    link = link[:40] + "..."
                
                top_rows.append([
                    str(i),
                    item.get("channel_type", ""),
                    link,
                    f"{item.get('views', 0):,}",
                    str(item.get("likes", 0)),
                    eng_str,
                ])
            blocks.append(nc.table_block(top_rows))

        # ── 플랫폼별 상세 분석 ──
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("📱 플랫폼별 상세 분석", level=2))

        for platform in ["인스타", "유튜브", "틱톡"]:
            s = stats.get(platform, {})
            if s["count"] == 0:
                continue
            
            emoji = "📸" if platform == "인스타" else "📺" if platform == "유튜브" else "🎵"
            blocks.append(nc.heading_block(f"{emoji} {platform}", level=3))
            
            detail_rows = [
                ["지표", "이번주", "전주", "변화"],
            ]
            c = comparisons.get(platform, {})
            
            detail_rows.append([
                "컨텐츠 수",
                str(s["count"]),
                str(c.get("count", {}).get("prev_week", 0)),
                c.get("count", {}).get("direction", "-"),
            ])
            detail_rows.append([
                "총 조회수",
                f"{s['views']:,}",
                f"{c.get('views', {}).get('prev_week', 0):,}",
                c.get("views", {}).get("direction", "-"),
            ])
            detail_rows.append([
                "평균 조회수",
                f"{s['avg_views']:,}",
                f"{c.get('avg_views', {}).get('prev_week', 0):,}",
                c.get("avg_views", {}).get("direction", "-"),
            ])
            detail_rows.append([
                "참여율",
                f"{s['engagement_rate']}%",
                f"{c.get('engagement_rate', {}).get('prev_week', 0)}%",
                c.get("engagement_rate", {}).get("direction", "-"),
            ])
            blocks.append(nc.table_block(detail_rows))

        # ── 종합 평가 ──
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("📋 종합 평가", level=2))

        total = stats["total"]
        views_grade, views_emoji, views_desc = self.rate_views(total["avg_views"])
        eng_grade, eng_emoji, eng_desc = self.rate_engagement(total["engagement_rate"])
        overall_emoji, overall_label, overall_action = self.get_overall_rating(views_grade, eng_grade)

        blocks.append(nc.callout_block(
            f"평가1 조회수 (바이럴): {views_emoji} {views_grade} (평균 {total['avg_views']:,}회) — {views_desc}\n"
            f"평가2 참여율 (매력도): {eng_emoji} {eng_grade} ({total['engagement_rate']}%) — {eng_desc}\n"
            f"총평: {overall_emoji} {overall_label}\n"
            f"→ 액션: {overall_action}",
            emoji="📋"
        ))

        # ── 개별 컨텐츠 총평 ──
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("🏷️ 컨텐츠별 총평 & 액션플랜", level=2))

        if top_content:
            rating_rows = [["채널/유형", "조회수", "참여율", "총평", "액션"]]
            for item in top_content:
                r = self.rate_single_content(item)
                rating_rows.append([
                    item.get("channel_type", ""),
                    f"{item.get('views', 0):,}",
                    f"{r['engagement_value']}%" if r['engagement_value'] is not None else "N/A",
                    f"{r['overall_emoji']} {r['overall_label']}",
                    r["action"][:30] + "..." if len(r["action"]) > 30 else r["action"],
                ])
            blocks.append(nc.table_block(rating_rows))

        # ── ✍️ 컨텐츠 상세 분석 ──
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("✍️ 컨텐츠 상세 분석", level=2))
        
        # 개별 컨텐츠 분석
        all_content_sorted = sorted(
            [item for item in top_content],
            key=lambda x: x.get("views", 0), reverse=True
        )
        for item in all_content_sorted:
            link = item.get("content_link", "")
            ch = item.get("channel_type", "")
            views = item.get("views", 0)
            video_id = None
            upload_date = item.get("upload_date", "")
            
            blocks.append(nc.heading_block(f"[{ch}] 조회 {views:,}회", level=3))
            blocks.append(nc.paragraph_block(f"🔗 {link}"))

            # YouTube Analytics 데이터 삽입
            if self.analytics and "youtube.com" in link and upload_date:
                # video_id 추출
                import re
                match = re.search(r'(?:v=|shorts/)([a-zA-Z0-9_-]{11})', link)
                if match:
                    video_id = match.group(1)
                    try:
                        analysis = self.analytics.get_full_video_analysis(video_id, upload_date)
                        
                        # 기본 지표
                        basic = analysis.get("basic")
                        if basic:
                            avg_dur = basic.get("averageViewDuration", 0)
                            avg_pct = basic.get("averageViewPercentage", 0)
                            mins_watched = basic.get("estimatedMinutesWatched", 0)
                            subs_gained = basic.get("subscribersGained", 0)
                            
                            blocks.append(nc.callout_block(
                                f"⏱ 평균 시청 시간: {avg_dur}초 ({avg_pct:.1f}%)\n"
                                f"📺 총 시청 시간: {round(mins_watched)}분\n"
                                f"👥 구독자 획득: +{subs_gained}명",
                                emoji="📊"
                            ))
                        
                        # 시청자 유지율 & 이탈 구간
                        retention = analysis.get("retention")
                        if retention:
                            ret_text = f"📉 평균 유지율: {retention['avg_view_pct']}%\n"
                            if retention.get("drop_points"):
                                ret_text += "⚠️ 이탈 구간:\n"
                                for dp in sorted(retention["drop_points"], key=lambda x: -x["drop"])[:3]:
                                    ret_text += f"  → {dp['position_pct']}% 지점: {dp['drop']}% 급감 ({dp['severity']})\n"
                            else:
                                ret_text += "✅ 특이 이탈 구간 없음"
                            blocks.append(nc.callout_block(ret_text, emoji="📉"))
                        
                        # 트래픽 소스
                        traffic = analysis.get("traffic_sources")
                        if traffic:
                            traffic_rows = [["소스", "조회수", "비율"]]
                            for src in traffic[:5]:
                                traffic_rows.append([
                                    src["source"],
                                    f"{src['views']:,}",
                                    f"{src['pct']}%",
                                ])
                            blocks.append(nc.paragraph_block("🔀 트래픽 소스", bold=True))
                            blocks.append(nc.table_block(traffic_rows))
                        
                        # 시청자 인구통계
                        demo = analysis.get("demographics")
                        if demo and demo.get("age_groups"):
                            demo_text = f"👤 주요 시청층: {demo['top_gender']} {demo['top_age_group']}세\n"
                            demo_text += "연령 분포: "
                            demo_text += " | ".join([f"{age}: {pct}%" for age, pct in demo["age_groups"].items()])
                            demo_text += f"\n성별: 남성 {demo['gender'].get('male', 0)}% / 여성 {demo['gender'].get('female', 0)}%"
                            blocks.append(nc.callout_block(demo_text, emoji="👥"))
                        
                        # 구독자 비율
                        subs = analysis.get("subscriber_status")
                        if subs:
                            blocks.append(nc.paragraph_block(
                                f"🔔 구독자: {subs['subscribed']}% / 비구독자: {subs['unsubscribed']}%"
                            ))
                        
                    except Exception as e:
                        blocks.append(nc.paragraph_block(f"⚠️ Analytics 데이터 수집 실패: {str(e)[:100]}"))
            
            # 수동 분석 영역 (Analytics 유무와 관계없이 항상 포함)
            blocks.append(nc.paragraph_block("✅ 좋았던 점: (작성 필요)"))
            blocks.append(nc.paragraph_block("❌ 개선점: (작성 필요)"))
            blocks.append(nc.paragraph_block("📌 이탈 원인 분석: (작성 필요)"))
            blocks.append(nc.paragraph_block(""))

        # ── 다음주 기획 방향 ──
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("📝 다음주 컨텐츠 기획 방향", level=2))

        # 다음주 날짜 계산
        next_week_start = datetime.strptime(week_range["end"], "%Y-%m-%d") + timedelta(days=1)
        next_week_end = next_week_start + timedelta(days=6)
        blocks.append(nc.paragraph_block(
            f"대상 기간: {next_week_start.month}/{next_week_start.day} ~ {next_week_end.month}/{next_week_end.day}",
            bold=True
        ))

        # 채널별 기획 방향 템플릿
        channel_guides = {
            "📸 인스타그램 매거진 피드": "목적: 브랜드 이미지 구축, 에디터 큐레이션\n→ 기획: (작성 필요)",
            "🎬 인스타그램 릴스": "목적: 신규 팔로워 유입, 알고리즘 노출\n→ 기획: (작성 필요)",
            "📺 유튜브 숏츠": "목적: 채널 유입 + 바이럴\n→ 기획: (작성 필요)",
            "🎥 유튜브 롱폼": "목적: 브랜드 신뢰도 + 깊은 스토리텔링\n→ 기획: (작성 필요)",
            "🎵 틱톡": "목적: Z세대 타겟 + 트렌드 참여\n→ 기획: (작성 필요)",
        }
        for channel, guide in channel_guides.items():
            blocks.append(nc.heading_block(channel, level=3))
            blocks.append(nc.paragraph_block(guide))

        # 마케팅 이슈 메모 영역
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("📅 마케팅 이슈 & 이벤트 캘린더", level=2))
        blocks.append(nc.callout_block(
            f"[{next_week_start.month}/{next_week_start.day}~{next_week_end.month}/{next_week_end.day}] 주요 이벤트/기념일:\n"
            "(실무자가 해당 주차의 이벤트, 시즌, 트렌드를 기록하세요)\n\n"
            "마케팅 포인트:\n"
            "→ (작성 필요)",
            emoji="📅"
        ))

        return blocks

    def _generate_insights(self, stats, comparisons):
        """데이터 기반 자동 인사이트 생성"""
        insights = []
        total = stats["total"]
        
        views_change = comparisons.get("total", {}).get("views", {})
        if views_change.get("direction") == "증가":
            insights.append(f"전체 조회수가 전주 대비 {abs(views_change.get('change_pct', 0))}% 증가했습니다.")
        elif views_change.get("direction") == "감소":
            insights.append(f"전체 조회수가 전주 대비 {abs(views_change.get('change_pct', 0))}% 감소했습니다. 원인 분석이 필요합니다.")

        for platform in ["인스타", "유튜브", "틱톡"]:
            p_stats = stats.get(platform, {})
            p_comp = comparisons.get(platform, {})
            
            if p_stats["count"] == 0:
                continue

            views_pct = p_comp.get("views", {}).get("change_pct", 0)
            if views_pct > 30:
                insights.append(f"{platform} 조회수가 전주 대비 {views_pct}% 급증. 성공 요인을 분석하여 반복 적용 필요.")
            elif views_pct < -30:
                insights.append(f"{platform} 조회수가 전주 대비 {abs(views_pct)}% 급감. 콘텐츠 방향 재검토 필요.")

            if p_stats["engagement_rate"] > Config.ENGAGEMENT_HIGH:
                insights.append(f"{platform} 참여율이 {p_stats['engagement_rate']}%로 '상' 이상 수준. 현재 방향 유지 추천.")

        if not insights:
            insights.append("이번 주는 전반적으로 안정적인 성과를 보였습니다.")

        return insights

    def run_weekly_analysis(self, target_date=None):
        """주간 분석 전체 실행
        
        핵심 변경: 기존 주차별 행을 찾아서 수치 업데이트 + 분석 블록 추가
        (별도 페이지 생성하지 않음)
        """
        week = self.get_week_range(target_date)
        prev_week = self.get_prev_week_range(target_date)

        print(f"\n{'='*60}")
        print(f"📊 주간 분석 실행: {week['label']}")
        print(f"   비교 대상: {prev_week['label']}")
        print(f"{'='*60}\n")

        # 1. 데이터 조회
        print("📥 이번주 데이터 조회 중...")
        this_week_raw = self.notion.query_content_db(week["start"], week["end"])
        this_week_data = [parse_notion_content(p) for p in this_week_raw]
        print(f"   → {len(this_week_data)}개 컨텐츠 확인")

        print("📥 전주 데이터 조회 중...")
        prev_week_raw = self.notion.query_content_db(prev_week["start"], prev_week["end"])
        prev_week_data = [parse_notion_content(p) for p in prev_week_raw]
        print(f"   → {len(prev_week_data)}개 컨텐츠 확인")

        # 2. 분석
        print("\n📊 분석 중...")
        this_stats, top_content = self.analyze_content_list(this_week_data)
        prev_stats, _ = self.analyze_content_list(prev_week_data)

        # 3. 비교
        comparisons = self.compare_weeks(this_stats, prev_stats)

        # 4. 주차별 DB에서 기존 행 찾기
        print("\n📋 주차별 DB 업데이트 중...")
        weekly_data = {
            "week_label": week["label"],
            "content_count": this_stats["total"]["count"],
            "total_views": this_stats["total"]["views"],
            "total_likes": this_stats["total"]["likes"],
            "total_saves": this_stats["total"]["saves"],
            "total_comments": this_stats["total"]["comments"],
            "total_shares": this_stats["total"]["shares"],
            "checked": True,
        }

        existing = self.notion.query_weekly_db(week["label"])
        
        if existing:
            # 기존 행 → 수치 업데이트
            page_id = existing[0]["id"]
            self.notion.update_weekly_entry(page_id, weekly_data)
            print(f"   ✅ 수치 업데이트 완료: {week['label']}")
            
            # 기존 페이지에 분석 블록 추가 (기존 내용 위에 추가됨)
            print("   📝 분석 블록 추가 중...")
            blocks = self.generate_analysis_blocks(week, this_stats, top_content, comparisons, prev_week)
            try:
                self.notion.append_blocks(page_id, blocks)
                print(f"   ✅ 분석 블록 추가 완료")
            except Exception as e:
                print(f"   ⚠️ 블록 추가 실패: {e}")
                # 블록이 너무 많으면 배치로 나눠서 추가
                print("   🔄 배치 추가 시도...")
                for i in range(0, len(blocks), 20):
                    batch = blocks[i:i+20]
                    try:
                        self.notion.append_blocks(page_id, batch)
                    except Exception as e2:
                        print(f"   ⚠️ 배치 {i//20+1} 실패: {e2}")
        else:
            # 새 행 생성 (수치 + 분석 블록 포함)
            print(f"   📝 새 행 생성: {week['label']}")
            blocks = self.generate_analysis_blocks(week, this_stats, top_content, comparisons, prev_week)
            
            try:
                page = self.notion.create_weekly_analysis_page_with_numbers(
                    Config.NOTION_WEEKLY_DB_ID,
                    week["label"],
                    weekly_data,
                    blocks
                )
                print(f"   ✅ 새 행 생성 완료: {page.get('url', '')}")
            except Exception as e:
                print(f"   ⚠️ 생성 실패, 수치만 저장: {e}")
                self.notion.create_weekly_entry(weekly_data)

        # 결과 요약
        print(f"\n{'='*60}")
        print(f"✅ 주간 분석 완료!")
        print(f"   총 컨텐츠: {this_stats['total']['count']}개")
        print(f"   총 조회수: {this_stats['total']['views']:,}회")
        print(f"   평균 조회수: {this_stats['total']['avg_views']:,}회")
        print(f"   참여율: {this_stats['total']['engagement_rate']}%")
        print(f"{'='*60}")

        return {
            "week": week,
            "stats": this_stats,
            "comparisons": comparisons,
            "top_content": top_content,
        }
