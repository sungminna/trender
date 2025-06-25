from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def run_playwright():
    from playwright.sync_api import sync_playwright
    import os

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://namu.wiki")
        page.wait_for_timeout(3000)  # 더 긴 대기 시간
        
        # 트렌딩 키워드들을 개별적으로 추출
        trending_keywords = []
        
        # 실제 HTML 구조에 맞는 선택자들
        selectors_to_try = [
            "[data-v-dea72308] li a span",  # data-v 속성 내부의 모든 키워드 span들
        ]
        
        for selector in selectors_to_try:
            elements = page.query_selector_all(selector)
            if elements:
                print(f"Found {len(elements)} elements with selector: {selector}")
                for i, element in enumerate(elements):
                    keyword = element.text_content().strip()
                    if keyword and keyword not in trending_keywords:  # 중복 제거
                        trending_keywords.append(keyword)
                        print(f"{len(trending_keywords)}. {keyword}")
                        if len(trending_keywords) >= 10:  # 10개로 제한
                            break
                break
        
        # 만약 개별 요소들을 찾지 못했다면, 전체 텍스트를 분석
        if not trending_keywords:
            element = page.query_selector("[data-v-dea72308]")
            if element:
                full_text = element.text_content().strip()
                print(f"Full text: {full_text}")
                
                # 텍스트를 분석해서 키워드들을 추출
                import re
                # 한글, 영어, 숫자, 특수문자 조합으로 키워드 패턴 매칭
                keywords = re.findall(r'[가-힣a-zA-Z0-9()]+', full_text)
                
                print(f"Extracted {len(keywords)} keywords:")
                for i, keyword in enumerate(keywords[:10]):  # 최대 10개만
                    print(f"{i+1}. {keyword}")
                    trending_keywords.append(keyword)
        
        print(f"\nTotal trending keywords found: {len(trending_keywords)}")

        print(f"Page title: {page.title()}")
        browser.close()
        
        return trending_keywords

with DAG('crtest', start_date=datetime(2025, 1, 1), schedule='@daily') as dag:
    run_playwright_task = PythonOperator(task_id='run_playwright', python_callable=run_playwright)