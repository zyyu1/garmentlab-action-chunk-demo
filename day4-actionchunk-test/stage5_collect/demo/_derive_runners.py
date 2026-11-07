from pathlib import Path

APP = "Path('/root/autodl-tmp/stage5-trial/app')"
src = Path('a5-rc8b-recovery-hold120-rc7-r2/app')


def patch(text):
    text = text.replace(
        "sys.path.insert(0,'/root/autodl-tmp/garmentlab-action-chunk-demo')",
        "sys.path.insert(0,'/root/autodl-tmp/garmentlab-action-chunk-demo')\nAPP = " + APP
        + "\nsys.path.insert(0, str(APP))")
    text = text.replace("Path(__file__).with_name('square-initial-plan.json')",
                        "Path(__file__).with_name('stage5-demo-initial-plan.json')")
    text = text.replace("str(Path(__file__).with_name('square_cloth_40cm.usda'))",
                        "str(APP/'square_cloth_40cm.usda')")
    for name in ('square-initial-files.json', 'square-initial-stripfold-files.json'):
        text = text.replace("'files_manifest':'%s'" % name,
                            "'files_manifest':'stage5-demo-initial-files.json'")
        text = text.replace("'files_manifest': '%s'" % name,
                            "'files_manifest': 'stage5-demo-initial-files.json'")
    return text


out = Path('stage5_collect/demo')
out.mkdir(parents=True, exist_ok=True)
for name in ('day4-square-initial.py', 'day4-square-initial-stripfold.py'):
    text = (src / name).read_text(encoding='utf-8')
    new = name.replace('.py', '-demo.py')
    (out / new).write_text(patch(text), encoding='utf-8')
    print('wrote', new, len(text))
