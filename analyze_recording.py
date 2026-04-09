import sys, os, io, json, time, re, base64, shutil
from pathlib import Path
from PIL import Image
from openadapt_ml.ingest.capture import capture_to_episode
from anthropic import Anthropic

SCRIPTS_DIR = Path(r'C:/Users/Administrator/AppData/Local/Python/pythoncore-3.14-64/Scripts')
OUTPUT_DIR = Path(r'C:/scripts/analysis')
SEND_W, SEND_H = 1280, 800

def analyze(capture_name):
    capture_path = SCRIPTS_DIR / capture_name
    if not capture_path.exists():
        print(f'ERROR: Capture not found: {capture_path}')
        sys.exit(1)

    output = OUTPUT_DIR / capture_name
    output.mkdir(parents=True, exist_ok=True)

    print(f'Loading capture: {capture_name}')
    ep = capture_to_episode(str(capture_path))
    print(f'Found {len(ep.steps)} steps')

    client = Anthropic()
    steps_report = []

    for i, step in enumerate(ep.steps):
        action = step.action
        action_type = action.type.value if hasattr(action.type, 'value') else str(action.type)
        coords = action.normalized_coordinates
        text = action.text

        img_path = None
        if step.observation and step.observation.screenshot_path:
            src = Path(step.observation.screenshot_path)
            if src.exists():
                img_path = output / f'step_{i+1:02d}.png'
                shutil.copy2(src, img_path)

        action_desc = f'{action_type}'
        if coords:
            action_desc += f' at ({coords[0]:.3f}, {coords[1]:.3f})'
        if text:
            action_desc += f' text="{text}"'

        print(f'Step {i+1}/{len(ep.steps)}: {action_desc}')

        screen_desc = 'No screenshot available'
        if img_path and img_path.exists():
            img = Image.open(str(img_path))
            resized = img.resize((SEND_W, SEND_H))
            buf = io.BytesIO()
            resized.save(buf, format='PNG')
            img_b64 = base64.b64encode(buf.getvalue()).decode()

            resp = client.messages.create(
                model='claude-sonnet-4-5-20250929',
                max_tokens=500,
                messages=[{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': 'Describe this screen in 2-3 sentences. What application/dialog is shown? What buttons, fields, or important elements are visible? What would a user be doing at this step?'},
                        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png', 'data': img_b64}}
                    ]
                }]
            )
            screen_desc = resp.content[0].text
            time.sleep(0.5)

        step_info = {
            'step': i + 1,
            'action': action_desc,
            'screen_description': screen_desc,
            'screenshot': str(img_path) if img_path else None,
            'is_decision_point': False
        }
        steps_report.append(step_info)
        print(f'  Screen: {screen_desc[:100]}...')

    report_path = output / 'analysis.json'
    with open(report_path, 'w') as f:
        json.dump(steps_report, f, indent=2)
    print(f'Report saved: {report_path}')

    summary_path = output / 'summary.txt'
    with open(summary_path, 'w') as f:
        f.write(f'Recording Analysis: {capture_name}\n')
        f.write(f'Total Steps: {len(steps_report)}\n')
        f.write('=' * 60 + '\n\n')
        for s in steps_report:
            f.write(f'Step {s["step"]}: {s["action"]}\n')
            f.write(f'  Screen: {s["screen_description"]}\n\n')
    print(f'Summary saved: {summary_path}')

    script_path = output / 'draft_automation.py'
    with open(script_path, 'w') as f:
        f.write('from opera_auto import *\n\n')
        f.write(f'# Auto-generated from recording: {capture_name}\n')
        f.write(f'# {len(steps_report)} steps recorded\n')
        f.write('# Review and edit before running!\n\n')
        for s in steps_report:
            f.write(f'# Step {s["step"]}: {s["action"]}\n')
            f.write(f'# Screen: {s["screen_description"][:80]}\n')
            if 'click' in s['action'].lower():
                f.write(f'do("TODO: Describe what to click based on screen description above")\n')
            elif 'type' in s['action'].lower():
                f.write(f'do("TODO: Describe what to type")\n')
            else:
                f.write(f'# Action: {s["action"]}\n')
            f.write('time.sleep(2)\n\n')
    print(f'Draft script saved: {script_path}')

    print('\n=== POTENTIAL DECISION POINTS ===')
    for i, s in enumerate(steps_report):
        desc = s['screen_description'].lower()
        if any(kw in desc for kw in ['dialog', 'confirm', 'warning', 'yes', 'no', 'ok', 'error', 'popup']):
            print(f'  Step {s["step"]}: {s["screen_description"][:100]}')
            steps_report[i]['is_decision_point'] = True

    with open(report_path, 'w') as f:
        json.dump(steps_report, f, indent=2)

    print(f'\nDone! Check {output} for results.')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: analyze_recording.py <capture_name>')
        print('  Example: analyze_recording.py NightAudit20260318')
        sys.exit(1)
    analyze(sys.argv[1])
