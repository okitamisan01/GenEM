from genem_demo.cli import main


def test_cli_hsr_disabled(capsys):
    assert main(['--hsr', '--yes', '--scenario', 'nod']) == 2
    assert 'HSR execution disabled' in capsys.readouterr().out


def test_cli_mock_feedback(tmp_path):
    assert main(['--mock', '--yes', '--scenario', 'nod', '--feedback', 'slower',
                 '--log', str(tmp_path / 'log.jsonl')]) == 0
    assert len((tmp_path / 'log.jsonl').read_text().splitlines()) == 2


def test_cli_decline(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr('builtins.input', lambda _: 'n')
    assert main(['--scenario', 'nod', '--log', str(tmp_path / 'log.jsonl')]) == 0
    assert 'MOCK head_nod' not in capsys.readouterr().out


def test_interactive_unknown_then_hello(monkeypatch, tmp_path, capsys):
    answers = iter(['h8', 'hello', 'y', ''])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    assert main(['--mock', '--log', str(tmp_path / 'history.jsonl')]) == 0
    output = capsys.readouterr().out
    assert 'Unsupported input:' in output
    assert 'MOCK look_at' in output and 'MOCK head_nod' in output


def test_interactive_quit_after_unknown(monkeypatch, tmp_path):
    answers = iter(['h8', 'quit'])
    monkeypatch.setattr('builtins.input', lambda _: next(answers))
    log = tmp_path / 'history.jsonl'
    assert main(['--mock', '--log', str(log)]) == 0
    assert not log.exists()


def test_noninteractive_unknown_still_fails(tmp_path):
    assert main(['--instruction', 'h8', '--yes',
                 '--log', str(tmp_path / 'history.jsonl')]) == 2


def test_cli_ros_motion_never_accepts_yes(capsys):
    assert main(['--sim', '--yes', '--scenario', 'nod']) == 2
    assert '--yes is forbidden' in capsys.readouterr().out
