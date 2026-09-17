"""Contrats frontend qui protègent la traçabilité des réponses."""

from pathlib import Path

APP_JS = (Path(__file__).resolve().parents[2] / "frontend" / "app.js").read_text()


def test_frontend_does_not_inject_unsourced_glossary():
    assert "const GLOSS =" not in APP_JS
    assert "GLOSS_FALC" not in APP_JS


def test_frontend_does_not_send_assistant_answers_back_as_context():
    assert 'S.history.push({ role: "assistant"' not in APP_JS


def test_unknown_copy_does_not_promise_unsourced_contacts():
    assert "Voici vers qui vous tourner" not in APP_JS
    assert "Voici qui peut vous aider" not in APP_JS


def test_simplified_packet_uses_falc_view_and_can_restore_detailed_packet():
    assert (
        "function botBubble(ans, question, falcView = S.falc, alternateAnswer = null)"
        in APP_JS
    )
    assert "const copy = falcView ? T_FALC : T_STD;" in APP_JS
    assert 'const path = falcView ? "/api/chat" : "/api/chat/simplify";' in APP_JS
    assert "botBubble(ans2, question, !falcView, ans)" in APP_JS


def test_simplification_replaces_the_whole_answer_packet():
    section = APP_JS.split('body.querySelector(".simplify-btn")', 1)[1].split(
        "const fu =", 1
    )[0]
    assert "b.remove()" in section
    assert "botBubble(ans2, question, !falcView, ans)" in section
    assert 'querySelectorAll("p, ol")' not in section


def test_frontend_healthcheck_uses_ipv4_loopback():
    dockerfile = (
        Path(__file__).resolve().parents[2] / "docker" / "Dockerfile.front"
    ).read_text()
    assert "http://127.0.0.1/" in dockerfile
    assert "http://localhost/" not in dockerfile
