from google.genai import types
from google import genai
import streamlit as st
from dotenv import load_dotenv
load_dotenv()


MODEL = "gemini-3.8-flash"
# Memory limit: the model always sees the original request and first recipe,
# plus this many of the most recent follow-up messages
MAX_FOLLOW_UPS = 10

SYSTEM_INSTRUCTION = """You are a helpful home chef.
When the user asks to change the recipe, reply with the full updated recipe in the same Markdown format.
When they ask a cooking question, answer briefly and keep it about the current recipe."""


@st.cache_resource
def get_client():
    # Retry temporary errors like 503 "model overloaded" a few times before giving up,
    # and don't wait forever if the API stops responding
    return genai.Client(http_options=types.HttpOptions(
        timeout=60_000,
        retry_options=types.HttpRetryOptions(attempts=3)))


def build_prompt(ingredients, cuisine, meal, diet, servings, max_time, notes):
    prompt = f"""Create one recipe using these details.

Ingredients I have: {ingredients}
Cuisine: {cuisine}
Meal type: {meal}
Dietary preference: {diet}
Servings: {servings}
Maximum total time: {max_time} minutes
"""
    if notes:
        prompt += f"Extra notes: {notes}\n"
    prompt += """
You may add common pantry staples (salt, oil, spices) but keep extra ingredients to a minimum.

Format the answer in Markdown:
## <Recipe name>
A one-line description.
**Prep time / Cook time / Servings**
### Ingredients
(bulleted list with quantities)
### Instructions
(numbered steps)
### Tips
(1-3 short tips)
"""
    return prompt


def build_history(messages):
    recent = messages[2:][-MAX_FOLLOW_UPS:]
    # Start the recent part on a user message so roles keep alternating
    if recent and recent[0]["role"] == "assistant":
        recent = recent[1:]
    return [
        types.Content(role="model" if m["role"] == "assistant" else "user",
                      parts=[types.Part(text=m["content"])])
        for m in messages[:2] + recent
    ]


def stream_reply(messages):
    stream = get_client().models.generate_content_stream(
        model=MODEL,
        contents=build_history(messages),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW)
        ),
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text


def respond():
    with st.chat_message("assistant"):
        try:
            with st.spinner("Cooking up a reply..."):
                reply = st.write_stream(stream_reply(st.session_state.messages))
        except Exception as e:
            st.error(f"Couldn't get a reply: {e}")
            # Forget the unanswered message so the conversation stays consistent
            st.session_state.messages.pop()
            return
    st.session_state.messages.append({"role": "assistant", "content": str(reply)})


def clear_chat():
    st.session_state.messages = []


st.set_page_config(page_title="Recipe Generator", page_icon="🍳")
st.title("🍳 Recipe Generator")
st.caption(f"Powered by {MODEL}. After your recipe arrives, ask follow-ups; it remembers the conversation.")

st.session_state.setdefault("messages", [])

with st.form("recipe_form"):
    ingredients = st.text_area(
        "What ingredients do you have?",
        placeholder="e.g. chicken, rice, onion, garlic, tomatoes",
    )
    col1, col2 = st.columns(2)
    with col1:
        cuisine = st.selectbox(
            "Cuisine",
            ["Any", "Indian", "Italian", "Chinese", "Mexican",
                "Thai", "Japanese", "Mediterranean", "American"],
        )
        diet = st.selectbox(
            "Dietary preference",
            ["None", "Vegetarian", "Vegan", "Gluten-free", "Keto", "High-protein"],
        )
    with col2:
        meal = st.selectbox(
            "Meal type", ["Any", "Breakfast", "Lunch", "Dinner", "Snack", "Dessert"])
        servings = st.number_input(
            "Servings", min_value=1, max_value=12, value=2)
    max_time = st.slider("Maximum time (minutes)", 10, 120, 30, step=5)
    notes = st.text_input(
        "Anything else?", placeholder="e.g. spicy, no oven, kid-friendly")
    submitted = st.form_submit_button("Generate recipe", type="primary")

if submitted:
    if not ingredients.strip():
        st.warning("Please enter at least one ingredient.")
    else:
        # A new recipe starts a new conversation
        prompt = build_prompt(ingredients, cuisine, meal,
                              diet, servings, max_time, notes)
        summary = f"{ingredients.strip()} · {cuisine} · {meal} · {diet} · {servings} servings · up to {max_time} min"
        st.session_state.messages = [
            {"role": "user", "content": prompt, "display": summary}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message.get("display", message["content"]))

if st.session_state.messages:
    follow_up = st.chat_input(
        "Ask a follow-up, e.g. make it vegetarian", submit_mode="disable")
    if follow_up:
        st.session_state.messages.append(
            {"role": "user", "content": follow_up})
        with st.chat_message("user"):
            st.markdown(follow_up)

# Answer the newest message: a new recipe request or a follow-up
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    respond()

if st.session_state.messages:
    with st.container(horizontal=True):
        st.download_button("Download latest reply", st.session_state.messages[-1]["content"],
                           file_name="recipe.md", icon=":material/download:", on_click="ignore")
        st.button("Start over", icon=":material/restart_alt:", on_click=clear_chat)
