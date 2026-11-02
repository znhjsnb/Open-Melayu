import os
import json

transcript_path = r"C:\Users\d\.gemini\antigravity\brain\a15a97c6-dccc-4f20-bae5-6b32e0337038\.system_generated\logs\transcript.jsonl"
out_path = r"c:\Users\d\Documents\open-melayu\docs\CONVERSATION_FOR_AUDIT.md"
os.makedirs(os.path.dirname(out_path), exist_ok=True)

entries = []
with open(transcript_path, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
            step_idx = item.get('step_index')
            source = item.get('source')
            stype = item.get('type')
            content = item.get('content', '')
            if stype == 'USER_INPUT':
                entries.append(f"### [Step {step_idx}] USER:\n{content}\n")
            elif stype == 'PLANNER_RESPONSE' and content:
                entries.append(f"### [Step {step_idx}] ANTIGRAVITY (Agent):\n{content}\n")
        except Exception as e:
            pass

with open(out_path, 'w', encoding='utf-8') as f:
    f.write("# Open-Lexicon & Open-Melayu 会话交互记录（待 Codex 事实与幻觉审查）\n\n")
    f.write("\n---\n\n".join(entries))

print(f"Extracted {len(entries)} turns to {out_path}")
