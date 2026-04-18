# jfinqa audit report

Source: `scripts/data/final/jfinqa_v1.json`
Total questions: 1000
Unique companies (EDINET code): 61

## Distribution

### Subtask
- `consistency_checking`: 200
- `numerical_reasoning`: 550
- `temporal_reasoning`: 250

### Accounting standard
- `IFRS`: 332 (33.2%)
- `J-GAAP`: 624 (62.4%)
- `US-GAAP`: 44 (4.4%)

### Filing year
- `2023`: 10
- `2024`: 990

### Top 15 companies
- マルハニチロ: 19
- 味の素: 19
- 日本ハム: 19
- 大林組: 19
- 丸紅: 19
- 住友不動産: 19
- 野村不動産ホールディングス: 19
- 日本製鉄: 19
- JFEホールディングス: 19
- 日清食品ホールディングス: 19
- ブリヂストン: 19
- 住友ゴム工業: 19
- AGC: 19
- ライオン: 19
- 花王: 19

## Findings

- schema missing fields: 0
- DSL unparsable / execution error: 0
- DSL result ↔ answer mismatch: 0
- exact duplicate questions: 0
- near-duplicate questions: 0
