import sys
from unittest.mock import MagicMock, patch
from streamlit.testing.v1 import AppTest

APP = __file__.replace("tests/test_app.py", "app.py")


def run(env, fake=None, turns=1):
    with patch.dict("os.environ", env, clear=False):
        at = AppTest.from_file(APP, default_timeout=30)
        with patch("openai.OpenAI", return_value=fake or MagicMock()):
            at.run()
            for i in range(turns):
                at.chat_input[0].set_value(f"msg {i}").run()
    return at


LIVE = {"AIKI_API_KEY": "k", "AIKI_BASE_URL": "http://x", "AIKI_MODEL": "m"}


def fake_ok():
    f = MagicMock()
    f.chat.completions.create.return_value.choices = [MagicMock(message=MagicMock(content="ok"))]
    return f


def table(md):
    # table_to_csv lives in app.py; read it through an AppTest-free import of the source
    ns = {}
    src = open(APP).read()
    start = src.index("def table_to_csv")
    exec("import csv, io, re\n" + src[start:src.index("# ---------- Sidebar")], ns)
    return ns["table_to_csv"](md)


def test_escaped_pipe_and_dash_row():
    out = table("| a | b |\n|---|---|\n| x \\| y | z |\n| - | : |")
    assert out.splitlines() == ["a,b", "x | y,z", "-,:"]


def test_no_table():
    assert table("just text") is None


def test_error_not_leaked_or_resent():
    f = MagicMock()
    f.chat.completions.create.side_effect = RuntimeError("SECRET-URL")
    at = run(LIVE, f, turns=2)
    assert "SECRET-URL" not in " ".join(m["content"] for m in at.session_state.messages)
    sent = f.chat.completions.create.call_args.kwargs["messages"]
    assert all("went wrong" not in m["content"] for m in sent)


def test_history_capped():
    f = fake_ok()
    run(LIVE, f, turns=20)
    assert len(f.chat.completions.create.call_args.kwargs["messages"]) <= 13  # system + 12


def test_missing_model_is_demo():
    env = {**LIVE, "AIKI_MODEL": ""}
    at = run(env)  # message is sent inside run(), while the env patch is active
    assert "Demo mode" in at.session_state.messages[-1]["content"]
