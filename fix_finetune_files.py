"""Fix fine-tuning files: ensure all conversations end with assistant turn."""
import json

for fname in ['bruce_finetune_train.jsonl', 'bruce_finetune_validation.jsonl']:
    with open(fname, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    fixed = 0
    out = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        conv = json.loads(line)
        msgs = conv['messages']
        if msgs[-1]['role'] != 'assistant':
            msgs.append({'role': 'assistant', 'content': 'Con gusto, que tenga buen dia.'})
            fixed += 1
            print(f"  {fname} ejemplo {i+1}: agregado turno final assistant")
        out.append(json.dumps(conv, ensure_ascii=False))
    with open(fname, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    print(f"{fname}: {fixed} corregidos, {len(out)} total")
