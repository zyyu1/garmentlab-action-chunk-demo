"""Read installed solver getter/setter source without importing Isaac or starting simulation."""
import ast
import hashlib
import json
from pathlib import Path

root=Path('/root/autodl-tmp/envs/isaac40/lib/python3.10/site-packages/isaacsim')
names={'get_solver_position_iteration_count','get_solver_velocity_iteration_count',
       'set_solver_position_iteration_count','set_solver_velocity_iteration_count',
       'get_solver_position_iteration_counts','get_solver_velocity_iteration_counts',
       'set_solver_position_iteration_counts','set_solver_velocity_iteration_counts'}
records=[]
paths=sorted(set(root.glob('exts*/omni.isaac.core/omni/isaac/core/articulations/articulation*.py')))
for path in paths:
    raw=path.read_bytes()
    tree=ast.parse(raw.decode('utf-8-sig'))
    for cls in tree.body:
        if not isinstance(cls,ast.ClassDef):continue
        for method in cls.body:
            if not isinstance(method,ast.FunctionDef) or method.name not in names:continue
            body=method.body
            if body and isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str):
                method.body=body[1:]
            text=ast.unparse(method)
            record={'file':str(path),'file_sha256':hashlib.sha256(raw).hexdigest(),
                    'class':cls.name,'method':method.name,'line':method.lineno,'source_without_docstring':text}
            records.append(record)
            print('\n'+str(path)+':'+str(method.lineno)+' '+cls.name,flush=True)
            print(text,flush=True)
if not records:raise RuntimeError('No matching installed Isaac Core sources: '+str(root))
target=Path('/root/autodl-tmp/day4-solver-api-audit.json')
target.write_text(json.dumps({'scope':'Read-only installed source; no simulator imported',
                             'records':records},indent=2),encoding='utf-8')
print('\nSOLVER_API_EXPORT_OK',target,flush=True)
