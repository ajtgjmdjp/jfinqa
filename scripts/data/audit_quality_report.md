# jfinqa deep audit report

Total rows scanned: 1000

## Findings summary
- **impossible_cogs**: 0
- **gross_profit_mismatch**: 22
- **op_income_mismatch**: 311
- **ni_decomposition_mismatch**: 0
- **asset_total_mismatch**: 1
- **balance_sheet_mismatch**: 0
- **roe_convention_ambiguity**: 89
- **rounding_pedantry**: 0

## gross_profit_mismatch

Count: 22
```json
[
  {
    "id": "nr_006",
    "company": "大林組",
    "expected": 284204.0,
    "reported": 219602.0
  },
  {
    "id": "nr_017",
    "company": "旭化成",
    "expected": 879039.0,
    "reported": 815969.0
  },
  {
    "id": "nr_110",
    "company": "大林組",
    "expected": 284204.0,
    "reported": 219602.0
  },
  {
    "id": "nr_121",
    "company": "旭化成",
    "expected": 879039.0,
    "reported": 815969.0
  },
  {
    "id": "nr_214",
    "company": "大林組",
    "expected": 284204.0,
    "reported": 219602.0
  },
  {
    "id": "nr_225",
    "company": "旭化成",
    "expected": 879039.0,
    "reported": 815969.0
  },
  {
    "id": "nr_318",
    "company": "大林組",
    "expected": 284204.0,
    "reported": 219602.0
  },
  {
    "id": "nr_329",
    "company": "旭化成",
    "expected": 879039.0,
    "reported": 815969.0
  },
  {
    "id": "nr_422",
    "company": "大林組",
    "expected": 284204.0,
    "reported": 219602.0
  },
  {
    "id": "nr_433",
    "company": "旭化成",
    "expected": 879039.0,
    "reported": 815969.0
  }
]
```

## op_income_mismatch

Count: 311
```json
[
  {
    "id": "nr_003",
    "company": "INPEX",
    "expected": 1220688.0,
    "reported": 1114189.0
  },
  {
    "id": "nr_009",
    "company": "キリンホールディングス",
    "expected": 201495.0,
    "reported": 150294.0
  },
  {
    "id": "nr_011",
    "company": "日清食品ホールディングス",
    "expected": 61378.0,
    "reported": 73361.0
  },
  {
    "id": "nr_012",
    "company": "日本たばこ産業",
    "expected": 634051.0,
    "reported": 672410.0
  },
  {
    "id": "nr_016",
    "company": "東レ",
    "expected": 97179.0,
    "reported": 57651.0
  },
  {
    "id": "nr_017",
    "company": "旭化成",
    "expected": 140746.0,
    "reported": 177168.0
  },
  {
    "id": "nr_018",
    "company": "花王",
    "expected": 93657.0,
    "reported": 60035.0
  },
  {
    "id": "nr_020",
    "company": "アステラス製薬",
    "expected": 571077.0,
    "reported": 25518.0
  },
  {
    "id": "nr_021",
    "company": "エーザイ",
    "expected": 211996.0,
    "reported": 53408.0
  },
  {
    "id": "nr_022",
    "company": "第一三共",
    "expected": 549369.0,
    "reported": 211588.0
  }
]
```

## asset_total_mismatch

Count: 1
```json
[
  {
    "id": "nr_017",
    "company": "旭化成",
    "current_asset": 1650037.0,
    "fixed_asset": 2012693.0,
    "expected_sum": 3662730.0,
    "reported_total": 3551395.0
  }
]
```

## roe_convention_ambiguity

Count: 89
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
    "company": "三菱マテリアル",
    "net_income": 37280.0,
    "parent_ni": 29793.0,
    "question": "三菱マテリアルの2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_003",
    "company": "INPEX",
    "net_income": 332576.0,
    "parent_ni": 321708.0,
    "question": "INPEXの2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_004",
    "company": "大和ハウス工業",
    "net_income": 300253.0,
    "parent_ni": 298752.0,
    "question": "大和ハウス工業の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_005",
    "company": "清水建設",
    "net_income": 20779.0,
    "parent_ni": 17163.0,
    "question": "清水建設の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_006",
    "company": "大林組",
    "net_income": 77179.0,
    "parent_ni": 75059.0,
    "question": "大林組の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_007",
    "company": "鹿島建設",
    "net_income": 116615.0,
    "parent_ni": 115033.0,
    "question": "鹿島建設の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_008",
    "company": "日本ハム",
    "net_income": 29448.0,
    "parent_ni": 28078.0,
    "question": "日本ハムの2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_009",
    "company": "キリンホールディングス",
    "net_income": 150438.0,
    "parent_ni": 112697.0,
    "question": "キリンホールディングスの2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  },
  {
    "id": "nr_010",
    "company": "味の素",
    "net_income": 102032.0,
    "parent_ni": 87121.0,
    "question": "味の素の2024年3月期のROEをDuPont分解(純利益率×総資産回転率×財務レバレッジ)で求めると何%か。"
  }
]
```
