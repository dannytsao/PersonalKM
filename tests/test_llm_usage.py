from pathlib import Path

from personalkm.llm import alerts, usage


def test_usage_report_notify_calls_alert(monkeypatch, tmp_path: Path, capsys):
    sent = []
    monkeypatch.setattr(usage, "USAGE_FILE", tmp_path / "usage.json")
    monkeypatch.setattr(usage, "RUNTIME_DIR", tmp_path)
    monkeypatch.setattr(alerts, "notify_usage_report", lambda text: sent.append(text))

    usage.record("ollama", 10, 5)
    exit_code = usage.main(["report", "--notify"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "ollama" in out
    assert len(sent) == 1
    assert "ollama" in sent[0]
