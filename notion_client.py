"""
빌딘 컨텐츠 자동화 시스템 - Notion API 클라이언트
"""
import requests
from datetime import datetime, timedelta
from config import Config


class NotionClient:
    BASE_URL = "https://api.notion.com/v1"
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {Config.NOTION_API_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }

    def _request(self, method, endpoint, json_data=None):
        """API 요청 래퍼"""
        url = f"{self.BASE_URL}{endpoint}"
        resp = requests.request(method, url, headers=self.headers, json=json_data)
        if resp.status_code not in (200, 201):
            print(f"❌ Notion API 오류 [{resp.status_code}]: {resp.text[:300]}")
        resp.raise_for_status()
        return resp.json()

    # ─── 컨텐츠 DB 조작 ───

    def query_content_db(self, start_date=None, end_date=None, filter_extra=None):
        """컨텐츠 목록 DB에서 항목 조회"""
        filters = []
        
        if start_date:
            filters.append({
                "property": "업로드 일",
                "date": {"on_or_after": start_date}
            })
        if end_date:
            filters.append({
                "property": "업로드 일",
                "date": {"on_or_before": end_date}
            })
        if filter_extra:
            filters.append(filter_extra)

        body = {"page_size": 100}
        if len(filters) == 1:
            body["filter"] = filters[0]
        elif len(filters) > 1:
            body["filter"] = {"and": filters}

        all_results = []
        has_more = True
        start_cursor = None

        while has_more:
            if start_cursor:
                body["start_cursor"] = start_cursor
            
            data = self._request("POST", f"/databases/{Config.NOTION_CONTENT_DB_ID}/query", body)
            all_results.extend(data.get("results", []))
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

        return all_results

    def create_content_entry(self, entry_data):
        """컨텐츠 목록 DB에 새 항목 추가
        
        entry_data = {
            "upload_date": "2026-02-14",
            "route": "빌딘 오피셜",
            "content_link": "https://...",
            "channel_type": "인스타그램 릴스",
            "views": 500,
            "likes": 10,
            "saves": 5,
            "comments": 2,
            "shares": 1,
        }
        """
        properties = {
            "업로드 일": {"date": {"start": entry_data["upload_date"]}},
            "경로(계정)": {"select": {"name": entry_data["route"]}},
            "컨텐츠 링크": {"url": entry_data["content_link"]},
            "채널/유형": {"select": {"name": entry_data["channel_type"]}},
        }

        # 숫자 필드 (있는 경우에만 추가)
        num_fields = {
            "조회수": "views",
            "좋아요": "likes",
            "저장": "saves",
            "댓글": "comments",
            "공유": "shares",
        }
        for notion_name, key in num_fields.items():
            if key in entry_data and entry_data[key] is not None:
                properties[notion_name] = {"number": entry_data[key]}

        return self._request("POST", "/pages", {
            "parent": {"database_id": Config.NOTION_CONTENT_DB_ID},
            "properties": properties,
        })

    def update_content_entry(self, page_id, updates):
        """기존 컨텐츠 항목 업데이트 (조회수, 좋아요 등 갱신)"""
        properties = {}
        
        num_fields = {
            "views": "조회수",
            "likes": "좋아요",
            "saves": "저장",
            "comments": "댓글",
            "shares": "공유",
        }
        for key, notion_name in num_fields.items():
            if key in updates and updates[key] is not None:
                properties[notion_name] = {"number": updates[key]}

        # 점검현황 체크
        if "checked" in updates:
            properties["점검현황"] = {"checkbox": updates["checked"]}

        if properties:
            return self._request("PATCH", f"/pages/{page_id}", {"properties": properties})

    def find_content_by_link(self, link):
        """컨텐츠 링크로 기존 항목 검색"""
        body = {
            "filter": {
                "property": "컨텐츠 링크",
                "url": {"equals": link}
            }
        }
        data = self._request("POST", f"/databases/{Config.NOTION_CONTENT_DB_ID}/query", body)
        results = data.get("results", [])
        return results[0] if results else None

    # ─── 주차별 정리 DB 조작 ───

    def query_weekly_db(self, week_label=None):
        """주차별 정리 DB 조회"""
        body = {"page_size": 100}
        if week_label:
            body["filter"] = {
                "property": "주차",
                "title": {"equals": week_label}
            }
        
        data = self._request("POST", f"/databases/{Config.NOTION_WEEKLY_DB_ID}/query", body)
        return data.get("results", [])

    def create_weekly_entry(self, week_data):
        """주차별 정리 항목 생성
        
        week_data = {
            "week_label": "2/2-2/8",
            "content_count": 24,
            "total_views": 8219,
            "total_likes": 146,
            "total_saves": 24,
            "total_comments": 20,
            "total_shares": 12,
            "engagement_rate": 2.37,
        }
        """
        properties = {
            "주차": {"title": [{"text": {"content": week_data["week_label"]}}]},
            "컨텐츠 수": {"number": week_data["content_count"]},
            "조회수": {"number": week_data["total_views"]},
            "좋아요": {"number": week_data["total_likes"]},
            "저장": {"number": week_data["total_saves"]},
            "댓글": {"number": week_data["total_comments"]},
            "공유": {"number": week_data["total_shares"]},
        }

        return self._request("POST", "/pages", {
            "parent": {"database_id": Config.NOTION_WEEKLY_DB_ID},
            "properties": properties,
        })

    def update_weekly_entry(self, page_id, week_data):
        """주차별 정리 항목 업데이트"""
        properties = {}
        field_map = {
            "content_count": "컨텐츠 수",
            "total_views": "조회수",
            "total_likes": "좋아요",
            "total_saves": "저장",
            "total_comments": "댓글",
            "total_shares": "공유",
        }
        for key, notion_name in field_map.items():
            if key in week_data:
                properties[notion_name] = {"number": week_data[key]}

        if "checked" in week_data:
            properties["점검현황"] = {"checkbox": week_data["checked"]}

        return self._request("PATCH", f"/pages/{page_id}", {"properties": properties})

    # ─── 주간 분석 페이지 생성 ───

