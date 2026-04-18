# jfinqa deep audit report

Total rows scanned: 1000

## Findings summary
- **impossible_cogs**: 0
- **gross_profit_mismatch**: 0
- **op_income_mismatch**: 98
- **ni_decomposition_mismatch**: 0
- **asset_total_mismatch**: 0
- **balance_sheet_mismatch**: 0
- **roe_convention_ambiguity**: 64
- **rounding_pedantry**: 0

## op_income_mismatch

Count: 98
```json
[
  {
    "id": "nr_006",
    "company": "伊藤忠商事",
    "expected": 263681.0,
    "reported": 244999.0
  },
  {
    "id": "nr_016",
    "company": "旭化成",
    "expected": 77670.0,
    "reported": 64490.0
  },
  {
    "id": "nr_020",
    "company": "武田薬品工業",
    "expected": 656377.0,
    "reported": 778662.0
  },
  {
    "id": "nr_030",
    "company": "オムロン",
    "expected": 15800.0,
    "reported": 17376.0
  },
  {
    "id": "nr_032",
    "company": "ファナック",
    "expected": 260210.0,
    "reported": 160260.0
  },
  {
    "id": "nr_038",
    "company": "オリックス",
    "expected": 87067.0,
    "reported": 81628.0
  },
  {
    "id": "nr_056",
    "company": "KDDI",
    "expected": 926853.0,
    "reported": 961584.0
  },
  {
    "id": "nr_067",
    "company": "伊藤忠商事",
    "expected": 263681.0,
    "reported": 244999.0
  },
  {
    "id": "nr_077",
    "company": "旭化成",
    "expected": 77670.0,
    "reported": 64490.0
  },
  {
    "id": "nr_081",
    "company": "武田薬品工業",
    "expected": 656377.0,
    "reported": 778662.0
  }
]
```

## roe_convention_ambiguity

Count: 64
```json
[
  {
    "id": "nr_001",
    "company": "マルハニチロ",
    "net_income": 24722.0,
    "parent_ni": 20853.0,
    "question": "マルハニチロの2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_002",
    "company": "味の素",
    "net_income": 1898.0,
    "parent_ni": 1898.0,
    "question": "味の素の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_003",
    "company": "日本ハム",
    "net_income": 1161.0,
    "parent_ni": 1161.0,
    "question": "日本ハムの2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_004",
    "company": "大林組",
    "net_income": 1064.2,
    "parent_ni": 1064.4,
    "question": "大林組の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_005",
    "company": "清水建設",
    "net_income": 29448.0,
    "parent_ni": 28078.0,
    "question": "清水建設の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_006",
    "company": "伊藤忠商事",
    "net_income": 166031.0,
    "parent_ni": 164073.0,
    "question": "伊藤忠商事の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_007",
    "company": "丸紅",
    "net_income": 17766.0,
    "parent_ni": 16176.0,
    "question": "丸紅の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_008",
    "company": "三菱商事",
    "net_income": 102032.0,
    "parent_ni": 87121.0,
    "question": "三菱商事の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_009",
    "company": "住友不動産",
    "net_income": 25904.0,
    "parent_ni": 24495.0,
    "question": "住友不動産の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_010",
    "company": "野村不動産ホールディングス",
    "net_income": 471.5,
    "parent_ni": 471.5,
    "question": "野村不動産ホールディングスの2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  }
]
```
