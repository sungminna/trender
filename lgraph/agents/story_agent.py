from dotenv import load_dotenv
from langgraph.prebuilt import create_react_agent
from langchain.tools import Tool

from utils.prompt_loader import get_prompt, prompt_loader
from utils.message_formatter import stream_and_print

load_dotenv()


def create_story_agent():
    """Korean Podcast Story Agent를 생성합니다. 프롬프트는 파일에서 동적으로 로드됩니다."""
    story_prompt = get_prompt("story_agent")
    
    return create_react_agent(
        model="openai:gpt-4.1-mini",
        tools=[
            # 현재는 별도 도구 없음 - 리서치 결과를 바탕으로 한국어 팟캐스트 스크립트 생성
        ],
        prompt=story_prompt,
        name="korean_podcast_story_agent",
    )


def reload_story_agent():
    """
    프롬프트를 다시 로드하여 Korean Podcast Story Agent를 재생성합니다.
    서비스 운영 중 프롬프트 업데이트 시 호출하세요.
    """
    global story_agent
    print("Reloading Korean podcast story agent with updated prompt...")
    story_agent = create_story_agent()
    print("Korean podcast story agent reloaded successfully!")
    return story_agent


def get_available_prompts():
    """사용 가능한 프롬프트 목록을 반환합니다."""
    return prompt_loader.list_available_prompts()


# Korean Podcast Story Agent 인스턴스 생성
story_agent = create_story_agent()

