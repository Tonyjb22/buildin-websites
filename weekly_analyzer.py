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

    def get_week_range(self, target_date=None):
        """주차 날짜 범위 계산 (월~일 기준)"""
        if target_date is None:
            target_date = datetime.now()
        
        # 직전 주 월요일~일요일
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

        top_content = []  # 조회수 기준 상위 컨텐츠

        for item in content_list:
            ch = item.get("channel_type", "")
            
            # 플랫폼 분류
            if "인스타" in ch:
                platform = "인스타"
            elif "유튜브" in ch:
                platform = "유튜브"
            elif "틱톡" in ch:
                platform = "틱톡"
            else:
                platform = None

            # 전체 통계
            stats["total"]["count"] += 1
            stats["total"]["views"] += item.get("views", 0)
            stats["total"]["likes"] += item.get("likes", 0)
            stats["total"]["saves"] += item.get("saves", 0)
            stats["total"]["comments"] += item.get("comments", 0)
            stats["total"]["shares"] += item.get("shares", 0)

            # 플랫폼별 통계
            if platform and platform in stats:
                stats[platform]["count"] += 1
                stats[platform]["views"] += item.get("views", 0)
                stats[platform]["likes"] += item.get("likes", 0)
                stats[platform]["saves"] += item.get("saves", 0)
                stats[platform]["comments"] += item.get("comments", 0)
                stats[platform]["shares"] += item.get("shares", 0)

            top_content.append(item)

        # 평균 조회수 계산
        for key in stats:
            count = stats[key]["count"]
            stats[key]["avg_views"] = round(stats[key]["views"] / count) if count > 0 else 0

        # 참여율 계산
        for key in stats:
            views = stats[key]["views"]
            if views > 0:
                engagement = stats[key]["likes"] + stats[key]["saves"] + stats[key]["comments"] + stats[key]["shares"]
                stats[key]["engagement_rate"] = round(engagement / views * 100, 2)
            else:
                stats[key]["engagement_rate"] = 0

        # 상위 컨텐츠 정렬
        top_content.sort(key=lambda x: x.get("views", 0), reverse=True)

        return stats, top_content[:5]

    def calculate_engagement_d6(self, item):
        """D+6 참여율 계산 (노션 수식 로직 재구현)"""
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
        """총평 산출 (조회수×참여율 매트릭스 기반 액션플랜)"""
        key = (views_grade, eng_grade)
        if key in Config.RATING_ACTION_MAP:
            emoji, label, action = Config.RATING_ACTION_MAP[key]
            return emoji, label, action
        # 매핑에 없는 경우 기본값
        return "😐", f"{views_grade}-{eng_grade}", "특이사항 없음."

    def rate_single_content(self, item):
        """개별 컨텐츠 평가 (조회수 + 참여율 → 총평)"""
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
        nc = NotionClient  # 블록 헬퍼 사용

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

        # 자동 인사이트 생성
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
            
            blocks.append(nc.heading_block(f"{'📸' if platform == '인스타' else '📺' if platform == '유튜브' else '🎵'} {platform}그램" if platform == "인스타" else f"{'📺' if platform == '유튜브' else '🎵'} {platform}", level=3))
            
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

        # ── 평가 ──
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

        # ── 개별 컨텐츠 총평 (상위 + 하위) ──
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("🏷️ 컨텐츠별 총평 & 액션플랜", level=2))

        if top_content:
            rating_rows = [["채널/유형", "조회수", "참여율", "총평", "액션"]]
            for item in top_content:
                r = self.rate_single_content(item)
                link = item.get("content_link", "")
                if len(link) > 30:
                    link = link[:30] + "..."
                rating_rows.append([
                    item.get("channel_type", ""),
                    f"{item.get('views', 0):,}",
                    f"{r['engagement_value']}%" if r['engagement_value'] is not None else "N/A",
                    f"{r['overall_emoji']} {r['overall_label']}",
                    r["action"][:30] + "..." if len(r["action"]) > 30 else r["action"],
                ])
            blocks.append(nc.table_block(rating_rows))

        # ── 다음주 개선 포인트 ──
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("🎯 다음주 개선 포인트", level=2))

        improvements = self._generate_improvements(stats, comparisons, top_content)
        for imp in improvements:
            blocks.append(nc.bulleted_list_block(imp))

        # ── 다음주 컨텐츠 기획 방향 ──
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("📝 다음주 컨텐츠 기획 방향", level=2))
        blocks.append(nc.paragraph_block("(실무자가 아래 내용을 바탕으로 구체적인 기획을 작성해주세요)", color="gray"))

        directions = self._generate_content_directions(stats, comparisons, top_content)
        for direction in directions:
            blocks.append(nc.bulleted_list_block(direction))

        return blocks

    def _generate_insights(self, stats, comparisons):
        """데이터 기반 자동 인사이트 생성"""
        insights = []
        total = stats["total"]
        
        # 전체 추세
        views_change = comparisons.get("total", {}).get("views", {})
        if views_change.get("direction") == "증가":
            insights.append(f"전체 조회수가 전주 대비 {abs(views_change.get('change_pct', 0))}% 증가했습니다.")
        elif views_change.get("direction") == "감소":
            insights.append(f"전체 조회수가 전주 대비 {abs(views_change.get('change_pct', 0))}% 감소했습니다. 원인 분석이 필요합니다.")

        # 플랫폼별 특이사항
        for platform in ["인스타", "유튜브", "틱톡"]:
            p_stats = stats.get(platform, {})
            p_comp = comparisons.get(platform, {})
            
            if p_stats["count"] == 0:
                continue

            # 조회수 급증/급감 (30% 이상 변화)
            views_pct = p_comp.get("views", {}).get("change_pct", 0)
            if views_pct > 30:
                insights.append(f"{platform} 조회수가 전주 대비 {views_pct}% 급증. 성공 요인을 분석하여 반복 적용 필요.")
            elif views_pct < -30:
                insights.append(f"{platform} 조회수가 전주 대비 {abs(views_pct)}% 급감. 콘텐츠 방향 재검토 필요.")

            # 높은 참여율
            if p_stats["engagement_rate"] > Config.ENGAGEMENT_HIGH:
                insights.append(f"{platform} 참여율이 {p_stats['engagement_rate']}%로 '상' 이상 수준. 현재 콘텐츠 방향을 유지하면 좋겠습니다.")

        if not insights:
            insights.append("이번 주는 전반적으로 안정적인 성과를 보였습니다.")

        return insights

    def _generate_improvements(self, stats, comparisons, top_content):
        """개선 포인트 자동 생성 (4단계 평가 기반)"""
        improvements = []

        for platform in ["인스타", "유튜브", "틱톡"]:
            p_stats = stats.get(platform, {})
            p_comp = comparisons.get(platform, {})
            
            if p_stats["count"] == 0:
                continue

            # 조회수 감소 플랫폼
            if p_comp.get("views", {}).get("direction") == "감소":
                improvements.append(f"[{platform}] 조회수 감소 → 초반 3초 후킹 강화. 첫 프레임에 시각적 자극(음식, 비포/애프터 등) 배치")

            # 참여율 '하' 플랫폼
            if p_stats["engagement_rate"] < Config.ENGAGEMENT_MID:
                improvements.append(f"[{platform}] 참여율 {p_stats['engagement_rate']}%로 '하' 등급 → 이탈률 점검. CTA 강화, 저장/공유 유도 멘트 추가")
            
            # 조회수 '하' 플랫폼
            if p_stats["avg_views"] < Config.VIEWS_MID:
                improvements.append(f"[{platform}] 평균 조회수 {p_stats['avg_views']}회로 '하' 등급 → 썸네일/제목 자극적으로 변경, 해시태그 전략 재검토")

        # 상위 컨텐츠 패턴 분석
        if top_content:
            top_types = [item.get("channel_type", "") for item in top_content[:3]]
            if len(set(top_types)) == 1:
                improvements.append(f"상위 컨텐츠가 모두 [{top_types[0]}] → 해당 채널 비중 확대, 다른 채널은 포맷 변경 시도")

        if not improvements:
            improvements.append("전반적으로 양호한 성과. 현재 전략을 유지하되, 콘텐츠별 A/B 테스트(썸네일·제목·도입부)로 최적화 시도")

        return improvements

    def _generate_content_directions(self, stats, comparisons, top_content):
        """다음주 컨텐츠 방향 제안"""
        directions = []

        # 잘 나온 포맷 기반 방향
        if top_content:
            best = top_content[0]
            r = self.rate_single_content(best)
            directions.append(
                f"이번주 최고 성과: [{best.get('channel_type', '')}] 조회수 {best.get('views', 0):,}회 "
                f"→ 총평 {r['overall_emoji']} {r['overall_label']}"
            )
            if "재업로드" in r.get("overall_label", ""):
                directions.append(f"→ 성과 좋은 컨텐츠를 시기 맞춰 재업로드 추천")
            elif "광고" in r.get("action", ""):
                directions.append(f"→ 유료 광고 집행 적극 추천")

        # 플랫폼별 방향
        for platform in ["인스타", "유튜브", "틱톡"]:
            p_stats = stats.get(platform, {})
            if p_stats["count"] == 0:
                continue

            if p_stats["avg_views"] >= Config.VIEWS_HIGH:
                directions.append(f"[{platform}] 성과 우수(상 이상) → 컨텐츠 수 늘려볼 것 추천. 현재 포맷 유지.")
            elif p_stats["avg_views"] < Config.VIEWS_MID:
                directions.append(f"[{platform}] 성과 부진(하) → 포맷 변경 또는 후킹 포인트 강화. 숏폼 호흡 빠르게.")

        # 공통 방향
        directions.append("공통: '기승전결' 대신 '전결기승' — 맛있는 것(결론) 먼저 배치")
        directions.append("웰니스 포지셔닝: '약과 경쟁X, 보완O' → 일상 관리 루틴으로 컨텐츠 전개")
        directions.append("인스타: 비주얼 이미지 + 트렌디한 오디오 필수. 광고 느낌 최소화 (일반 릴스와 혼동되기 쉬운 형태)")

        return directions

    def run_weekly_analysis(self, target_date=None):
        """주간 분석 전체 실행
        
        1. 이번주/전주 데이터 조회
        2. 통계 분석
        3. 전주 대비 비교
        4. Notion 분석 페이지 생성
        5. 주차별 DB 업데이트
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

        # 4. Notion 분석 페이지 생성
        if Config.NOTION_ANALYSIS_PAGE_ID:
            print("\n📝 Notion 분석 페이지 생성 중...")
            blocks = self.generate_analysis_blocks(week, this_stats, top_content, comparisons, prev_week)
            
            title = f"📊 {week['label']} 주간 분석"
            page = self.notion.create_weekly_analysis_page(
                Config.NOTION_ANALYSIS_PAGE_ID,
                title,
                blocks
            )
            print(f"   ✅ 분석 페이지 생성 완료: {page.get('url', 'URL 확인 필요')}")

        # 5. 주차별 DB 업데이트
        if Config.NOTION_WEEKLY_DB_ID:
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
                self.notion.update_weekly_entry(existing[0]["id"], weekly_data)
                print(f"   ✅ 기존 항목 업데이트: {week['label']}")
            else:
                self.notion.create_weekly_entry(weekly_data)
                print(f"   ✅ 새 항목 생성: {week['label']}")

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
