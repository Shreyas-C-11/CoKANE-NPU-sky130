#!/usr/bin/env python3
"""Record build events locally. Does not send mail, chat messages or webhooks."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def read_json(path):
    return json.loads(path.read_text()) if path.is_file() else {}

def snapshot(running=False, exit_code=None):
    active = read_json(ROOT / 'evidence/active-run.json')
    run = ROOT / active.get('run_directory', 'runs/wokwi')
    commit = read_json(run / 'final/commit_id.json').get('commit')
    result = {'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
              'run_directory': str(run), 'source_commit': commit,
              'status': 'running' if running else 'unknown_or_running',
              'fully_verified': False, 'exit_code': exit_code}
    if running:
        result['source_commit'] = None
        result['message'] = 'CPU+MAC hardening started.'
        return result
    log = run / 'flow.log'
    complete = log.is_file() and 'Flow complete.' in log.read_text(errors='replace')
    metrics = read_json(run / 'final/metrics.json')
    required = ['route__drc_errors', 'magic__drc_error__count',
                'design__lvs_error__count', 'route__antenna_violation__count']
    keys = required + [k for k in metrics if
        k.startswith(('timing__setup__wns__corner:', 'timing__hold__wns__corner:',
                      'design__max_slew_violation__count',
                      'design__max_fanout_violation__count',
                      'design__max_cap_violation__count'))]
    selected = {k: metrics[k] for k in keys if k in metrics}
    findings = {k: v for k, v in selected.items() if
                (float(v) < 0 if '__wns' in k else float(v) > 0)}
    missing = [k for k in required if k not in metrics]
    for category in ['setup', 'hold']:
        if not any(k.startswith(f'timing__{category}__wns__corner:') for k in metrics):
            missing.append(f'timing_{category}_corner_results')
    result.update(flow_complete=complete, checks=selected, findings=findings,
                  missing_checks=missing,
                  pending_verification=['pin-level gate simulation', 'SDF timing simulation',
                                        'Tiny Tapeout precheck', 'final sign-off review'])
    if exit_code is not None and exit_code != 0:
        result['status'] = 'failed'
    elif complete:
        result['status'] = 'completed_with_findings' if findings or missing else 'physical_checks_passed_pending_verification'
    elif exit_code == 0:
        result['status'] = 'incomplete'
    result['message'] = ('CPU+MAC build: ' + result['status'] +
                         '. Completion is not full design sign-off.')
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--running', action='store_true')
    parser.add_argument('--exit-code', type=int)
    args = parser.parse_args()
    result = snapshot(args.running, args.exit_code)
    destination = ROOT / 'evidence/build-notification.json'
    destination.parent.mkdir(exist_ok=True)
    prior = read_json(destination)
    destination.with_suffix('.tmp').write_text(json.dumps(result, indent=2) + '\n')
    destination.with_suffix('.tmp').replace(destination)
    if any(prior.get(k) != result.get(k) for k in ['status','source_commit','findings','missing_checks','run_directory']):
        with (ROOT / 'evidence/build-events.jsonl').open('a') as events:
            events.write(json.dumps(result) + '\n')
    print(result['message'])
    print('Status file:', destination)

if __name__ == '__main__':
    main()
