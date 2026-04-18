# jfinqa audit report

Source: `scripts/data/final/jfinqa_v1.json`
Total questions: 1000
Unique companies (EDINET code): 104

## Distribution

### Subtask
- `consistency_checking`: 200
- `numerical_reasoning`: 550
- `temporal_reasoning`: 250

### Accounting standard
- `IFRS`: 323 (32.3%)
- `J-GAAP`: 656 (65.6%)
- `US-GAAP`: 21 (2.1%)

### Filing year
- `2024`: 1000

### Top 15 companies
- マルハニチロ: 12
- 三菱マテリアル: 12
- INPEX: 12
- 大和ハウス工業: 12
- 清水建設: 12
- 大林組: 11
- 鹿島建設: 11
- 日本ハム: 11
- キリンホールディングス: 11
- 味の素: 11
- 日清食品ホールディングス: 11
- 日本たばこ産業: 11
- 王子ホールディングス: 11
- ユニ・チャーム: 11
- 信越化学工業: 11

## Findings

- schema missing fields: 0
- DSL unparsable / execution error: 0
- DSL result ↔ answer mismatch: 0
- exact duplicate questions: 0
- near-duplicate questions: 0
