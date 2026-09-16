"""Regression checks for operator-owned platform settings and absence of shared-service writes.

Requires Python/PyYAML/Jinja2 and Node.js. Uses temporary fixture files only.
"""
import copy
import json
from pathlib import Path
import subprocess
import tempfile

from jinja2 import Environment, StrictUndefined
import yaml

ROOT = Path(__file__).resolve().parents[1]
environment = Environment(undefined=StrictUndefined)
environment.filters['to_json'] = json.dumps
context = {
    'inv_addons': {'baikor_r': {'publication': {
        'masterportal': {'config_path': 'config.json', 'services_path': 'services.json'},
        'layer_id': 'baikor-r-construction-sites', 'layer_title': 'Baustellen',
        'workspace': 'operator_data', 'feature_type': 'public_construction_site_areas',
        'search_feature_type': 'public_construction_sites',
    }}},
    'inv_gd': {'domain': 'customer.example'},
    'baikor_geoserver_namespace': {'json': {'namespace': {'uri': 'https://customer.example/custom-namespace'}}},
}
script = environment.from_string((ROOT / 'templates/configure_masterportal.js.j2').read_text()).render(context)
customer_search = {'type': 'specialWfs', 'resultEvents': {'onClick': ['operatorAction']},
                   'definitions': [{'typeName': 'operator_data:trees', 'name': 'Trees'}]}
customer_layer = {'id': 'customer-layer', 'layers': 'operator_data:trees', 'custom': {'retain': True}}
original = {
    'portalConfig': {
        'map': {'mapView': {'startCenter': [100, 200], 'extent': [0, 0, 500, 500], 'zoomLevel': 7}},
        'mainMenu': {'searchBar': {'searchInterfaces': [customer_search]}},
    },
    'layerConfig': {'subjectlayer': {'elements': [
        {'name': 'Baustellen', 'type': 'folder', 'elements': [{'id': 'customer-layer', 'visibility': False}]}
    ]}},
}
with tempfile.TemporaryDirectory(prefix='baikor-portal-test-') as directory:
    folder = Path(directory)
    (folder / 'configure.js').write_text(script)
    for has_search in [True, False]:
        fixture = copy.deepcopy(original)
        if not has_search:
            fixture['portalConfig']['mainMenu']['searchBar']['searchInterfaces'] = []
        (folder / 'config.json').write_text(json.dumps(fixture))
        (folder / 'services.json').write_text(json.dumps([customer_layer]))
        previous = None
        for _ in range(2):
            subprocess.run(['node', 'configure.js', 'config.json', 'services.json'], cwd=folder, check=True, capture_output=True)
            config = json.loads((folder / 'config.json').read_text())
            services = json.loads((folder / 'services.json').read_text())
            assert config['portalConfig']['map'] == original['portalConfig']['map']
            assert services[0] == customer_layer
            assert len(services) == 2
            search = config['portalConfig']['mainMenu']['searchBar']['searchInterfaces'][0]
            if has_search:
                assert search['resultEvents'] == customer_search['resultEvents']
                assert search['definitions'][0] == customer_search['definitions'][0]
            assert 'https://customer.example/custom-namespace' in search['definitions'][-1]['namespaces']
            assert config['layerConfig']['subjectlayer']['elements'][0]['elements'][0] == {'id': 'customer-layer', 'visibility': False}
            if previous:
                assert (config, services) == previous, 'Second run must not duplicate entries'
            previous = (config, services)
    (folder / 'config.json').write_text(json.dumps(original))
    collision = [dict(customer_layer, id='baikor-r-construction-sites')]
    (folder / 'services.json').write_text(json.dumps(collision))
    before = [(folder / path).read_bytes() for path in ['config.json', 'services.json']]
    result = subprocess.run(['node', 'configure.js', 'config.json', 'services.json'], cwd=folder, capture_output=True)
    assert result.returncode != 0
    assert before == [(folder / path).read_bytes() for path in ['config.json', 'services.json']]

all_tasks = '\n'.join(path.read_text() for path in (ROOT / 'tasks').rglob('*.yml'))
for forbidden in ['node_red.yml', '/data/flows.json', '/data/flows_cred.json', 'services/wfs/workspaces', '/rest/reload']:
    assert forbidden not in all_tasks, f'Unexpected shared-service mutation: {forbidden}'
geo_tasks = yaml.safe_load((ROOT / 'tasks/baikor_r/geoserver.yml').read_text())
assert all('kubernetes.core.k8s' not in task for task in geo_tasks), 'GeoServer deployment is operator-owned'
masterportal = (ROOT / 'tasks/baikor_r/masterportal.yml').read_text()
assert 'kubernetes.core.k8s' not in masterportal, 'Masterportal integration only exports controller files'
assert not (ROOT / 'tasks/baikor_r/service_portal.yml').exists(), 'The addon must not manage the Core service portal'
assert 'service_portal' not in all_tasks, 'The addon must not register or update service-portal cards'
defaults = yaml.safe_load((ROOT / 'default_inventory.yml').read_text())['all']['children']['controller']['vars']['inv_addons']['baikor_r']
assert 'node_red' not in defaults
assert 'service_portal' not in defaults
assert defaults['publication']['enable'] is False
assert defaults['imports']['service_account']['enable'] is False
print('PASS: existing map, searches and layers preserved; no Node-RED, service-portal or shared GeoServer deployment writes.')