def create_weekly_analysis_page(self, parent_id, title, blocks):
    """주간 분석 결과를 주차별 정리 DB 안에 페이지로 생성"""
    return self._request("POST", "/pages", {
        "parent": {"database_id": parent_id},
        "properties": {
            "주차": {"title": [{"text": {"content": title}}]}
        },

    def append_blocks(self, page_id, blocks):
        """기존 페이지에 블록 추가"""
        return self._request("PATCH", f"/blocks/{page_id}/children", {
            "children": blocks,
        })

    # ─── Notion 블록 헬퍼 ───

    @staticmethod
    def heading_block(text, level=2):
        """제목 블록 생성"""
        key = f"heading_{level}"
        return {
            "object": "block",
            "type": key,
            key: {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }

    @staticmethod
    def paragraph_block(text, bold=False, color="default"):
        """문단 블록 생성"""
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{
                    "type": "text",
                    "text": {"content": text},
                    "annotations": {"bold": bold, "color": color}
                }]
            }
        }

    @staticmethod
    def bulleted_list_block(text):
        """글머리 기호 목록 블록"""
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }

    @staticmethod
    def callout_block(text, emoji="💡"):
        """콜아웃 블록"""
        return {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"type": "text", "text": {"content": text}}],
                "icon": {"type": "emoji", "emoji": emoji},
            }
        }

    @staticmethod
    def divider_block():
        return {"object": "block", "type": "divider", "divider": {}}

    @staticmethod
    def table_block(rows, has_header=True):
        """테이블 블록 생성
        rows = [["헤더1", "헤더2"], ["값1", "값2"], ...]
        """
        table_rows = []
        for row in rows:
            cells = []
            for cell in row:
                cells.append([{
                    "type": "text",
                    "text": {"content": str(cell)}
                }])
            table_rows.append({
                "type": "table_row",
                "table_row": {"cells": cells}
            })

        return {
            "type": "table",
            "table": {
                "table_width": len(rows[0]) if rows else 1,
                "has_column_header": has_header,
                "has_row_header": False,
                "children": table_rows,
            }
        }


# 편의 함수
def parse_notion_content(page):
    """Notion 페이지 데이터를 파이썬 딕셔너리로 변환"""
    props = page["properties"]
    
    def get_number(prop_name):
        p = props.get(prop_name, {})
        return p.get("number") if p.get("number") is not None else 0

    def get_date(prop_name):
        p = props.get(prop_name, {})
        date_obj = p.get("date")
        return date_obj["start"] if date_obj else None

    def get_select(prop_name):
        p = props.get(prop_name, {})
        sel = p.get("select")
        return sel["name"] if sel else None

    def get_url(prop_name):
        p = props.get(prop_name, {})
        return p.get("url")

    def get_checkbox(prop_name):
        p = props.get(prop_name, {})
        return p.get("checkbox", False)

    def get_formula_string(prop_name):
        p = props.get(prop_name, {})
        formula = p.get("formula", {})
        return formula.get("string", "")

    return {
        "page_id": page["id"],
        "upload_date": get_date("업로드 일"),
        "route": get_select("경로(계정)"),
        "content_link": get_url("컨텐츠 링크"),
        "channel_type": get_select("채널/유형"),
        "views": get_number("조회수"),
        "likes": get_number("좋아요"),
        "saves": get_number("저장"),
        "comments": get_number("댓글"),
        "shares": get_number("공유"),
        "checked": get_checkbox("점검현황"),
        "engagement": get_formula_string("D+6 참여..."),
    }
