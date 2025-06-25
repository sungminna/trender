from tavily import TavilyClient
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Tavily client
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def _format_search_results(response: dict, search_type: str = "") -> str:
    """
    Common function to format search results for ReAct Agent consumption.
    Returns clean, structured text that's easy for OpenAI models to parse.
    """
    try:
        results = []
        
        # Add search summary if answer exists
        if response.get('answer'):
            results.append("SEARCH SUMMARY:")
            results.append(f"{response['answer']}")
            results.append("")
        
        # Add search results
        if response.get('results'):
            results.append(f"DETAILED SEARCH RESULTS ({len(response['results'])} items):")
            results.append("")
            
            for i, result in enumerate(response['results'], 1):
                results.append(f"[Result {i}]")
                results.append(f"Title: {result.get('title', 'N/A')}")
                results.append(f"URL: {result.get('url', 'N/A')}")
                results.append(f"Content: {result.get('content', 'N/A')}")
                if search_type:
                    results.append(f"Source: {search_type}")
                results.append("")
        
        return "\n".join(results)
    
    except Exception as e:
        return f"Error processing search results: {str(e)}"

def web_search(query: str) -> str:
    """일반 웹 검색; 지난 주간의 일반 웹 페이지를 검색합니다."""
    try:
        response = tavily_client.search(
            query=query,
            max_results=3,
            topic="general",
            include_answer=True,
            include_raw_content=True,
            include_images=False,
            search_depth="advanced",
            chunks_per_source=5,
            time_range="week"
        )
        
        return _format_search_results(response, "General Web")
        
    except Exception as e:
        return f"Error during web search: {str(e)}"

def news_search(query: str) -> str:
    """최신 뉴스 검색; 지난 하루 동안의 뉴스 기사"""
    try:
        response = tavily_client.search(
            query=query,
            max_results=3,
            topic="news",
            include_answer=True,
            include_raw_content=True,
            include_images=False,
            search_depth="advanced",
            chunks_per_source=5,
            time_range="day"
        )
        
        return _format_search_results(response, "News")
        
    except Exception as e:
        return f"Error during news search: {str(e)}"

def namu_search(query: str) -> str:
    """namu.wiki 전문 검색; 지난 한 달간 namu.wiki 문서를 검색합니다"""
    try:
        response = tavily_client.search(
            query=query,
            max_results=3,
            topic="general",
            include_answer=True,
            include_raw_content=True,
            include_images=False,
            search_depth="advanced",
            chunks_per_source=5,
            time_range="month",
            include_domains=["namu.wiki"]
        )
        
        return _format_search_results(response, "NamuWiki")
        
    except Exception as e:
        return f"Error during namu search: {str(e)}"