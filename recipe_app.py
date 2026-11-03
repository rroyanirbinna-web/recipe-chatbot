from google.genai import types
from google import genai
import streamlit as st
from dotenv import load_dotenv
load_dotenv()


MODEL = "gemini-3.8-flash"


@st.cache_resource
def get_client():
    return genai.Client()


def build_prompt(ingredients, cuisine, meal, diet, servings, max_time, notes):
    prompt = f"""You are a helpful home chef. Create one recipe using these details.

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


def stream_recipe(prompt):
    stream = get_client().models.generate_content_stream(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.LOW)
        ),
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text


st.set_page_config(page_title="Recipe Generator", page_icon="🍳")
st.title("🍳 Recipe Generator")
st.caption(f"Powered by {MODEL}")

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
        prompt = build_prompt(ingredients, cuisine, meal,
                              diet, servings, max_time, notes)
        try:
            with st.spinner("Cooking up a recipe..."):
                recipe = st.write_stream(stream_recipe(prompt))
            st.download_button("Download recipe", str(recipe),
                               file_name="recipe.md", on_click="ignore")
        except Exception as e:
            st.error(f"Couldn't generate a recipe: {e}")
