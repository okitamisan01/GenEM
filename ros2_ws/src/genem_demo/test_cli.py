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
