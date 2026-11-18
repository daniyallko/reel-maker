from app.providers.gemini import GEMINI_MODEL


def test_gemini_model_is_available_to_new_users():
    assert GEMINI_MODEL == "gemini-3.5-flash-lite"
