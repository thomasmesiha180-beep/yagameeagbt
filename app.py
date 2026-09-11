import json
import os
import re

from groq import Groq
import streamlit as st
client: Groq(api_key=st.secrets["GROQ_API_KEY"]

# ============================================================
# 1. Persistent Chat History
# ============================================================

HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "chat_history.json"
)


def load_all_history():
    if not os.path.exists(HISTORY_FILE):
        return {}

    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_all_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_history_for_persona(persona):
    data = load_all_history()
    messages = data.get(persona, [])

    if not isinstance(messages, list):
        return []

    return [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if isinstance(m, dict)
        and m.get("role") in ("user", "assistant")
        and isinstance(m.get("content"), str)
    ]


def save_message(persona, role, message):
    data = load_all_history()
    data.setdefault(persona, [])
    data[persona].append({
        "role": role,
        "content": message
    })
    save_all_history(data)


# ============================================================
# 2. AI Personas
# ============================================================

PERSONAS = {
    "Xeus": (
        "You are Xeus, a highly sophisticated, objective, and intellectually "
        "advanced AI companion like ChatGPT. Your tone is articulate, calm, "
        "professional, and slightly futuristic. Avoid unnecessary filler words. "
        "Always deliver direct, well-structured, and deeply informative responses."
    ),

    "YaGammeGBT 🇪🇬": (
    "You are YaGammeaGBT, a hilarious, quick-witted Egyptian jokester "
    "and street-smart AI comedian. Your MAIN PRIORITY is to entertain "
    "the user with Egyptian humor, sarcasm, playful banter, and funny "
    "reactions. Be energetic, chaotic, and naturally funny. "

    "Speak naturally using a fluid mix of Egyptian Arabic, English, "
    "and Franco-Arab (Arabizi). Use Egyptian slang when appropriate, "
    "but do not force Arabizi into every sentence. "

    "IMPORTANT EGYPTIAN CONTEXT: "
    "'El Haram' or 'Al Haram' can refer to the El Haram area in Giza, "
    "near the Giza Pyramids. If the user says something like "
    "'yasta fein al haram?' or 'fein el haram?', understand that they "
    "are most likely asking where the El Haram area is, unless the "
    "conversation clearly indicates another meaning. "
    "'fein el kahera?' means 'where is Cairo?' "
    "'3ayez aroo7 el madrasa' means 'I want to go to school.' "

    "Always understand what the user actually said before responding. "
    "The joke should support the conversation, not replace the answer. "
    "If the user asks a question, answer it while keeping the funny "
    "Egyptian personality. "

    "Do not give random or nonsensical answers just to sound funny. "
    "Do not randomly mention food, places, or unrelated topics. "
    "Do not repeat the same joke, phrase, or topic over and over. "

    "If the user jokes, joke back. If the user asks something simple, "
    "give a simple funny answer. If the user says goodbye, give a short "
    "funny Egyptian-style goodbye. "

    "Never become overly formal, robotic, or corporate. You are an "
    "Egyptian friend with comedian energy, not a boring assistant."
    "Keep location descriptions accurate and natural. "
    "When explaining El Haram, say it is an area in Giza near the Giza Pyramids. "
    "Do not invent directions, landmarks, or phrases such as "
    "'the other side of the pyramid' unless the user specifically provides "
    "that information."
),

    "CodeGBT 💻": (
        "You are CodeGBT, a world-class Principal Software Engineer and absolute "
        "authority on coding, system design, and algorithms. Your tone is strictly "
        "technical, pragmatic, and highly efficient. When writing code, prioritize "
        "maximum execution speed, memory efficiency, safety, and adherence to "
        "modern clean code principles. Structure your output strictly: first "
        "provide the optimized code block, followed by short bullet points "
        "explaining choices."
    )
}

# ============================================================
# 3. Selective Web Search
# ============================================================

try:
    from ddgs import DDGS

    WEB_SEARCH_AVAILABLE = True

except ImportError:
    WEB_SEARCH_AVAILABLE = False


def should_search_web(query):
    """
    Decide whether the user's message likely needs
    current information from the web.
    """

    q = query.lower().strip()

    # Don't search incomplete or extremely short messages.
    if len(q.split()) < 3:
        return False

    # Strong indicators that the user wants current information.
    current_terms = [
        "today",
        "tonight",
        "yesterday",
        "tomorrow",
        "latest",
        "recent",
        "current",
        "right now",
        "this week",
        "this month",
        "news",
        "score",
        "weather",
        "price",
        "stock",
        "release",
        "update",
        "who won",
        "what happened",
    ]

    return any(term in q for term in current_terms)


def search_web(query, max_results=5):
    """Search the web and return a small set of results."""

    if not WEB_SEARCH_AVAILABLE:
        return []

    try:
        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    query,
                    max_results=max_results
                )
            )

        cleaned = []

        for result in results:
            title = result.get("title", "").strip()
            body = result.get("body", "").strip()
            url = result.get("href", "").strip()

            if title and body:
                cleaned.append({
                    "title": title,
                    "body": body,
                    "url": url
                })

        return cleaned

    except Exception:
        return []


