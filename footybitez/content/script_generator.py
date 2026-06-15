import os
import time
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)


def _get_keys(prefix: str) -> list:
    """Collect all non-empty env vars named PREFIX, PREFIX2, PREFIX3 …"""
    keys = []
    for suffix in ["", "2", "3"]:
        val = os.getenv(f"{prefix}{suffix}")
        if val:
            keys.append(val)
    return keys


class ScriptGenerator:
    def __init__(self):
        self.gemini_keys = _get_keys("GEMINI_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        if not self.gemini_keys:
            logger.warning("No GEMINI_API_KEY found. Will rely on Groq or Wikipedia fallback.")

    def _try_gemini(self, prompt: str) -> dict | None:
        """Try all Gemini keys in order using new google-genai SDK."""
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            logger.error("google-genai not installed. Run: pip install google-genai>=1.0.0")
            return None

        for i, key in enumerate(self.gemini_keys):
            for model_name in ["gemini-2.5-flash", "gemini-1.5-pro"]:
                try:
                    logger.info(f"Trying Gemini key #{i+1} model={model_name}...")
                    client = genai.Client(api_key=key)
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.7,
                            thinking_config=types.ThinkingConfig(thinking_budget=0)
                        )
                    )
                    text = response.text.strip()
                    # Strip markdown code fences if present
                    if text.startswith("```"):
                        text = text.split("\n", 1)[-1]
                    if text.endswith("```"):
                        text = text.rsplit("```", 1)[0]
                    data = json.loads(text.strip())
                    if self._validate_script_data(data):
                        logger.info(f"Gemini key #{i+1} ({model_name}) succeeded.")
                        return data
                except Exception as e:
                    logger.warning(f"Gemini key #{i+1} model={model_name} failed: {e}")
        return None

    def generate_script(self, topic, category="General", context=None):
        """
        Generates a short video script using Groq (priority), Gemini, or Wikipedia fallback.
        """
        # 0. Fetch Context for Factual Grounding (skip for What If?)
        if context is None:
            context = ""
            if category != "What If?":
                context = self._fetch_context(topic)
                if context and context != "__NO_CONTEXT__":
                    logger.info(f"Fetched factual context for grounding ({len(context)} chars).")
                elif context == "__NO_CONTEXT__":
                    logger.warning("Context fetch failed after retries — proceeding in conservative mode.")
        else:
            logger.info("Using provided custom grounding context.")

        prompt = self._get_prompt(topic, category, context=context)

        # 1. Try Groq (preferred for factual accuracy)
        if self.groq_api_key:
            try:
                from groq import Groq
                client = Groq(api_key=self.groq_api_key)
                logger.info(f"Generating script with Groq (Llama3) for category: {category}...")
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1024,
                    response_format={"type": "json_object"}
                )
                text = completion.choices[0].message.content
                data = json.loads(text)
                if self._validate_script_data(data):
                    logger.info("Groq generation successful.")
                    return self._sanitize_visual_keywords(data)
            except Exception as e:
                logger.error(f"Groq generation failed: {e}")

        # 2. Try Gemini (new SDK)
        if self.gemini_keys:
            logger.info(f"Generating script with Gemini for category: {category}...")
            result = self._try_gemini(prompt)
            if result:
                return self._sanitize_visual_keywords(result)

        # 3. Fallback: Wikipedia
        logger.warning("All AI models failed. Converting to Wikipedia Mode.")
        return self._get_wikipedia_script(topic)

    def _fetch_context(self, topic):
        """
        Fetches background info from Wikipedia to ground the LLM in facts.
        Retries once with a simplified query if the first attempt fails.
        Returns '__NO_CONTEXT__' sentinel if both attempts fail.
        """
        import wikipedia
        import re

        def _do_fetch(query):
            clean = query.replace("Most clutch", "").replace("Top 5", "").replace("Why", "").strip()
            clean = re.split(r'[:?]', clean)[0].strip()
            potential_entities = [clean]
            for joiner in [" vs ", " and ", " versus ", " & "]:
                if joiner in clean.lower():
                    potential_entities = clean.lower().split(joiner)
                    break

            full_context = []
            seen_pages = set()

            for ent in potential_entities[:2]:
                try:
                    ent = ent.strip()
                    if not ent or len(ent) < 2:
                        continue

                    search_query = ent.lower().replace("football", "soccer")
                    if "soccer" not in search_query and "association" not in search_query:
                        search_query += " soccer"

                    search_res = wikipedia.search(search_query, results=1)
                    if not search_res:
                        continue

                    page_title = search_res[0]
                    if page_title in seen_pages:
                        continue
                    seen_pages.add(page_title)

                    page = wikipedia.page(page_title, auto_suggest=False)
                    context_parts = [f"ENTITY: {page.title}\nSUMMARY: {page.summary[:700]}"]

                    sections = page.sections
                    for target in ["Honours", "Career statistics", "Club career",
                                   "International career", "Records", "Rules"]:
                        match = next((s for s in sections if target.lower() in s.lower()), None)
                        if match:
                            try:
                                sec_text = page.section(match)
                                if sec_text:
                                    context_parts.append(f"--- {match.upper()} ---\n{sec_text[:800]}")
                            except Exception:
                                continue

                    full_context.append("\n".join(context_parts))
                    if len("\n\n".join(full_context)) > 4000:
                        break

                except Exception as e:
                    logger.warning(f"Failed to fetch context for {ent}: {e}")
                    continue

            return "\n\n=====\n\n".join(full_context) if full_context else None

        # First attempt
        try:
            result = _do_fetch(topic)
            if result:
                return result
        except Exception as e:
            logger.warning(f"Context fetch attempt 1 failed: {e}")

        # Retry with simplified query (just the raw topic)
        logger.info("Retrying context fetch with simplified query...")
        try:
            result = _do_fetch(topic.split(":")[0].split("?")[0])
            if result:
                return result
        except Exception as e:
            logger.warning(f"Context fetch attempt 2 failed: {e}")

        return "__NO_CONTEXT__"

    def _get_prompt(self, topic, category, context=""):
        """Generates the prompt based on the category."""

        base_style = "High energy, 'Did you know?' style."

        # ── Player verification rule (injected for all player-related categories) ──────
        PLAYER_CATEGORIES = {"Comparisons & Debates", "Football Stories", "Rankings & Lists",
                             "World Cup & Stats", "Shocking Moments", "Money & Transfers", "wc_upcoming"}
        is_player_category = category in PLAYER_CATEGORIES
        is_comparison = category == "Comparisons & Debates"

        import datetime as _dt
        _current_year = _dt.datetime.now().year

        PLAYER_VERIFICATION_RULE = f"""
        CRITICAL PLAYER ACCURACY RULES (current year: {_current_year}):
        - Transfer windows happen every summer and winter. Player clubs change frequently.
        - NEVER state a player's current club as fact unless you are 100% certain it is
          still true RIGHT NOW in {_current_year}.
        - If uncertain about a player's current club, say "at [club] at the time" or omit the club.
        - For stats: ALWAYS use season-specific language ("in the 2023-24 season, X scored Y")
          NOT present-tense claims ("X scores Y goals per season for Z club").
        - Key verified transfers: Kylian Mbappe joined Real Madrid in summer 2024 (left PSG).
          Do NOT describe Mbappe as playing for PSG. He is at Real Madrid.
        """ if is_player_category else ""
        extra_instructions = (
            "CRITICAL GLOBAL RULE: Focus strictly on major Men's Football (e.g. English Premier League, "
            "La Liga, Champions League, World Cup, Saudi Pro League, MLS).\n"
            "STRICT GENDER RULE: Content is ONLY about MEN'S football. NEVER mention women's football, "
            "women's national teams, NWSL, WSL, or female players. This is non-negotiable.\n"
            "CRITICAL SPECIFICITY RULE: NEVER use generic pronouns like 'a team', 'a player', "
            "'this club', or 'a certain match'. You MUST explicitly name the exact club (e.g., 'Real Madrid'), "
            "the exact player (e.g., 'Lionel Messi'), and the exact score or year in EVERY sentence. "
            "Be ultra-specific.\n"
        )

        if category == "Football Stories":
            base_style = "Narrative storytelling, dramatic, emotional."
            extra_instructions = "Focus on the hero's journey: rise, fall, and redemption (if applicable). Make the viewer feel the emotion."
        elif category == "Mysteries & Dark Side":
            base_style = "Suspenseful, investigative, slightly dark."
            extra_instructions = "Build tension. Use words like 'unexplained', 'vanished', 'shocking'. Focus on the unknown."
        elif category == "Comparisons & Debates":

            base_style = "Analytical but controversial, engaging."
            extra_instructions = (
                "Present stats for Side A, then Side B. End with a question to provoke comments.\n"
                "COMPARISON VISUAL RULE: Each segment MUST have TWO separate visual_keywords — "
                "one for each subject being compared. Use the format: "
                '"visual_keyword": "[Player A full name] action"  and in the next segment '
                '"visual_keyword": "[Player B full name] action". '
                "Do NOT combine both subjects into one search query."
            )
        elif category == "What If?":
            base_style = "Imaginative, hypothetical, 'alternate history'."
            extra_instructions = "Describe the scenario vividly. Use 'Imagine a world where...'. Focus on the ripple effects."
        elif category == "Tactics & IQ":
            base_style = "Educational, smart, inside scoop."
            extra_instructions = "Explain complex ideas simply. Use analogies. Make the viewer feel like an expert."
        elif category == "Shocking Moments":
            base_style = "Viral, explosive, reaction-heavy."
            extra_instructions = "Build up to the moment. Describe the exact split-second it happened."
        elif category == "Rankings & Lists":
            base_style = "Fast-paced, countdown style."
            extra_instructions = (
                "CRITICAL: TOPICS MUST BE ABOUT FOOTBALL (SOCCER) PLAYERS/TEAMS. "
                "For EVERY item on the list, EXPLICITLY state their full name, club, and exact numbers. "
                "Do NOT say 'One player did this...' Say 'In 2012, Lionel Messi scored 91 goals...'"
            )
        elif category == "World Cup & Stats":
            base_style = "Informative, epic, data-driven."
            extra_instructions = "Use impressive numbers. Highlight the scale of the event. Connect history to modern day."
        elif category == "wc_upcoming":
            base_style = "Pre-match preview, high anticipation, data-driven."
            extra_instructions = (
                "Highlight the upcoming match date and significance.\n"
                "You MUST discuss:\n"
                "1. Head-to-head records/history between the teams.\n"
                "2. Winning probabilities or prediction statistics from the context.\n"
                "3. Key players or recent form indicators.\n"
                "End with an engaging question inviting predictions in the comments."
            )

        import datetime
        current_year = datetime.datetime.now().year

        # Build factual grounding section
        no_context = (not context) or context == "__NO_CONTEXT__"
        if no_context:
            factual_grounding = f"""
            NOTE: No external factual context is available for this topic.
            Use only your training knowledge. Be CONSERVATIVE — omit any statistic, fee,
            or figure you are not certain about. Use descriptive language instead
            (e.g. 'multiple trophies', 'around X goals') rather than guessing exact numbers.
            Current Year: {current_year}.
            """
        else:
            factual_grounding = f"""
            GROUND TRUTH CONTEXT (Use this as your ONLY source for facts/numbers/dates):
            \"\"\"{context}\"\"\"

            STRICT FACTUAL RULES (Current Year: {current_year}):
            1. Use the PROVIDED CONTEXT for all statistics, trophies, and dates.
            2. If you mention a formation (e.g. 4-4-2), ensure the math makes sense: 10 outfielders + 1 Goalkeeper = 11 players TOTAL.
            3. DO NOT HALLUCINATE. If context says Messi has 4 UCL titles, DO NOT say 7.
            4. If a specific number is not in the context, use descriptive terms (e.g., 'multiple titles', 'many records') instead of guessing.
            5. ALWAYS prioritize the MOST RECENT information. Check the first few sentences of context for a player's CURRENT club.
            6. Accuracy is more important than drama.
            """

        strict_accuracy = f"""
        STRICT ACCURACY RULES (apply to ALL categories — non-negotiable):
        A. Only include players/teams that GENUINELY fit the topic definition.
           "One-season wonder" = exceptional ONE season then significant decline/departure.
           Do NOT include players with sustained multi-season success.
        B. NEVER invent or estimate transfer fees, contract values, or bonus amounts.
           Only state a fee if you are certain of the figure. If uncertain, omit entirely.
        C. Every statistic (goals, assists, points) must be real and verifiable.
           If not certain, use "around X goals" or omit the number.
        D. The script must stay ON TOPIC for ALL entries. Do not drift to adjacent topics.
        E. Target word count: 130-150 words total across hook + segments + outro.
           Count your words before returning. Do NOT exceed 160 words.
        """

        VISUAL_KEYWORD_RULES = """
VISUAL KEYWORD RULES — MANDATORY (image search will fail if these are violated):
- Every visual_keyword MUST reference a specific named player, club, stadium, or event.
- ALWAYS include the player's FULL NAME and club name in the query.
- ALWAYS end with "soccer" or "football" to confirm sport context.
- For national team scenes: use "[Country] men national football team [year]" format.
  GOOD: "Brazil men national football team 2002 World Cup"
  BAD: "Brazil football", "national team trophy"
- For player scenes: use "[Full name] [club] soccer [year/action]"
  GOOD: "Cristiano Ronaldo Real Madrid soccer 2018 bicycle kick"
  BAD: "footballer celebrating", "player goal"
- FORBIDDEN words in visual_keyword: "nfl", "american", "rugby", "women", "female",
  "cricket", "hockey", "basketball", "tennis", "golf", "ladies", "girl"
- NEVER use just "football" or "soccer" alone — always add the entity name.
"""

        return f"""
        {factual_grounding}
        {strict_accuracy}
        {PLAYER_VERIFICATION_RULE}
        {VISUAL_KEYWORD_RULES}

        Create a viral YouTube Short script about: "{topic.replace('football', 'soccer')}".
        STRICT DEFINITION: This video is STRICTLY about Association Football (Soccer).
        Ignore all American Football, Music, or Rugby associations.
        Category: {category}
        Style: {base_style}
        {extra_instructions}

        CRITICAL OUTPUT FORMAT — return ONLY valid JSON with this exact structure:
        {{
            "hook": "The first 3 seconds hook text (max 10 words)",
            "primary_entity": "Name of the main person or club (e.g. Lionel Messi, Real Madrid)",
            "segments": [
                {{ "text": "Sentence 1...", "visual_keyword": "search term 1" }},
                {{ "text": "Sentence 2...", "visual_keyword": "search term 2" }}
            ],
            "outro": "Call to action text"
        }}

        Rules:
        1. "hook": Must be shocking/intriguing but FACTUALLY ACCURATE.
        2. "primary_entity": EXTRACT the exact name of the main subject.
        3. "segments": Split whenever the VISUAL SUBJECT changes. NO FICTION.
        4. "visual_keyword": Specific search term. 
           - ALWAYS include the FULL name of the player or club. 
           - If talking about a country, use "[Country] National Team soccer" (e.g. "Brazil National Team soccer").
           - Be extremely specific about the action.
           BAD: "football", "trophy", "brazil"
           GOOD: "Lionel Messi holding world cup trophy", "Real Madrid fans celebrating", "Brazil National Team 2002 World Cup"
           STRICT RULE: Do NOT use generic terms. If talking about Brazil's world cup win, the keyword MUST be "Brazil National Team World Cup Trophy".
        5. HIGHLIGHTING: Enclose these in asterisks (*):
           - Player Names (*Messi*, *Ronaldo*)
           - Club/Country Names (*Real Madrid*, *Brazil*)
           - Stadium/Place Names (*Camp Nou*, *London*)
           - ALL Numerical Values (*7*, *1999*, *90+5*, *first*, *billion*)
           - Superlatives (*Best*, *Fastest*, *Legend*)
        """

    def _sanitize_visual_keywords(self, script_data: dict) -> dict:
        """
        Post-processing safety net: scans every segment's visual_keyword and
        replaces any that contain wrong-sport or wrong-gender terms.
        This runs AFTER the LLM response — it's the last line of defense.
        """
        BAD_KW = [
            "nfl", "gridiron", "american football", "superbowl", "touchdown",
            "rugby", "cricket", "hockey", "nhl", "baseball", "basketball",
            "tennis", "golf", "boxing", "women", "woman", "female", "ladies",
            "girl", "nwsl", "wsl", "nwt", "womens",
        ]
        primary = script_data.get("primary_entity", "football")
        fallback_kw = f"{primary} association football soccer men"

        segments = script_data.get("segments", [])
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            kw = seg.get("visual_keyword", "")
            kw_lower = kw.lower()
            for bad in BAD_KW:
                if bad in kw_lower:
                    logger.warning(
                        f"[Sanitizer] Rejected visual_keyword '{kw}' — contains '{bad}'. "
                        f"Replacing with fallback: '{fallback_kw}'"
                    )
                    seg["visual_keyword"] = fallback_kw
                    break  # One replacement per segment is enough

        return script_data

    def _validate_script_data(self, data):
        if "hook" in data and "segments" in data:
            new_segments = []
            for s in data["segments"]:
                if isinstance(s, str):
                    new_segments.append({"text": s, "visual_keyword": "football"})
                else:
                    new_segments.append(s)
            data["segments"] = new_segments

            if "primary_entity" not in data:
                data["primary_entity"] = ""

            full_text = f"{data['hook']} {' '.join([s['text'] for s in data['segments']])} {data.get('outro', '')}"

            lower_text = full_text.lower()
            refusal_phrases = [
                "does not mention",
                "no mention of",
                "context does not contain",
                "cannot satisfy",
                "do not have information",
                "not provided in the context"
            ]
            for phrase in refusal_phrases:
                if phrase in lower_text:
                    logger.warning(f"AI Refusal Detected in Script: {full_text[:100]}...")
                    return False

            data['full_text'] = full_text
            return True
        return False

    def _get_wikipedia_script(self, topic):
        """Fetches a summary from Wikipedia and structures it as a script."""
        try:
            import wikipedia
            search_res = wikipedia.search(topic, results=1)
            if not search_res:
                raise Exception("No wikipedia results")

            page = wikipedia.page(search_res[0], auto_suggest=False)
            sentences = page.summary.split('. ')

            hook = f"Did you know this about *{page.title}*?"
            final_segments = []
            count = 0
            for s in sentences:
                if len(s) < 20:
                    continue
                clean_s = s.strip()
                if not clean_s.endswith('.'):
                    clean_s += '.'

                words = clean_s.split()
                highlighted_s = []
                for w in words:
                    if w.isdigit() or page.title.split()[0] in w:
                        highlighted_s.append(f"*{w}*")
                    else:
                        highlighted_s.append(w)

                final_segments.append({
                    "text": " ".join(highlighted_s),
                    "visual_keyword": f"{page.title} football context"
                })
                count += 1
                if count >= 3:
                    break

            return {
                "hook": hook,
                "segments": final_segments,
                "outro": "Subscribe for more verified facts!",
                "full_text": f"{hook} {' '.join([s['text'] for s in final_segments])}"
            }

        except Exception as e:
            logger.error(f"Wikipedia fallback failed: {e}")
            return {
                "hook": f"Here is a crazy fact about *{topic}*!",
                "segments": [
                    {"text": f"*{topic}* is a true legend of football.", "visual_keyword": f"{topic} player"},
                    {"text": "Their story inspires millions around the globe.", "visual_keyword": "football stadium crowd"}
                ],
                "outro": "Comment below!",
                "full_text": f"Here is a crazy fact about {topic}!"
            }


    def generate_breaking_news_script(self, topic: str, event: dict) -> dict | None:
        """
        Generates a 120-140 word breaking news script for match result Shorts.
        Used by the BreakingNewsPipeline.

        Rules:
        - 120-140 words total (hook + segments + outro)
        - Incorporates detailed match statistics (possession, shots, fouls, cards, corner kicks)
        - Mentions goalscorers with minute of goal
        - Tone: urgent, fast, detailed match breakdown
        - Facts only, strictly grounded in input data
        """
        import datetime as _dt
        current_year = _dt.datetime.now().year

        home = event.get("home", "")
        away = event.get("away", "")
        hs = event.get("home_score", 0)
        as_ = event.get("away_score", 0)

        # Build event context string from API-Football/Gemini events
        event_lines = []
        for ev in event.get("api_events", []):
            ev_type = ev.get("type", "")
            player = ev.get("player", {}).get("name", "")
            minute = ev.get("time", {}).get("elapsed", "?")
            detail = ev.get("detail", "")
            if ev_type == "Goal":
                event_lines.append(f"  GOAL {minute}': {player}")
            elif ev_type == "Card" and detail == "Red Card":
                event_lines.append(f"  RED CARD {minute}': {player}")
            elif ev_type == "Card" and detail == "Yellow Card":
                event_lines.append(f"  YELLOW CARD {minute}': {player}")
        event_context = "\n".join(event_lines) if event_lines else "No detailed event data available."

        # Format stats
        stats = event.get("stats", {})
        stats_str = ""
        if stats:
            stats_str = json.dumps(stats, indent=2)
        else:
            stats_str = "No detailed match statistics available."

        prompt = f"""
        You are a football news anchor. Generate a detailed BREAKING NEWS YouTube Short script about a recently finished match.

        MATCH: {home} {hs}–{as_} {away} (World Cup 2026)
        
        MATCH STATS:
        {stats_str}
        
        MATCH TIMELINE & EVENTS:
        {event_context}

        STRICT RULES:
        1. WORD COUNT: The script MUST be between 120 and 140 words total across hook + segments + outro. This is extremely important. Count the words and ensure they fit this range.
        2. Hook: Start with a strong hook (max 10 words) stating the final result.
        3. Match Review: Describe how the match played out. To hit the word count target, each segment MUST contain at least 2 to 3 detailed, descriptive sentences (around 20 to 25 words per segment). Highlight who dominated, possession percentages, shots, shots on target, fouls, corners, offsides, and cards (yellow/red) from the provided stats.
        4. Visuals: Split the script into 4 to 6 segments. Each segment should have a unique, highly specific "visual_keyword".
        5. Visual Keywords Rule: To ensure we get real photos of this specific match from the internet:
           - Every keyword MUST include the team names and the World Cup 2026 context.
           - Examples: "{home} vs {away} World Cup 2026 match action", "{home} fans celebrating 2026 World Cup", "[Scorer Name] goal {home} vs {away} 2026".
           - DO NOT use generic stock terms. Only use terms that target the real match and players.
        6. Outro: End with an engaging question for the comments.
        7. HIGHLIGHTING: Enclose the following in asterisks (*):
           - Player Names (e.g., *Messi*, *Ronaldo*)
           - Team/Country Names (e.g., *Japan*, *Netherlands*)
           - All Numerical Values (e.g., *2-0*, *62%*, *12*, *first*, *45'*)
           - Superlatives (e.g., *Best*, *Legend*, *Unbelievable*)
        8. FACTS ONLY. Do not speculate or hallucinate stats. If a statistic is not in the provided match data, do not mention it.

        Return ONLY valid JSON:
        {{
            "hook": "The scoreline hook (max 10 words)",
            "primary_entity": "Winning team or match name",
            "segments": [
                {{"text": "Sentence 1 and Sentence 2 describing the game flow/events with highlighting...", "visual_keyword": "specific real match query"}},
                {{"text": "Sentence 1 and Sentence 2 detailing scorers/cards with highlighting...", "visual_keyword": "specific real match query"}},
                {{"text": "Sentence 1 and Sentence 2 breaking down the stats like possession and shots on target with highlighting...", "visual_keyword": "specific real match query"}},
                {{"text": "Sentence 1 and Sentence 2 summarizing the tactical impact or aftermath with highlighting...", "visual_keyword": "specific real match query"}}
            ],
            "outro": "Engaging call to action outro (e.g. Follow for the full breakdown. Who was your player of the match?)"
        }}
        """
        attempt_prompt = prompt
        data = None
        result = None
        
        for attempt in range(3):
            if self.groq_api_key:
                try:
                    from groq import Groq
                    client = Groq(api_key=self.groq_api_key)
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": attempt_prompt}],
                        temperature=0.3,
                        max_tokens=1024,
                        response_format={"type": "json_object"}
                    )
                    data = json.loads(completion.choices[0].message.content)
                    if self._validate_script_data(data):
                        hook = data.get("hook", "")
                        segments_text = " ".join([seg.get("text", "") for seg in data.get("segments", []) if isinstance(seg, dict)])
                        outro = data.get("outro", "")
                        word_count = len(f"{hook} {segments_text} {outro}".strip().split())
                        
                        if 120 <= word_count <= 140:
                            logger.info(f"Breaking news script generated via Groq (attempt {attempt+1}) with {word_count} words.")
                            return data
                        else:
                            logger.warning(f"Groq script word count {word_count} out of range (120-140). Retrying...")
                            attempt_prompt = prompt + f"\n\nSTRICT REQUIREMENT: Your previous attempt was {word_count} words. You MUST write longer, more detailed descriptions in each segment's text to reach a total word count of between 120 and 140 words. Make each of the 4 segments contain exactly 2-3 long, descriptive sentences!"
                except Exception as e:
                    logger.error(f"Breaking news Groq generation failed: {e}")

            if self.gemini_keys:
                result = self._try_gemini(attempt_prompt)
                if result:
                    hook = result.get("hook", "")
                    segments_text = " ".join([seg.get("text", "") for seg in result.get("segments", []) if isinstance(seg, dict)])
                    outro = result.get("outro", "")
                    word_count = len(f"{hook} {segments_text} {outro}".strip().split())
                    if 120 <= word_count <= 140:
                        logger.info(f"Breaking news script generated via Gemini (attempt {attempt+1}) with {word_count} words.")
                        return result
                    else:
                        logger.warning(f"Gemini script word count {word_count} out of range (120-140). Retrying...")
                        attempt_prompt = prompt + f"\n\nSTRICT REQUIREMENT: Your previous attempt was {word_count} words. You MUST write longer, more detailed descriptions in each segment's text to reach a total word count of between 120 and 140 words. Make each of the 4 segments contain exactly 2-3 long, descriptive sentences!"

        # Fallback to the last generated script even if it was outside target range
        logger.warning("Could not hit exact 120-140 word count range after 3 attempts. Returning last attempt.")
        if data:
            return data
        if result:
            return result

        logger.error("Breaking news script generation failed on all providers.")
        return None


if __name__ == "__main__":
    try:
        generator = ScriptGenerator()
        script = generator.generate_script("Lionel Messi")
        print(script)
    except Exception as e:
        print(f"Setup failed: {e}")
