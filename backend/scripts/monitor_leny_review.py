"""Read-only resource sampling around an authenticated HTTP review job."""
import argparse
import json
import time
from verify_leny_v11_production import Monitor
from run_leny_authenticated_review import ROOT, prepare, save


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase')
    parser.add_argument('--expected', type=int, default=6)
    args = parser.parse_args()
    if not args.phase.replace('-', '').isalnum():
        raise SystemExit('Invalid phase')
    prepare()
    started = time.monotonic()
    with Monitor() as monitor:
        while time.monotonic()-started < 1800:
            result = ROOT/'results'/(args.phase+'.json')
            if result.exists() and len(json.loads(result.read_text(encoding='utf-8'))['cases']) >= args.expected:
                break
            time.sleep(2)
    save(ROOT/'results'/('resources-'+args.phase+'.json'), {
        'scope': 'global_machine_samples_not_attributed_to_LENY',
        'seconds': time.monotonic()-started, 'samples': monitor.samples})
    print('Muestras de recursos guardadas:', len(monitor.samples))
