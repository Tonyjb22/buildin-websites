"""
빌딘 컨텐츠 자동화 시스템 - 메인 실행 스크립트

사용법:
    python main.py collect      # 데이터 수집만
    python main.py analyze      # 주간 분석만  
    python main.py full         # 수집 + 분석 전체 실행
    python main.py test         # API 연결 테스트
"""
import sys
from datetime import datetime
from config import Config


def run_collection():
    """데이터 수집: Instagram + YouTube → Notion DB"""
    from instagram_collector import InstagramCollector
    from youtube_collector import YouTubeCollector
    from notion_client import NotionClient

    notion = NotionClient()
    all_content = []

    # ── Instagram 수집 ──
    if Config.INSTAGRAM_ACCESS_TOKEN:
        try:
            ig = InstagramCollector()
            ig_content = ig.collect_weekly_data(days_back=7)
            all_content.extend(ig_content)
        except Exception as e:
            print(f"❌ Instagram 수집 오류: {e}")
    else:
        print("⏭️ Instagram API 토큰 미설정 - 건너뜁니다")

    # ── YouTube 수집 ──
    if Config.YOUTUBE_API_KEY:
        try:
            yt = YouTubeCollector()
            yt_content = yt.collect_weekly_data(days_back=7)
            all_content.extend(yt_content)
        except Exception as e:
            print(f"❌ YouTube 수집 오류: {e}")
    else:
        print("⏭️ YouTube API 키 미설정 - 건너뜁니다")

    # ── Notion DB에 저장/업데이트 ──
    print(f"\n💾 Notion DB에 {len(all_content)}개 항목 저장 중...")
    
    created = 0
    updated = 0
    skipped = 0

    for item in all_content:
        link = item.get("content_link", "")
        if not link:
            skipped += 1
            continue

        # 기존 항목 검색
        existing = notion.find_content_by_link(link)
        
        if existing:
            # 기존 항목 업데이트 (조회수 등 갱신)
            notion.update_content_entry(existing["id"], {
                "views": item.get("views"),
                "likes": item.get("likes"),
                "saves": item.get("saves"),
                "comments": item.get("comments"),
                "shares": item.get("shares"),
                "checked": True,
            })
            updated += 1
        else:
            # 새 항목 생성
            try:
                notion.create_content_entry(item)
                created += 1
            except Exception as e:
                print(f"  ⚠️ 생성 실패: {link[:40]}... ({e})")
                skipped += 1

    print(f"\n✅ Notion DB 저장 완료: 신규 {created}개 | 업데이트 {updated}개 | 건너뜀 {skipped}개")
    return all_content


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
        print("STEP 1: 데이터 수집")
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
