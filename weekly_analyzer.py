"""
빌딘 컨텐츠 자동화 시스템 - 주간 분석 생성기 v4
"""
import re
from datetime import datetime, timedelta
from collections import defaultdict
from config import Config
from notion_client import NotionClient, parse_notion_content

KOREAN_EVENTS = {
    (1, 1): ("새해 첫날", "새해 목표, 건강 다짐, 신년 루틴"),
    (2, 14): ("발렌타인데이", "커플 웰니스, 선물 추천, 건강 초콜릿"),
    (3, 1): ("삼일절", "국경일 휴무, 봄 시즌 전환"),
    (3, 8): ("세계 여성의 날", "여성 건강, 셀프케어"),
    (3, 14): ("화이트데이", "답례 선물, 건강 간식"),
    (3, 22): ("세계 물의 날", "수분 섭취, 하이드레이션"),
    (4, 7): ("세계 건강의 날", "건강 캠페인, 루틴 점검"),
    (4, 22): ("지구의 날", "친환경, 비건, 지속가능성"),
    (5, 5): ("어린이날", "가족 건강, 키즈 영양"),
    (5, 8): ("어버이날", "부모님 건강 선물"),
    (5, 15): ("스승의 날", "감사 선물"),
    (6, 6): ("현충일", "국경일 휴무"),
    (8, 15): ("광복절", "국경일, 여름 건강"),
    (10, 3): ("개천절", "국경일 휴무"),
    (10, 9): ("한글날", "국경일 휴무"),
    (10, 31): ("할로윈", "할로윈 이벤트, MZ 문화"),
    (11, 11): ("빼빼로데이", "선물 추천, 건강 간식"),
    (12, 25): ("크리스마스", "연말 선물, 홀리데이 루틴"),
    (12, 31): ("연말", "올해 회고, 건강 결산"),
}

SEASONAL_THEMES = {
    1: "신년 목표, 다이어트 시즌, 겨울 면역력, 실내 운동",
    2: "설 연휴, 봄 준비, 피부 관리, 발렌타인",
    3: "봄 시즌 전환, 알레르기, 야외 활동, 디톡스",
    4: "봄 나들이, 자외선 차단, 다이어트, 건강검진",
    5: "가정의 달, 야외 활동, 선물 시즌",
    6: "여름 준비, 바디 관리, 수분 보충, 장마",
    7: "본격 여름, 수분/전해질, 휴가 준비",
    8: "한여름, 피부 진정, 피로 회복, 가을 준비",
    9: "환절기 면역, 가을 건강, 추석, 실내 운동",
    10: "가을 건강, 면역력, 건조 피부 관리",
    11: "겨울 준비, 면역력 강화, 블프, 연말 시즌",
    12: "연말 결산, 송년회, 면역력, 겨울 루틴",
}


