"""Tests for the chatbot's conversation memory.

Gemini is replaced by a fake client that records the history it receives, so the tests
run offline and without an API key. Run with `python tests/test_memory.py` or `pytest`.
"""
from pathlib import Path

import google.genai
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "recipe_app.py")

calls = []
fail_next = {"on": False}


class FakeChunk:
    def __init__(self, text):
        self.text = text


class FakeModels:
    def generate_content_stream(self, model, contents, config):
        calls.append({"contents": contents, "config": config})
        if fail_next["on"]:
            fail_next["on"] = False
            raise RuntimeError("503 UNAVAILABLE (fake)")
        yield FakeChunk(f"reply {len(calls)}")


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.models = FakeModels()


google.genai.Client = FakeClient


def roles(contents):
    return [c.role for c in contents]


def texts(contents):
    return [c.parts[0].text for c in contents]


def start_with_recipe(ingredients="chicken, rice, onion"):
    calls.clear()
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    at.text_area[0].input(ingredients)
    at.button[0].click().run()
    assert not at.exception, at.exception
    return at


def test_chat_box_appears_only_after_first_recipe():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert len(at.chat_input) == 0
    at = start_with_recipe()
    assert len(at.chat_input) == 1


def test_first_recipe_sends_form_details_and_system_instruction():
    at = start_with_recipe("paneer, spinach")
    assert roles(calls[0]["contents"]) == ["user"]
    assert "paneer, spinach" in texts(calls[0]["contents"])[0]
    assert "home chef" in calls[0]["config"].system_instruction
    assert [m["role"] for m in at.session_state.messages] == ["user", "assistant"]


def test_follow_up_sees_whole_conversation():
    at = start_with_recipe()
    at.chat_input[0].set_value("Make it vegetarian").run()
    contents = calls[-1]["contents"]
    assert roles(contents) == ["user", "model", "user"]
    assert texts(contents)[1:] == ["reply 1", "Make it vegetarian"]


def test_history_is_capped_and_keeps_original_recipe():
    at = start_with_recipe()
    for i in range(9):
        at.chat_input[0].set_value(f"question {i}").run()
    contents = calls[-1]["contents"]
    r = roles(contents)
    assert len(at.session_state.messages) == 20
    assert len(contents) <= 2 + 10
    assert texts(contents)[0] == texts(calls[0]["contents"])[0]
    assert texts(contents)[1] == "reply 1"
    assert texts(contents)[-1] == "question 8"
    assert all(r[i] != r[i + 1] for i in range(len(r) - 1)), r


def test_failed_reply_is_forgotten():
    at = start_with_recipe()
    before = len(at.session_state.messages)
    fail_next["on"] = True
    at.chat_input[0].set_value("this one fails").run()
    assert len(at.session_state.messages) == before
    assert any("Couldn't get a reply" in e.value for e in at.error)


def test_start_over_clears_memory():
    at = start_with_recipe()
    [b for b in at.button if b.label == "Start over"][0].click().run()
    assert at.session_state.messages == []
    assert len(at.chat_input) == 0


if __name__ == "__main__":
    tests = [f for name, f in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"passed: {test.__name__}")
    print(f"All {len(tests)} tests passed")