# 테스트 실행
if __name__ == "__main__":
    # 테스트용 샘플 리서치 결과 (한국어 팟캐스트용)
    sample_research_result = """
    ## EXECUTIVE SUMMARY

The role of the United States in conflicts involving Iran has been multifaceted and has evolved over several decades, culminating recently in direct military interventions within the Iran-Israel conflict in 2025. Historically, the US's interactions with Iran date back to the 1953 CIA-orchestrated coup against Iran’s democratically elected Prime Minister Mossadegh, ensuing decades of support for the Shah of Iran, and severe diplomatic ruptures following the 1979 Iranian Revolution and the hostage crisis.

During the 1980-1988 Iran-Iraq War, the US supported Iraq with arms and intelligence to counterbalance Iran, despite the war’s devastating human toll. The relationship was further strained by incidents such as the US Navy's downing of Iran Air Flight 655 in 1988. Since then, US policy toward Iran has included economic sanctions, paramilitary covert actions, and diplomatic containment efforts focused on Iran’s nuclear program.

Most recently, tensions peaked in 2025 when, after failed diplomacy and accelerating Iranian nuclear enrichment, the US escalated its involvement by launching airstrikes on Iranian nuclear facilities alongside Israeli forces—the first direct US military strikes inside Iran in decades. These strikes utilized advanced bunker-buster munitions aimed at crippling Iran’s uranium enrichment capability. This action marked a highly significant shift from previous indirect involvement to overt military engagement, generating wide international concern over potential regional escalation.

Public opinion worldwide reflects deep divisions, with allies urging restraint and opponents condemning US action as escalating conflict risks. Meanwhile, Iran has vowed retaliation, raising fears of protracted conflict with unpredictable consequences. The US role, shaped by a history of covert operations, proxy conflicts, and diplomatic tensions, continues to be central in the geopolitics of the Middle East, making the evolving US-Iran dynamic a critical subject for comprehensive analysis and storytelling.

---

### SELECTED EXCERPTS

> "The U.S. military struck three Iranian nuclear sites in June 2025, joining Israel's campaign to cripple Iran's nuclear program. The strikes were described as a 'spectacular military success' but raised fears of wider regional conflict." — LA Times, 2025

> "The US supported Iraq during the Iran-Iraq War by supplying arms and intelligence to counterbalance Iran, despite the war’s devastating effects and controversies such as the 1988 downing of Iran Air Flight 655." — Wikipedia

> "The 1979 Iran Hostage Crisis severely damaged US-Iran relations, shifting US policy towards sanctions, diplomatic isolation and a focus on countering Iran's regional influence and nuclear ambitions." — Council on Foreign Relations timeline

> "US direct military intervention in Iran during the 2025 Israel-Iran conflict represents a shift from previous indirect and covert US actions to overt engagement, markedly escalating tensions in the region." — Foreign Affairs analysis

---

## TIMELINE

- **1953**: CIA-backed coup ousts Iranian PM Mossadegh, installs Shah Mohammad Reza Pahlavi, beginning decades of US influence in Iran.
- **1979**: Iranian Revolution topples Shah; US embassy hostage crisis begins, lasting 444 days, irreparably damaging relations.
- **1980-1988**: Iran-Iraq War — US supports Iraq with arms, intelligence, and economic aid; downing of Iran Air Flight 655 by US Navy in 1988 kills 290 civilians.
- **1990s-2000s**: Sanctions intensify, covert operations and proxy conflicts escalate amid Iranian nuclear program concerns.
- **2015**: JCPOA nuclear deal signed; US withdraws in 2018 under President Trump, re-imposing sanctions.
- **Early 2020s**: US-Iran incidents escalate including drone strikes, assassination of Iranian General Qassem Soleimani (2020), and naval confrontations.
- **June 13, 2025**: Israeli strikes intensify on Iranian nuclear and missile sites; US shifts military assets closer to Middle East.
- **June 21, 2025**: US conducts airstrikes on Iran's Fordow, Natanz, and Isfahan nuclear sites, marking first direct military involvement; using B-2 stealth bombers and bunker buster bombs.
- **June 22, 2025**: Global outcry and calls for diplomacy; Iran vows retaliation; fears grow of wider regional conflict.

---

### SELECTED EXCERPTS

> "On July 3, 1988, the U.S. Navy's USS Vincennes mistakenly shot down Iran Air Flight 655, killing all 290 aboard, sparking international tension." — Wikipedia

> "US strike on June 21, 2025, known as Operation Midnight Hammer, marked the first operational use of 30,000-pound bunker buster bombs against Iranian nuclear sites." — Fox News

> "The 1979 hostage crisis became a defining rupture between US and Iran, leading to sanctions and decades of hostile relations." — Council on Foreign Relations

> "Iran’s 2025 responses to US and Israeli airstrikes include threats of retaliation, escalating the conflict to unprecedented levels." — Institute for the Study of War

---

## KEY STAKEHOLDERS

- **United States Government and Military**: Actors shaping policy from CIA’s early covert actions to Pentagon-led strikes in 2025; key figures include Presidents, Defense Secretaries, and military commanders.
- **Iranian Government and Military**: Including Supreme Leader Ayatollah Khamenei, the Revolutionary Guard Corps, and Iranian nuclear scientists and military assets targeted in strikes.
- **Israel**: Regional ally to the US, engaged in direct conflict with Iran; coordinated military efforts with US; Prime Minister Netanyahu a vocal advocate of regime change in Iran.
- **International Community**: United Nations, European Union, global powers (China, Russia), Gulf States, and organizations calling for diplomatic solutions.
- **Regional Proxy Groups**: Hezbollah, Houthi rebels, militias in Iraq and Syria allied with Iran or influenced by US presence, crucial players in the ongoing proxy struggle.
- **Civilian Populations & Hostages**: Iranian civilians suffering in wars, American diplomats in Iran during the hostage crisis, wider populations affected by conflict and economic sanctions.
- **Experts & Analysts**: Academics, strategists, journalists shaping public understanding and policy debates.

---

### SELECTED EXCERPTS

> "The US military's decisions are coordinated across multiple agencies, directed by the President and Pentagon leadership, currently focused on Iran’s nuclear threat." — LA Times, 2025

> "Iran's Supreme Leader Khamenei has become a target in rhetoric, with Israeli officials calling for regime change." — The Intercept, 2025

> "Arab Gulf States navigate complex alliances with both the US and Iran, balancing security and economic interests amid rising tensions." — Responsible Statecraft

> "Proxy militias such as Hezbollah and Kataib Hezbollah increase attacks on US and regional interests in response to US actions against Iran." — Institute for the Study of War

---

## NARRATIVE ELEMENTS

The US role in Iranian conflicts is a dramatic saga combining covert operations, proxy wars, diplomacy, and direct military action. From covert CIA orchestration to the hostage crisis trauma, secret arms deals during the Iran-Iraq war, up to the 2025 airstrikes as part of an escalating confrontation involving Israel, these storylines form a complex geopolitical tragedy.

Key dramatic moments include the hostage crisis’ personal terror and international diplomatic crisis; the 1988 downing of Iran Air Flight 655 causing mass civilian deaths; US support for brutal chemical warfare during the Iran-Iraq war; backchannels and betrayals in the Iran-Contra scandal; the assassination of General Soleimani, a defining recent flare-up; and the recent unprecedented US airstrikes on Iranian soil, risking full-scale war.

Themes of power, betrayal, revenge, and ideological conflict prevail alongside human costs: suffering families, hostages, soldiers, and civilians trapped in broader agendas.

Compelling characters include leaders wielding enormous influence but burdened by global consequences: Presidents Carter, Reagan, Trump; Supreme Leaders Khomeini and Khamenei; Qassem Soleimani; and the unknown civilians caught amidst shifting policies.

Moral tensions between national security and international law, between diplomacy and warfare, and debates about American interventionism versus regional sovereignty imbue the narrative with ethical complexity.

---

### SELECTED EXCERPTS

> "Hostage crisis survivors recounted years of captivity, influencing US public opinion and hardening attitudes towards Iran." — Council on Foreign Relations

> "The US covertly armed both sides during the Iran-Iraq war, creating a tragic stalemate with widespread casualties." — Wikipedia

> "Assassination of General Soleimani in 2020 marked a turning point, increasing hostilities and fears of war." — Foreign Affairs

> "The 2025 airstrikes create a new chapter, risking escalation while spotlighting US-Israel strategic partnership against Iran." — CNN

---

## PUBLIC OPINION & SENTIMENT

Public sentiment surrounding the US role in Iran conflicts is deeply polarized. In the US and allied countries, a significant portion of the population supports measures to curb Iran’s nuclear ambitions, often viewing Iran as a dangerous regime threatening regional and global security. Conversely, critics warn against endless military interventions, citing high costs and destabilizing effects, advocating diplomatic solutions.

Within Iran, government-controlled media and public opinion largely frame the US as an aggressive imperialist power, reinforcing nationalist resolve and portraying attacks as existential threats. Iranian diaspora and activists have varied views, some urging human rights and reform, others opposing regime policies.

Internationally, reactions vary from calls for restraint and peace by the UN and European nations to vocal condemnations and sanctions by US allies. Regional populations experience divided opinions, influenced by sectarian and geopolitical alignments, with Gulf states wary yet reliant on US security guarantees.

Social media amplifies both supportive and critical voices, with viral hashtags, protests, and misinformation shaping evolving public discourse. Fabricated narratives and conspiracy theories proliferate, deepening divides.

---

### SELECTED EXCERPTS

> "Polling data shows 45% of Americans supporting military action to prevent Iran obtaining nuclear weapons, while 40% favor diplomacy first." — NamuWiki

> "International social media campaigns have used hashtags like #NoWarWithIran and #PeaceInMiddleEast to protest escalation." — News Reports 2025

> "Iranian state media called the US strikes a 'declaration of war,' mobilizing public solidarity." — Institute for the Study of War

> "New Zealand, China, and many global actors condemned the US strikes, urging restraint and renewed talks." — The Sun Chronicle

---

## MOMENTUM & FORECAST

Since June 2025, US involvement in the Iran-Israel conflict marked by direct military strikes signals a surge in momentum toward potential broader conflict. The US military presence in the Middle East has increased with deployments protecting allies and US assets. Diplomatic talks have faltered amid escalating violence.

Experts foresee several possible trajectories: escalation into wider regional war involving Gulf states and proxies; prolonged stalemate with continual low-intensity conflicts; or potential return to diplomatic negotiations depending on leadership changes or external pressures.

The risk of miscalculation remains high due to Iran's asymmetrical warfare capabilities and proxy strength. US domestic opinion and congressional oversight are also crucial variables influencing future policy decisions.

Emerging sub-trends include cyber warfare escalation, proxy clashes in Iraq and Yemen, and international moves either toward sanctions expansion or peace negotiations.

The public and international community remain watchful with nervous anticipation, debating morality and strategy in what could be another 'forever war.'

---

### SELECTED EXCERPTS

> "The battle for air superiority and covert cyber strikes suggest a new, tech-led phase of US-Iran conflict." — BulgarianMilitary.com 2025

> "The U.S. Congress debates the legality and support for the President’s war powers, with bipartisan calls for restraint." — The Intercept

> "Iran’s willingness to retaliate raises risks of attacks on US bases and shipping routes like the Strait of Hormuz." — Foreign Affairs

---

## METHODOLOGY

- Conducted 20 search queries across NewsSearch, WebSearch, and NamuSearch.
- Used queries such as "미국 이란 전쟁 최신 소식", "US Iran conflict timeline detailed", "미국 이란 갈등 연대기", "Iran-Iraq war US role history", and "recent years US Iran tensions timeline."
- Sources included established news outlets (LA Times, CNN, AP, Fox News), academic and policy analysis (CFR, Foreign Affairs), Wikipedia, and Korean NamuWiki for local perspectives.
- Triangulated facts on US military operations, political statements, and timeline events.
- Extracted direct quotes for narrative color and authenticity.
- Identified gaps in detailed public opinion polls and integrated social media sentiment from recent news reports.
- Reviewed political stakes regarding international diplomacy and US congressional involvement.

---

### SELECTED EXCERPTS

> "This report utilized multiple reputable English-language and Korean sources to ensure breadth and accuracy." — Research Summary

> "Search queries included a balance of factual, timeline, and opinion angles." — Methodology Notes

---

## CULTURAL & CONTEXTUAL ANALYSIS

The US-Iran conflict sits at the crossroads of global geopolitical power struggles and regional ethnic, religious, and ideological tensions. US policy toward Iran historically reflects Cold War dynamics, oil geopolitics, and post-9/11 security concerns.

Culturally, Iranian society views US actions through a lens of foreign intervention and national resilience, with enduring memories of 1979 upheavals and the Iran-Iraq war trauma. American public opinion grapples with war weariness and national security fears.

Generational divides manifest in Iran's youth showing protest movements for reform despite government rigidity, while older generations often maintain nationalist sentiments.

Socioeconomic consequences of sanctions and war have deeply affected civilian populations, embedding a humanitarian dimension to otherwise strategic conflicts.

Globally, the US-Iran conflict influences oil markets, migration flows, and international security alliances, with ripple effects in diplomacy, terrorism, and global multilateralism.

The conflict is thus not only a military or political issue but a profound cultural and social flashpoint with far-reaching lasting implications.

---

### SELECTED EXCERPTS

> "The 1979 Revolution remains a defining moment in Iranian national identity, shaping responses to US policy." — CFR

> "In the US, war fatigue contrasts with concerns over preventing nuclear proliferation, creating political tensions." — Foreign Affairs

> "Regional sectarian divisions influence alliances, complicating peacemaking efforts." — Responsible Statecraft

> "Sanctions have deeply impacted Iranian society, but also fueled nationalist resistance." — NamuWiki

---

# SOURCE LIST

### Executive Summary and Timeline
- LA Times: https://www.latimes.com/world-nation/story/2025-06-21/the-latest-us-joins-israeli-air-campaign-and-strikes-3-nuclear-sites-in-iran
- Council on Foreign Relations Timeline: https://www.cfr.org/timeline/us-relations-iran-1953-2025
- Wikipedia Iran-US relations: https://en.wikipedia.org/wiki/Iran%E2%80%93United_States_relations
- CNN conflict timeline: https://edition.cnn.com/interactive/2025/06/world/us-iran-conflict-timeline-dg/
- Fox News Operation Midnight Hammer: https://www.foxnews.com/world/full-breakdown-operation-midnight-hammer-largest-b-2-operational-strike-us-history

### Stakeholders and Narratives
- The Intercept: https://theintercept.com/2025/06/21/iran-israel-united-states-war/
- Responsible Statecraft: https://responsiblestatecraft.org/iraq-iran-israel-war/
- Foreign Affairs: https://www.foreignaffairs.com/middle-east/americas-war-iran

### Public Opinion and Momentum
- The Sun Chronicle: https://www.thesunchronicle.com/news/nation_world/nations-react-to-us-strikes-on-iran-with-calls-for-diplomacy/article_3704f4f5-0300-5d6e-8346-eb3d9adf5419.html
- BulgarianMilitary.com: https://bulgarianmilitary.com/2025/06/22/us-airstrikes-on-irans-sites-what-happened-and-whats-next/
- Institute for the Study of War: https://www.understandingwar.org/backgrounder/iran-update-special-report-june-21-2025-evening-edition

### Cultural Context
- Council on Foreign Relations: https://www.cfr.org/
- NamuWiki (Korean local context): https://namu.wiki/w/%EC%9D%B4%EB%9E%80%20%EC%A0%84%EC%9F%81
- Foreign Affairs, Responsible Statecraft

---

### DONE
    """
    
    stream_and_print(
        story_agent,
        [{"role": "user", "content": f"""다음 리서치 결과를 바탕으로 ElevenLabs Eleven V3 TTS에 최적화된 한국어 팟캐스트 스크립트를 만들어줘. 
        
한국 청중에게 흥미롭고 문화적으로 적절하며, 감정적인 오디오 태그가 잘 통합된 완전한 팟캐스트 내러티브를 제작해줘:

{sample_research_result}"""}]
    )
