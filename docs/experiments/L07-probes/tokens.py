#!/usr/bin/env python3
"""汇总一个 agent transcript JSONL 的 token 用量（两组用同一脚本）。用法：tokens.py <file.jsonl>"""
import json, sys

path = sys.argv[1]
tot = {"input_tokens": 0, "cache_creation_input_tokens": 0,
       "cache_read_input_tokens": 0, "output_tokens": 0}
turns = 0
with open(path) as f:
    for line in f:
        try:
            d = json.loads(line)
        except Exception:
            continue
        u = (d.get("message") or {}).get("usage")
        if not u:
            continue
        turns += 1
        for k in tot:
            tot[k] += u.get(k) or 0
print(f"assistant-turns={turns}")
for k, v in tot.items():
    print(f"{k}={v}")
print(f"billable≈in+out={tot['input_tokens']+tot['output_tokens']}  "
      f"cache_read={tot['cache_read_input_tokens']}  cache_write={tot['cache_creation_input_tokens']}")
