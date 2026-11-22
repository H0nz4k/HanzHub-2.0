import os, runpy, sys
from pathlib import Path
root = Path(__file__).parent
runtime = Path('/opt/hanzhub/dashboard/runtime-abd6f63')
sys.path.insert(0, str(runtime))
os.chdir('/opt/hanzhub/dashboard/abd6f63')
page = runpy.run_path(str(Path(sys.argv[1]) if len(sys.argv) > 1 else runtime / 'dashboard-web.py'))['living_glass_home']
html = page(remote=True)
for fixture in ('10 <span>/ 13', '46 <span>°C', 'CPU 12 %', '2 <span>/ 3'):
    assert fixture not in html, fixture
assert 'class="public-dashboard"' in html
assert html.index('src="/dashboard-local.js') < html.index('src="/dashboard-public.js')
assert 'public-data-notice' in html
assert 'src="/dashboard-public.js' not in page(remote=False)
assert 'class="public-dashboard"' not in page(remote=True, demo=True)
print('Render passed: no fixture stats, remote read-only boot, LAN unchanged, explicit demo separate')
