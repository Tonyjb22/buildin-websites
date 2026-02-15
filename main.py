"""
빌딘 컨텐츠 자동화 시스템 - 메인 실행 스크립트

사용법:
    python main.py collect      # 새 컨텐츠 수집 + D+6 수치 업데이트
    python main.py analyze      # 주간 분석만  
    python main.py full         # 수집 + 분석 전체 실행
    python main.py test         # API 연결 테스트
"""
import sys
from datetime import datetime, timedelta
from config import Config


def run_collection():
    """데이터 수집: 
    1) 새 컨텐츠 → Notion DB에 항목 추가 (수치 없이 링크/날짜만)
    2) D+6 지난 컨텐츠 → 수치(조회수, 좋아요 등) 업데이트
    """
    from youtube_collector import YouTubeCollector
    from notion_client import NotionClient

    notion = NotionClient()
    today = datetime.now()

    # ═══════════════════════════════════════
    # STEP 1: 새 컨텐츠 수집 (어제~오늘 업로드분)
    # ═══════════════════════════════════════
    print("📥 STEP 1: 새 컨텐츠 수집 (최근 2일)")
    new_content = []

    # Instagram 수집
    if Config.INSTAGRAM_ACCESS_TOKEN:
        try:
            from instagram_collector import InstagramCollector
            ig = InstagramCollector()
            ig_content = ig.collect_weekly_data(days_back=2)
            new_content.extend(ig_content)
        except Exception as e:
            print(f"❌ Instagram 수집 오류: {e}")
    else:
        print("⏭️ Instagram API 토큰 미설정 - 건너뜁니다")

    # YouTube 수집
    if Config.YOUTUBE_API_KEY:
        try:
            yt = YouTubeCollector()
            yt_content = yt.collect_new_content(days_back=2)
            new_content.extend(yt_content)
        except Exception as e:
            print(f"❌ YouTube 수집 오류: {e}")
    else:
        print("⏭️ YouTube API 키 미설정 - 건너뜁니다")

    # Notion DB에 새 항목 추가 (수치 없이)
    created = 0
    skipped = 0
    for item in new_content:
        link = item.get("content_link", "")
        if not link:
            skipped += 1
            continue

        existing = notion.find_content_by_link(link)
        if existing:
            skipped += 1  # 이미 존재하면 건너뜀
            continue

        try:
            # 새 항목 생성 (수치 제외 - 링크/날짜/채널만)
            entry_data = {
                "upload_date": item["upload_date"],
                "route": item.get("route", "빌딘 오피셜"),
                "content_link": link,
                "channel_type": item["channel_type"],
            }
            notion.create_content_entry(entry_data)
            created += 1
            print(f"  ✅ 신규: [{item['channel_type']}] {item.get('title', link)[:40]}")
        except Exception as e:
            print(f"  ⚠️ 생성 실패: {link[:40]}... ({e})")
            skipped += 1

    print(f"📥 새 컨텐츠: {created}개 추가 | {skipped}개 건너뜀\n")

    # ═══════════════════════════════════════
    # STEP 2: D+6 수치 업데이트
    # ═══════════════════════════════════════
    print("📊 STEP 2: D+6 수치 업데이트")
    
    # 6~8일 전에 업로드된 컨텐츠 찾기 (D+6 수치 수집 대상)
    d6_start = (today - timedelta(days=8)).strftime("%Y-%m-%d")
    d6_end = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    
    print(f"  대상: {d6_start} ~ {d6_end} 업로드 컨텐츠")
    
    # Notion DB에서 해당 기간 컨텐츠 조회 (수치가 0인 것만)
    d6_content = notion.query_content_db(start_date=d6_start, end_date=d6_end)
    
    updated = 0
    for page in d6_content:
        props = page["properties"]
        
        # 이미 수치가 입력된 항목은 건너뜀
        views = props.get("조회수", {}).get("number")
        if views and views > 0:
            continue
        
        # 컨텐츠 링크 추출
        link = props.get("컨텐츠 링크", {}).get("url", "")
        if not link:
            continue
        
        # YouTube 수치 가져오기
        if "youtube.com" in link or "youtu.be" in link:
            if Config.YOUTUBE_API_KEY:
                try:
                    yt = YouTubeCollector()
                    metrics = yt.get_metrics_for_url(link)
                    if metrics:
                        notion.update_content_entry(page["id"], metrics)
                        updated += 1
                        print(f"  ✅ D+6 수치: {link[:40]}... (조회: {metrics.get('views', 0)})")
                except Exception as e:
                    print(f"  ⚠️ 수치 수집 실패: {link[:40]}... ({e})")
        
        # Instagram 수치 (향후 추가)
        elif "instagram.com" in link:
            if Config.INSTAGRAM_ACCESS_TOKEN:
                # TODO: Instagram 수치 업데이트 로직
                pass

    print(f"📊 D+6 수치 업데이트: {updated}개 완료\n")
    
    print(f"✅ 데이터 수집 완료!")


def run_analysis(target_date=None):
    """주간 분석 실행"""
    from weekly_analyzer import WeeklyAnalyzer
    
    analyzer = WeeklyAnalyzer()
    result = analyzer.run_weekly_analysis(target_date)
    return result


def run_test():
    """API 연결 테스트"""
    print("🔍 API 연결 테스트 시작...\n")

    # Notion
    print("── Notion ──")
    if Config.NOTION_API_TOKEN:
        from notion_client import NotionClient
        try:
            nc = NotionClient()
            results = nc.query_content_db()
            print(f"✅ Notion 연결 성공 (컨텐츠 DB: {len(results)}개 항목)")
        except Exception as e:
            print(f"❌ Notion 연결 실패: {e}")
    else:
        print("⚠️ NOTION_API_TOKEN이 설정되지 않았습니다")

    # Instagram
    print("\n── Instagram ──")
    if Config.INSTAGRAM_ACCESS_TOKEN:
        from instagram_collector import test_instagram_connection
        test_instagram_connection()
    else:
        print("⚠️ INSTAGRAM_ACCESS_TOKEN이 설정되지 않았습니다")

    # YouTube
    print("\n── YouTube ──")
    if Config.YOUTUBE_API_KEY:
        from youtube_collector import test_youtube_connection
        test_youtube_connection()
    else:
        print("⚠️ YOUTUBE_API_KEY가 설정되지 않았습니다")

    print("\n🔍 테스트 완료!")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "test":
        run_test()

    elif command == "collect":
        Config.validate()
        run_collection()

    elif command == "analyze":
        Config.validate()
        run_analysis()

    elif command == "full":
        Config.validate()
        print("🚀 전체 자동화 실행 시작\n")
        print("=" * 60)
        print("STEP 1: 데이터 수집 + D+6 수치 업데이트")
        print("=" * 60)
        run_collection()
        
        print("\n" + "=" * 60)
        print("STEP 2: 주간 분석")
        print("=" * 60)
        run_analysis()
        
        print("\n🎉 전체 자동화 완료!")

    else:
        print(f"알 수 없는 명령: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
