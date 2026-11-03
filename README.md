# Recipe Chatbot

A Streamlit app that turns the ingredients you have into a recipe using Google's Gemini
model, then lets you keep chatting about it ("make it vegetarian", "I don't have an oven")
while it remembers the conversation.

## Features

- A form for ingredients, cuisine, meal type, dietary preference, servings, time limit and notes
- The recipe streams in as it is generated, formatted in Markdown
- Follow-up chat with conversation memory
- Download the latest reply as a Markdown file, or **Start over** to clear the memory
- Automatic retries for temporary Gemini errors such as 503 "model overloaded"

## How to run

Developed with Python 3.14 and Streamlit 1.65. You need a Gemini API key from
[Google AI Studio](https://aistudio.google.com/apikey).

```bash
git clone https://github.com/rroyanirbinna-web/recipe-chatbot.git
cd recipe-chatbot
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, put your key in `GOOGLE_API_KEY`, then start the app:

```bash
streamlit run recipe_app.py
```

## How the memory works

The Gemini API is stateless: it only knows what you send in each request. Streamlit is
stateless too, because it reruns the whole script on every interaction. So the app stores the
conversation in `st.session_state.messages`, a list of `{"role", "content"}` dictionaries that
survives reruns. On every turn, `build_history()` converts the stored messages into Gemini's
format (`user` / `model` roles) and sends them along with the new message.

## Design decisions

1. **Bounded memory.** The model always sees the original request and the first recipe, plus the
   10 most recent follow-up messages (`MAX_FOLLOW_UPS`). Long chats stay fast and cheap, and the
   model never loses the recipe the conversation is about. If trimming would leave two model
   messages in a row, the extra one is dropped so roles keep alternating.
2. **A system instruction instead of a prompt prefix.** The "home chef" role and the rule "reply
   to changes with the full updated recipe" live in Gemini's `system_instruction`, so they apply
   to every turn rather than only the first message.
3. **Memory stays consistent when a call fails.** If Gemini returns an error, the unanswered
   message is removed from memory, so the next question isn't paired with a missing reply.
   Each request also has a 60-second timeout and up to 3 attempts, so a busy or unresponsive API
   ends in a clear error instead of a spinner that never stops.

## Tests

The tests replace Gemini with a fake client that records the history it receives, so they run
offline and need no API key. They use Streamlit's `AppTest` to drive the app headlessly.

```bash
python tests/test_memory.py
```

They check that the chat box only appears after the first recipe, that follow-ups include the
whole conversation, that the history is capped while keeping the original recipe, that failed
replies are forgotten, and that **Start over** clears the memory.

## Limitations

- Memory lasts for one browser tab: refreshing or closing the page clears it. Nothing is stored
  in a database.
- Recipes are AI-generated, so check allergens, cooking times and food safety yourself.
- The model name (`gemini-3.8-flash`) is a constant at the top of `recipe_app.py`.