class WeeklyAnalyzer:
    def __init__(self):
        self.notion = NotionClient()
        self.analytics = None
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
        if target_date is None:
            target_date = datetime.now()
        days_since_monday = target_date.weekday()
        last_monday = target_date - timedelta(days=days_since_monday + 7)
        last_sunday = last_monday + timedelta(days=6)
        return {
            "start": last_monday.strftime("%Y-%m-%d"),
            "end": last_sunday.strftime("%Y-%m-%d"),
            "label": f"{last_monday.month}/{last_monday.day}-{last_sunday.month}/{last_sunday.day}",
            "start_dt": last_monday, "end_dt": last_sunday,
        }

    def get_prev_week_range(self, target_date=None):
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
        stats = {
            "total": {"count": 0, "views": 0, "likes": 0, "saves": 0, "comments": 0, "shares": 0},
            "인스타": {"count": 0, "views": 0, "likes": 0, "saves": 0, "comments": 0, "shares": 0},
            "유튜브": {"count": 0, "views": 0, "likes": 0, "saves": 0, "comments": 0, "shares": 0},
            "틱톡": {"count": 0, "views": 0, "likes": 0, "saves": 0, "comments": 0, "shares": 0},
        }
        all_content = []
        for item in content_list:
            ch = item.get("channel_type", "")
            platform = "인스타" if "인스타" in ch else "유튜브" if "유튜브" in ch else "틱톡" if "틱톡" in ch else None
            stats["total"]["count"] += 1
            for m in ["views", "likes", "saves", "comments", "shares"]:
                stats["total"][m] += item.get(m, 0)
                if platform and platform in stats:
                    stats[platform][m] += item.get(m, 0)
            if platform and platform in stats:
                stats[platform]["count"] += 1
            all_content.append(item)

        for key in stats:
            c = stats[key]["count"]
            stats[key]["avg_views"] = round(stats[key]["views"] / c) if c > 0 else 0
            v = stats[key]["views"]
            if v > 0:
                eng = stats[key]["likes"] + stats[key]["saves"] + stats[key]["comments"] + stats[key]["shares"]
                stats[key]["engagement_rate"] = round(eng / v * 100, 2)
            else:
                stats[key]["engagement_rate"] = 0

        all_content.sort(key=lambda x: x.get("views", 0), reverse=True)
        top5 = all_content[:5]
        low5 = list(reversed(all_content[-5:])) if len(all_content) > 5 else []
        return stats, top5, low5, all_content

    def calculate_engagement_d6(self, item):
        ch = item.get("channel_type", "")
        is_shorts = ch == "유튜브 숏츠"
        views = item.get("views", 0)
        if views == 0:
            return None
        likes = max(0, (item.get("likes", 0) - 1) if is_shorts else (item.get("likes", 0) - 3))
        saves = 0 if is_shorts else max(0, item.get("saves", 0) - 3)
        shares = 0 if is_shorts else max(0, item.get("shares", 0) - 3)
        comments = max(0, item.get("comments", 0) * 0.5)
        return round((likes + saves + shares + comments) / views * 100, 2)

    def rate_views(self, views):
        if views >= Config.VIEWS_BEST: return "최상", "🔥"
        elif views >= Config.VIEWS_HIGH: return "상", "⭐"
        elif views >= Config.VIEWS_MID: return "중", "😐"
        else: return "하", "👎"

    def rate_engagement(self, rate):
        if rate >= Config.ENGAGEMENT_BEST: return "최상", "🔥"
        elif rate >= Config.ENGAGEMENT_HIGH: return "상", "⭐"
        elif rate >= Config.ENGAGEMENT_MID: return "중", "😐"
        else: return "하", "👎"

    def compare_weeks(self, this_stats, prev_stats):
        comparisons = {}
        for platform in ["total", "인스타", "유튜브", "틱톡"]:
            this_w = this_stats.get(platform, {})
            prev_w = prev_stats.get(platform, {})
            comparisons[platform] = {}
            for metric in ["views", "avg_views", "count", "engagement_rate", "likes", "saves", "comments", "shares"]:
                tv = this_w.get(metric, 0)
                pv = prev_w.get(metric, 0)
                pct = round((tv - pv) / pv * 100, 1) if pv > 0 else (100 if tv > 0 else 0)
                d = "📈" if tv > pv else "📉" if tv < pv else "➡️"
                comparisons[platform][metric] = {"this_week": tv, "prev_week": pv, "change_pct": pct, "direction": d}
        return comparisons

    def _build_analytics_blocks(self, item, nc):
        blocks = []
        link = item.get("content_link", "")
        upload_date = item.get("upload_date", "")
        if not self.analytics or "youtube.com" not in link or not upload_date:
            return blocks
        match = re.search(r'(?:v=|shorts/)([a-zA-Z0-9_-]{11})', link)
        if not match:
            return blocks
        video_id = match.group(1)
        try:
            analysis = self.analytics.get_full_video_analysis(video_id, upload_date)
        except Exception as e:
            blocks.append(nc.paragraph_block(f"⚠️ Analytics 실패: {str(e)[:80]}"))
            return blocks

        basic = analysis.get("basic")
        if basic:
            blocks.append(nc.callout_block(
                f"⏱ 평균 시청: {basic.get('averageViewDuration', 0)}초 ({basic.get('averageViewPercentage', 0):.1f}%)\n"
                f"📺 총 시청: {round(basic.get('estimatedMinutesWatched', 0))}분\n"
                f"👥 구독자: +{basic.get('subscribersGained', 0)} / -{basic.get('subscribersLost', 0)}\n"
                f"↗️ 공유: {basic.get('shares', 0)}회", emoji="📊"))

        retention = analysis.get("retention")
        if retention:
            txt = f"평균 유지율: {retention['avg_view_pct']}%\n"
            if retention.get("drop_points"):
                txt += "⚠️ 이탈 구간:\n"
                for dp in sorted(retention["drop_points"], key=lambda x: -x["drop"])[:3]:
                    txt += f"  → {dp['position_pct']}% 지점: {dp['drop']}% 급감 ({dp['severity']})\n"
            else:
                txt += "✅ 특이 이탈 없음"
            blocks.append(nc.callout_block(txt, emoji="📉"))

        traffic = analysis.get("traffic_sources")
        if traffic:
            rows = [["유입 경로", "조회수", "비율"]]
            for src in traffic[:5]:
                rows.append([src["source"], f"{src['views']:,}", f"{src['pct']}%"])
            blocks.append(nc.table_block(rows))

        demo = analysis.get("demographics")
        if demo and demo.get("age_groups"):
            age_str = " | ".join([f"{a}: {p}%" for a, p in demo["age_groups"].items()])
            blocks.append(nc.callout_block(
                f"주요 시청층: {demo['top_gender']} {demo['top_age_group']}세\n"
                f"연령: {age_str}\n"
                f"성별: 남 {demo['gender'].get('male', 0)}% / 여 {demo['gender'].get('female', 0)}%", emoji="👥"))

        subs = analysis.get("subscriber_status")
        if subs and (subs.get('subscribed', 0) > 0 or subs.get('unsubscribed', 0) > 0):
            blocks.append(nc.paragraph_block(f"🔔 구독자 {subs['subscribed']}% / 비구독자 {subs['unsubscribed']}%"))
        return blocks

    def _generate_auto_planning(self, stats, comparisons, top5, low5, analytics_cache):
        plans = {}
        channel_data = defaultdict(lambda: {"top": [], "low": []})
        for item in top5:
            channel_data[item.get("channel_type", "")]["top"].append(item)
        for item in low5:
            channel_data[item.get("channel_type", "")]["low"].append(item)

        for ch_type, data in channel_data.items():
            lines = []
            if data["top"]:
                t = data["top"][0]
                lines.append(f"✅ 성공 패턴: TOP 성과 ({t.get('views', 0):,}회)")
                vid = re.search(r'(?:v=|shorts/)([a-zA-Z0-9_-]{11})', t.get("content_link", ""))
                if vid and vid.group(1) in analytics_cache:
                    a = analytics_cache[vid.group(1)]
                    b = a.get("basic", {})
                    if b.get("averageViewPercentage", 0) > 50:
                        lines.append(f"   → 유지율 {b['averageViewPercentage']:.0f}% → 비슷한 길이/구성 유지")
                    tr = a.get("traffic_sources", [])
                    if tr:
                        lines.append(f"   → 주요 유입: {tr[0]['source']} ({tr[0]['pct']}%)")
                    d = a.get("demographics", {})
                    if d.get("top_age_group"):
                        lines.append(f"   → 핵심 시청층: {d['top_gender']} {d['top_age_group']}세")
            if data["low"]:
                lo = data["low"][0]
                lines.append(f"❌ 개선: 하위 ({lo.get('views', 0):,}회)")
                vid = re.search(r'(?:v=|shorts/)([a-zA-Z0-9_-]{11})', lo.get("content_link", ""))
                if vid and vid.group(1) in analytics_cache:
                    a = analytics_cache[vid.group(1)]
                    r = a.get("retention", {})
                    if r and r.get("drop_points"):
                        dp = r["drop_points"][0]
                        lines.append(f"   → {dp['position_pct']}% 지점 이탈 → 초반 후킹 강화")
                    b = a.get("basic", {})
                    if b.get("averageViewPercentage", 0) < 30:
                        lines.append(f"   → 시청률 {b['averageViewPercentage']:.0f}% → 영상 단축 or 전개 변경")
            if lines:
                plans[ch_type] = lines

        general = []
        vc = comparisons.get("total", {}).get("views", {})
        if vc.get("change_pct", 0) < -20:
            general.append("⚠️ 조회수 하락세 → 후킹 강화, 트렌드 반영")
        elif vc.get("change_pct", 0) > 20:
            general.append("🔥 상승세 유지 → 성공 포맷 반복, 시리즈화")
        ec = comparisons.get("total", {}).get("engagement_rate", {})
        if ec.get("this_week", 0) < Config.ENGAGEMENT_MID:
            general.append("참여율 낮음 → CTA 강화 (질문형 캡션, 댓글/저장 유도)")
        general.append("공통: '전결기승' 원칙 — 결론(핵심 장면) 먼저 배치")
        plans["__general__"] = general
        return plans

    def _get_upcoming_events(self, start, end):
        events = []
        current = start
        while current <= end:
            key = (current.month, current.day)
            if key in KOREAN_EVENTS:
                name, mkt = KOREAN_EVENTS[key]
                events.append({"date": current.strftime("%m/%d"), "name": name, "marketing": mkt})
            current += timedelta(days=1)
        season = SEASONAL_THEMES.get(start.month, "")
        return events, season

    def _generate_seasonal_ideas(self, month, events, stats):
        ideas = []
        for evt in events:
            if evt["marketing"]:
                for kw in evt["marketing"].split(", ")[:2]:
                    ideas.append(f"[{evt['name']}] '{kw}' → 릴스/숏츠 트렌드 참여")
        season_map = {
            1: ["신년 건강 루틴 챌린지", "올해 목표 세팅 VLOG"],
            2: ["발렌타인 건강 선물 추천", "봄맞이 디톡스 루틴"],
            3: ["환절기 면역력 관리법", "봄 야외 활동 추천"],
            4: ["자외선 차단 꿀팁", "봄 다이어트 식단"],
            5: ["어버이날 건강 선물 가이드", "가정의 달 가족 건강"],
            6: ["여름 준비 바디케어", "수분 보충 꿀팁"],
            7: ["더위 이기는 건강 습관", "휴가 전 바디 관리"],
            8: ["여름 피로 회복법", "가을 준비 스킨케어"],
            9: ["환절기 면역 영양제 추천", "가을 실내 운동"],
            10: ["가을 건조 피부 관리", "면역력 부스터 루틴"],
            11: ["겨울 준비 건강 체크리스트", "블프 건강 아이템"],
            12: ["연말 회고 & 건강 결산", "크리스마스 선물 가이드"],
        }
        for idea in season_map.get(month, []):
            ideas.append(f"[시즌] {idea}")
        if not ideas:
            ideas.append("시즌 특이사항 없음 — 기존 방향 유지")
        return ideas

    def generate_analysis_blocks(self, week_range, stats, top5, low5, all_content, comparisons, prev_week):
        blocks = []
        nc = NotionClient
        analytics_cache = {}

        # 헤더
        blocks.append(nc.callout_block(
            f"📊 {week_range['label']} 주간 컨텐츠 분석 리포트\n자동 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}", emoji="📊"))
        blocks.append(nc.divider_block())

        # 1. 전주 대비 요약 (전주 수치 포함)
        blocks.append(nc.heading_block("📈 전주 대비 요약", level=2))
        for plabel, pkey in [("📊 전체", "total"), ("📸 인스타", "인스타"), ("📺 유튜브", "유튜브"), ("🎵 틱톡", "틱톡")]:
            s = stats.get(pkey, {})
            c = comparisons.get(pkey, {})
            if s.get("count", 0) == 0 and pkey != "total":
                continue
            blocks.append(nc.heading_block(plabel, level=3))
            rows = [["지표", "이번주", "전주", "증감", "변화율"]]
            for label, key, fmt, suf in [
                ("컨텐츠 수","count","",""), ("총 조회수","views",",",""), ("평균 조회수","avg_views",",",""),
                ("좋아요","likes",",",""), ("저장","saves",",",""), ("댓글","comments",",",""),
                ("공유","shares",",",""), ("참여율","engagement_rate","","%")]:
                comp = c.get(key, {})
                tv, pv = comp.get("this_week", 0), comp.get("prev_week", 0)
                ch_pct = comp.get("change_pct", 0)
                d = comp.get("direction", "➡️")
                ts = f"{tv:,}{suf}" if fmt == "," else f"{tv}{suf}"
                ps = f"{pv:,}{suf}" if fmt == "," else f"{pv}{suf}"
                rows.append([label, ts, ps, d, f"{'+' if ch_pct > 0 else ''}{ch_pct}%"])
            blocks.append(nc.table_block(rows))

        # 2. 인사이트
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("💡 주요 인사이트", level=2))
        for ins in self._generate_insights(stats, comparisons):
            blocks.append(nc.bulleted_list_block(ins))

        # 3. TOP 5
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("🏆 상위 성과 TOP 5", level=2))
        if top5:
            rows = [["#", "채널", "링크", "조회수", "좋아요", "참여율"]]
            for i, item in enumerate(top5, 1):
                eng = self.calculate_engagement_d6(item)
                link = item.get("content_link", "")
                if len(link) > 50: link = link[:50] + "..."
                rows.append([str(i), item.get("channel_type",""), link, f"{item.get('views',0):,}", str(item.get("likes",0)), f"{eng}%" if eng else "N/A"])
            blocks.append(nc.table_block(rows))

        # 4. LOW 5
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("💀 하위 성과 LOW 5", level=2))
        if low5:
            rows = [["#", "채널", "링크", "조회수", "좋아요", "참여율"]]
            for i, item in enumerate(low5, 1):
                eng = self.calculate_engagement_d6(item)
                link = item.get("content_link", "")
                if len(link) > 50: link = link[:50] + "..."
                rows.append([str(i), item.get("channel_type",""), link, f"{item.get('views',0):,}", str(item.get("likes",0)), f"{eng}%" if eng else "N/A"])
            blocks.append(nc.table_block(rows))

        # 5. 상세 분석 (TOP5 + LOW5 + Analytics)
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("✍️ 컨텐츠 상세 분석", level=2))

        # TOP 5 상세
        blocks.append(nc.heading_block("🏆 TOP 5 상세 분석", level=3))
        for i, item in enumerate(top5, 1):
            link = item.get("content_link", "")
            ch = item.get("channel_type", "")
            views = item.get("views", 0)
            eng = self.calculate_engagement_d6(item)
            vg, ve = self.rate_views(views)
            blocks.append(nc.callout_block(f"#{i} [{ch}] 조회 {views:,}회 | 참여율 {eng}% | {ve} {vg}" if eng else f"#{i} [{ch}] 조회 {views:,}회 | {ve} {vg}", emoji="🏆"))
            blocks.append(nc.paragraph_block(f"🔗 {link}"))
            ab = self._build_analytics_blocks(item, nc)
            if ab:
                blocks.extend(ab)
                # 캐시
                m = re.search(r'(?:v=|shorts/)([a-zA-Z0-9_-]{11})', link)
                if m:
                    try:
                        analytics_cache[m.group(1)] = self.analytics.get_full_video_analysis(m.group(1), item.get("upload_date",""))
                    except: pass
            blocks.append(nc.paragraph_block("✅ 좋았던 점: (작성)"))
            blocks.append(nc.paragraph_block("❌ 개선점: (작성)"))
            blocks.append(nc.divider_block())

        # LOW 5 상세
        if low5:
            blocks.append(nc.heading_block("💀 LOW 5 상세 분석", level=3))
            for i, item in enumerate(low5, 1):
                link = item.get("content_link", "")
                ch = item.get("channel_type", "")
                views = item.get("views", 0)
                eng = self.calculate_engagement_d6(item)
                blocks.append(nc.callout_block(f"#{i} [{ch}] 조회 {views:,}회 | 참여율 {eng}%" if eng else f"#{i} [{ch}] 조회 {views:,}회", emoji="💀"))
                blocks.append(nc.paragraph_block(f"🔗 {link}"))
                ab = self._build_analytics_blocks(item, nc)
                if ab:
                    blocks.extend(ab)
                    m = re.search(r'(?:v=|shorts/)([a-zA-Z0-9_-]{11})', link)
                    if m:
                        try:
                            analytics_cache[m.group(1)] = self.analytics.get_full_video_analysis(m.group(1), item.get("upload_date",""))
                        except: pass
                blocks.append(nc.paragraph_block("❓ 조회수 낮은 이유: (작성)"))
                blocks.append(nc.paragraph_block("🔧 개선 방안: (작성)"))
                blocks.append(nc.divider_block())

        # 6. 종합 평가
        blocks.append(nc.heading_block("📋 종합 평가", level=2))
        total = stats["total"]
        vg, ve = self.rate_views(total["avg_views"])
        eg, ee = self.rate_engagement(total["engagement_rate"])
        blocks.append(nc.callout_block(
            f"조회수: {ve} {vg} (평균 {total['avg_views']:,}회)\n참여율: {ee} {eg} ({total['engagement_rate']}%)", emoji="📋"))

        # 7. 다음주 기획 (자동 생성)
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("📝 다음주 컨텐츠 기획 방향", level=2))
        nws = datetime.strptime(week_range["end"], "%Y-%m-%d") + timedelta(days=1)
        nwe = nws + timedelta(days=6)
        blocks.append(nc.paragraph_block(f"대상: {nws.month}/{nws.day} ~ {nwe.month}/{nwe.day}", bold=True))

        plans = self._generate_auto_planning(stats, comparisons, top5, low5, analytics_cache)
        for ch_type, lines in plans.items():
            if ch_type == "__general__": continue
            blocks.append(nc.heading_block(f"[{ch_type}]", level=3))
            for line in lines:
                blocks.append(nc.bulleted_list_block(line))
        gen = plans.get("__general__", [])
        if gen:
            blocks.append(nc.heading_block("🎯 전체 방향", level=3))
            for line in gen:
                blocks.append(nc.bulleted_list_block(line))

        # 8. 마케팅 이벤트 (자동)
        blocks.append(nc.divider_block())
        blocks.append(nc.heading_block("📅 마케팅 이슈 & 이벤트", level=2))
        events, season = self._get_upcoming_events(nws, nwe)
        blocks.append(nc.callout_block(f"📌 {nws.month}월 시즌 키워드: {season}", emoji="📌"))
        if events:
            rows = [["날짜", "이벤트", "마케팅 포인트"]]
            for e in events:
                rows.append([e["date"], e["name"], e["marketing"]])
            blocks.append(nc.table_block(rows))
        else:
            blocks.append(nc.paragraph_block("이번 주 특별 이벤트 없음"))
        blocks.append(nc.heading_block("💡 시즌 컨텐츠 아이디어", level=3))
        for idea in self._generate_seasonal_ideas(nws.month, events, stats):
            blocks.append(nc.bulleted_list_block(idea))

        return blocks

    def _generate_insights(self, stats, comparisons):
        insights = []
        vc = comparisons.get("total", {}).get("views", {})
        if vc.get("change_pct", 0) > 0:
            insights.append(f"전체 조회수 전주 대비 {abs(vc.get('change_pct',0))}% 증가 ({vc.get('prev_week',0):,} → {vc.get('this_week',0):,})")
        elif vc.get("change_pct", 0) < 0:
            insights.append(f"⚠️ 전체 조회수 전주 대비 {abs(vc.get('change_pct',0))}% 감소 ({vc.get('prev_week',0):,} → {vc.get('this_week',0):,})")
        for p in ["인스타", "유튜브", "틱톡"]:
            ps = stats.get(p, {})
            pc = comparisons.get(p, {})
            if ps["count"] == 0: continue
            vp = pc.get("views", {}).get("change_pct", 0)
            if vp > 30: insights.append(f"🔥 {p} 조회수 +{vp}% 급증 → 성공 요인 반복")
            elif vp < -30: insights.append(f"⚠️ {p} 조회수 {vp}% 급감 → 방향 재검토")
            if ps["engagement_rate"] > Config.ENGAGEMENT_HIGH:
                insights.append(f"{p} 참여율 {ps['engagement_rate']}% (상) → 방향 유지")
        if not insights: insights.append("전반적으로 안정적인 성과")
        return insights

    def run_weekly_analysis(self, target_date=None):
        week = self.get_week_range(target_date)
        prev_week = self.get_prev_week_range(target_date)
        print(f"\n{'='*60}\n📊 주간 분석: {week['label']} (비교: {prev_week['label']})\n{'='*60}\n")

        print("📥 이번주 데이터 조회 중...")
        this_raw = self.notion.query_content_db(week["start"], week["end"])
        this_data = [parse_notion_content(p) for p in this_raw]
        print(f"   → {len(this_data)}개")

        print("📥 전주 데이터 조회 중...")
        prev_raw = self.notion.query_content_db(prev_week["start"], prev_week["end"])
        prev_data = [parse_notion_content(p) for p in prev_raw]
        print(f"   → {len(prev_data)}개")

        print("\n📊 분석 중...")
        this_stats, top5, low5, all_content = self.analyze_content_list(this_data)
        prev_stats, _, _, _ = self.analyze_content_list(prev_data)
        comparisons = self.compare_weeks(this_stats, prev_stats)

        print("\n📋 주차별 DB 업데이트 중...")
        wd = {
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
        blocks = self.generate_analysis_blocks(week, this_stats, top5, low5, all_content, comparisons, prev_week)

        if existing:
            pid = existing[0]["id"]
            self.notion.update_weekly_entry(pid, wd)
            print(f"   ✅ 수치 업데이트: {week['label']}")
            print("   📝 블록 추가 중...")
            for i in range(0, len(blocks), 20):
                try: self.notion.append_blocks(pid, blocks[i:i+20])
                except Exception as e: print(f"   ⚠️ 배치 {i//20+1} 실패: {e}")
            print("   ✅ 완료")
        else:
            print(f"   📝 새 행 생성: {week['label']}")
            try:
                self.notion.create_weekly_analysis_page_with_numbers(Config.NOTION_WEEKLY_DB_ID, week["label"], wd, blocks)
                print("   ✅ 생성 완료")
            except Exception as e:
                print(f"   ⚠️ 실패, 수치만 저장: {e}")
                self.notion.create_weekly_entry(wd)

        print(f"\n{'='*60}\n✅ 완료! 컨텐츠: {this_stats['total']['count']}개 | 조회: {this_stats['total']['views']:,}회 | 참여율: {this_stats['total']['engagement_rate']}%\n{'='*60}")
        return {"week": week, "stats": this_stats, "comparisons": comparisons, "top_content": top5, "low_content": low5}
