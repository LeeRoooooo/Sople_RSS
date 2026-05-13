import datetime
import time
import pytz
import requests
from playwright.sync_api import sync_playwright
from feedgen.feed import FeedGenerator

def scrape_sople_final_custom():
    fg = FeedGenerator()
    fg.id('https://sople.me/rss-custom-v12')
    fg.title('소플 통합 알림 (교양이연구소 커스텀)')
    fg.link(href='https://sople.me/', rel='alternate')
    fg.description('AI뉴스 40자 확장 및 작가 게시글 브랜드 각인 버전')
    fg.language('ko')

    # 제목 정제 및 절단 함수
    def refine_title(text, category):
        text = text.replace('\n', ' ').strip()
        
        if category == 'policy':
            # 1. 불필요 문구 제거 및 40자 절단
            text = text.replace("NEW AI 정책 뉴스", "").strip()
            prefix = "[AI뉴스]"
            limit = 40
            final_text = f"{prefix} {text}"
        else:
            # 2. 작가 부분 브랜드 각인 및 30자 절단 (기존 유지)
            prefix = "[교양이연구소]"
            limit = 30
            final_text = f"{prefix} {text}"
        
        if len(final_text) > limit:
            return final_text[:limit-3] + "..."
        return final_text

    # ==========================================
    # PART 1: 작가 게시글 수집 (API)
    # ==========================================
    print("[작가] API 수집 및 브랜딩 시작...")
    author_api_url = "https://sople.me/api/author/list/board?page=0&size=30&order=RECENT&topicCategory="
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0"}

    try:
        response = requests.get(author_api_url, headers=headers, timeout=20)
        if response.status_code == 200:
            posts = response.json().get("content", [])
            for post in posts:
                board_id = post.get("boardId")
                title = post.get("title", "제목 없음")
                if not board_id: continue

                link = f"https://sople.me/author/board/{board_id}"
                fe = fg.add_entry()
                fe.id(link)
                # [교양이연구소] 추가 및 절단
                fe.title(refine_title(title, 'author'))
                fe.link(href=link)
                fe.pubDate(datetime.datetime.now(pytz.utc))
            print(f"  ✅ 작가 게시글 {len(posts)}개 완료")
    except Exception as e:
        print(f"  ❌ 작가 오류: {e}")

    # ==========================================
    # PART 2: 정책뉴스 수집 (Playwright)
    # ==========================================
    print("\n[정책뉴스] 스크레이핑 및 40자 확장 시작...")
    policy_url = 'https://sople.me/newsroom/news-list?newsType=policy'
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 ...")
            page = context.new_page()
            
            page.goto(policy_url, wait_until="load", timeout=60000)
            time.sleep(6) 
            
            page.wait_for_selector("a[href*='/newsroom/news-list/']", timeout=20000)
            links = page.locator("a[href*='/newsroom/news-list/']").all()
            
            added_count = 0
            seen_links = set()

            for link in links:
                try:
                    full_text = link.inner_text().strip()
                    if len(full_text) < 5: continue

                    href = link.get_attribute("href") or ""
                    full_link = f"https://sople.me{href}" if href.startswith('/') else href
                    
                    if 'newsType=policy' in full_link and full_link not in seen_links:
                        seen_links.add(full_link)
                        
                        fe = fg.add_entry()
                        fe.id(full_link)
                        
                        # [AI뉴스] 명찰 달고 40자로 확장
                        fe.title(refine_title(full_text, 'policy'))
                        fe.description(full_text) 
                        fe.link(href=full_link)
                        fe.pubDate(datetime.datetime.now(pytz.utc))
                        
                        added_count += 1
                        if added_count >= 15: break
                except:
                    continue
            
            print(f"  ✅ 정책뉴스 {added_count}개 완료")
            browser.close()
        except Exception as e:
            print(f"  ❌ 정책뉴스 오류: {e}")

    # ==========================================
    # PART 3: 저장
    # ==========================================
    if fg.entry():
        fg.rss_file('sople_rss.xml', pretty=True)
        print(f"\n✨ 커스텀 완료! sople_rss.xml을 확인해 보세요.")
    else:
        print("\n😭 수집된 데이터가 없습니다.")

if __name__ == "__main__":
    scrape_sople_final_custom()
