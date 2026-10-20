"""Local preparation must not overwrite reviewed files or enable physical motion."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_connection', REPO / 'scripts/prepare_hsr_connection.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def deployment_root(tmp_path):
    (tmp_path / 'config').mkdir()
    (tmp_path / 'config/hsr_hardware.example.yaml').write_text(
        (REPO / 'config/hsr_hardware.example.yaml').read_text())
    return tmp_path


def test_preparation_stays_unverified_and_uses_portable_container_paths(deployment_root):
    root = deployment_root
    paths = module.prepare(root, 'eth_test', '192.0.2.104', 104)
    assert len(paths) == 3
    profile = yaml.safe_load(paths[1].read_text())
    assert profile['verified'] is False
    env = paths[2].read_text()
    assert 'ROS_DOMAIN_ID=104' in env and 'rmw_cyclonedds_cpp' in env
    assert 'file:///root/genem_config/' in env
    document = ET.parse(paths[0])
    nodes = list(document.iter())
    assert any(x.attrib.get('name') == 'eth_test' for x in nodes)
    assert any(x.attrib.get('Address') == '192.0.2.104' for x in nodes)
    original = [p.read_bytes() for p in paths]
    with pytest.raises(ValueError, match='already exists'):
        module.prepare(root, 'other', '192.0.2.105', 105)
    assert [p.read_bytes() for p in paths] == original


@pytest.mark.parametrize('interface,ip,domain', [('eth bad', '192.0.2.1', 104),
    ('eth0', 'invalid', 104), ('eth0', '192.0.2.1', 233), ('eth0', '192.0.2.1', -1)])
def test_invalid_settings_write_nothing(deployment_root, interface, ip, domain):
    with pytest.raises(ValueError):
        module.prepare(deployment_root, interface, ip, domain)
    assert not list(deployment_root.rglob('*.local.*'))


def test_copy_known_working_dds_without_changing_source(deployment_root):
    known = deployment_root / 'known.xml'
    original = '<CycloneDDS><Domain/></CycloneDDS>'
    known.write_text(original)
    paths = module.prepare(deployment_root, 'eth0', '192.0.2.1', 104, known)
    assert paths[0].read_text() == original and known.read_text() == original