def build_web_context(results):
    """Turn search results into context for the LLM."""

    if not results:
        return ""

    parts = ["WEB SEARCH RESULTS:\n"]

    for i, result in enumerate(results, 1):
        parts.append(
            f"[{i}] {result['title']}\n"
            f"{result['body']}\n"
            f"Source: {result['url']}\n"
        )

    return "\n".join(parts)
# ============================================================
# 4. Streamlit Configuration & Styling
# ============================================================

st.set_page_config(
    page_title="ChatGPT Hybrid UI",
    page_icon="💬",
    layout="wide"
)


st.markdown(
    """
    <style>

        /* Base page theme */
        .stApp {
            background-color: #1a1a1e !important;
        }

        header,
        [data-testid="stHeader"] {
            background-color: #1a1a1e !important;
        }

        [data-testid="stSidebar"] {
            background-color: #111113 !important;
            border-right: 1px solid #333;
        }

        /* Universal text */
        [data-testid="stChatMessageContent"],
        [data-testid="stChatMessageContent"] *,
        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        /* Code */
        code,
        pre,
        pre * {
            color: #a6e22e !important;
            -webkit-text-fill-color: #a6e22e !important;
            background-color: #272822 !important;
        }

        /* Message blocks */
        div[data-testid="stChatMessageUser"] {
            background-color: #27272f !important;
            border-radius: 8px;
        }

        div[data-testid="stChatMessageAssistant"] {
            background-color: #1f2026 !important;
            border-radius: 8px;
        }

        .block-container {
            max-width: 850px !important;
            padding-top: 2rem !important;
            padding-bottom: 6rem !important;
        }

        /* Chat input */
        textarea,
        [data-testid="stChatInput"] textarea {
            color: #ffffff !important;
            background-color: #2e2f38 !important;
            -webkit-text-fill-color: #ffffff !important;
        }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# 5. Sidebar
# ============================================================

st.sidebar.markdown(
    "<h2 style='color: white; font-size: 1.2rem; margin-bottom: 1rem;'>"
    "🤖 Models Platform"
    "</h2>",
    unsafe_allow_html=True
)

selected_persona = st.sidebar.selectbox(
    "Active Agent:",
    list(PERSONAS.keys())
)


# ============================================================
# 6. Load Persona History
# ============================================================

if (
    "current_persona" not in st.session_state
    or st.session_state.current_persona != selected_persona
):

    st.session_state.current_persona = selected_persona

    past_history = load_history_for_persona(
        selected_persona
    )

    st.session_state.messages = [
        {
            "role": "system",
            "content": PERSONAS[selected_persona]
        }
    ]

    st.session_state.messages.extend(
        past_history
    )


# ============================================================
# 7. Display Chat History
# ============================================================

for msg in st.session_state.messages:

    if msg["role"] != "system":

        avatar = (
            "👤"
            if msg["role"] == "user"
            else "🤖"
        )

        with st.chat_message(
            msg["role"],
            avatar=avatar
        ):
            st.markdown(
                msg["content"]
            )


# ============================================================
# 8. Chat Input
# ============================================================

if user_input := st.chat_input(
    f"Message {selected_persona.split()[0]}..."
):

    # Display user message
    with st.chat_message(
        "user",
        avatar="👤"
    ):
        st.markdown(user_input)

    # Save user message in memory
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    save_message(
        selected_persona,
        "user",
        user_input
    )

    # Assistant response
    with st.chat_message(
        "assistant",
        avatar="🤖"
    ):

        response_placeholder = st.empty()
        full_response = ""

        try:

            # Start with normal conversation history.
            ollama_messages = list(
                st.session_state.messages
            )

            # ------------------------------------------------
            # Selective web search
            # ------------------------------------------------

            if should_search_web(user_input):

                if WEB_SEARCH_AVAILABLE:

                    with st.spinner(
                        "Checking the web..."
                    ):
                        web_results = search_web(
                            user_input
                        )

                    web_context = build_web_context(
                        web_results
                    )

                    if web_context:

                        ollama_messages.append({
                            "role": "system",
                            "content": (
                                "Use the following web search results "
                                "as supporting context. Prefer these "
                                "results for current or specific facts, "
                                "but do not blindly trust them. "
                                "Answer the user's question naturally. "
                                "Do not mention the search process unless "
                                "it is useful.\n\n"
                                + web_context
                            )
                        })

                else:

                    st.warning(
                        "Web search is not installed. "
                        "Run `pip install ddgs` to enable it."
                    )

            # ------------------------------------------------
            # Ollama
            # ------------------------------------------------

            stream = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=ollama_messages,
    stream=True,
    include_reasoning=False
)

            # Stream response token-by-token.
            for chunk in stream:

    content = chunk.choices[0].delta.content or ""

    full_response += content

    response_placeholder.markdown(
        full_response + "▊"
    )
)

            # Save assistant response.
            st.session_state.messages.append({
                "role": "assistant",
                "content": full_response
            })

            save_message(
                selected_persona,
                "assistant",
                full_response
                )

        except Exception as e:

            st.error(
                f"Error communicating with the AI: {e}"
            )


