"""Pipeline configuration: company pool, constants, and templates."""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = SCRIPTS_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CONTEXTS_DIR = DATA_DIR / "contexts"
GENERATED_DIR = DATA_DIR / "generated"
FINAL_DIR = DATA_DIR / "final"

# ---------------------------------------------------------------------------
# EDINET collection
# ---------------------------------------------------------------------------

TARGET_YEARS = ["2023", "2024"]

# Maximum concurrent date range for filing search (days per year lookup)
FILING_SEARCH_DAYS = 366

# ---------------------------------------------------------------------------
# Company pool — curated for diversity
# ---------------------------------------------------------------------------
# Criteria:
#   - Mix of IFRS / J-GAAP / US-GAAP
#   - Large-cap, mid-cap representation
#   - Broad industry coverage (TSE sector codes)
#   - At least 3 US-GAAP filers for standard diversity
#
# Fields: edinet_code, name, industry, gaap (expected)

COMPANY_POOL: list[dict[str, str]] = [
    # --- IFRS large-cap ---
    {
        "edinet_code": "E02144",
        "name": "トヨタ自動車",
        "industry": "輸送用機器",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01777",
        "name": "ソニーグループ",
        "industry": "電気機器",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E02513",
        "name": "ソフトバンクグループ",
        "industry": "情報・通信業",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E03432",
        "name": "ファーストリテイリング",
        "industry": "小売業",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01624",
        "name": "日立製作所",
        "industry": "電気機器",
        "gaap": "IFRS",
    },
    {"edinet_code": "E00436", "name": "三菱商事", "industry": "卸売業", "gaap": "IFRS"},
    {"edinet_code": "E00353", "name": "三井物産", "industry": "卸売業", "gaap": "IFRS"},
    {
        "edinet_code": "E01225",
        "name": "武田薬品工業",
        "industry": "医薬品",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E02529",
        "name": "リクルートホールディングス",
        "industry": "サービス業",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E00988",
        "name": "日本電産",
        "industry": "電気機器",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E02142",
        "name": "本田技研工業",
        "industry": "輸送用機器",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01737",
        "name": "パナソニックホールディングス",
        "industry": "電気機器",
        "gaap": "IFRS",
    },
    # --- J-GAAP large-cap ---
    {
        "edinet_code": "E01755",
        "name": "キーエンス",
        "industry": "電気機器",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E02726",
        "name": "任天堂",
        "industry": "その他製品",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E04425",
        "name": "KDDI",
        "industry": "情報・通信業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E04837",
        "name": "NTT",
        "industry": "情報・通信業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E01810",
        "name": "東京エレクトロン",
        "industry": "電気機器",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E00748",
        "name": "信越化学工業",
        "industry": "化学",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E00394",
        "name": "伊藤忠商事",
        "industry": "卸売業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E01656",
        "name": "ダイキン工業",
        "industry": "機械",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E02101",
        "name": "テルモ",
        "industry": "精密機器",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E01726",
        "name": "オムロン",
        "industry": "電気機器",
        "gaap": "J-GAAP",
    },
    # --- J-GAAP mid-cap (diverse industries) ---
    {
        "edinet_code": "E00334",
        "name": "清水建設",
        "industry": "建設業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E00240",
        "name": "大和ハウス工業",
        "industry": "建設業",
        "gaap": "J-GAAP",
    },
    {"edinet_code": "E00030", "name": "味の素", "industry": "食料品", "gaap": "J-GAAP"},
    {
        "edinet_code": "E01019",
        "name": "日清食品ホールディングス",
        "industry": "食料品",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E02194",
        "name": "スズキ",
        "industry": "輸送用機器",
        "gaap": "J-GAAP",
    },
    {"edinet_code": "E01165", "name": "花王", "industry": "化学", "gaap": "J-GAAP"},
    {
        "edinet_code": "E00446",
        "name": "住友不動産",
        "industry": "不動産業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E04430",
        "name": "セブン&アイ・ホールディングス",
        "industry": "小売業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E03277",
        "name": "楽天グループ",
        "industry": "サービス業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E05280",
        "name": "MonotaRO",
        "industry": "小売業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E02332",
        "name": "ヤマハ発動機",
        "industry": "輸送用機器",
        "gaap": "J-GAAP",
    },
    {"edinet_code": "E01110", "name": "旭化成", "industry": "化学", "gaap": "J-GAAP"},
    {
        "edinet_code": "E00690",
        "name": "JFEホールディングス",
        "industry": "鉄鋼",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E02160",
        "name": "日本郵船",
        "industry": "海運業",
        "gaap": "J-GAAP",
    },
    # --- Banks / financials (J-GAAP) ---
    {
        "edinet_code": "E03606",
        "name": "三菱UFJフィナンシャル・グループ",
        "industry": "銀行業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E03618",
        "name": "三井住友フィナンシャルグループ",
        "industry": "銀行業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E03789",
        "name": "東京海上ホールディングス",
        "industry": "保険業",
        "gaap": "J-GAAP",
    },
    # --- US-GAAP filers ---
    {
        "edinet_code": "E03814",
        "name": "野村ホールディングス",
        "industry": "証券業",
        "gaap": "US-GAAP",
    },
    {
        "edinet_code": "E01950",
        "name": "オリックス",
        "industry": "その他金融業",
        "gaap": "US-GAAP",
    },
    {
        "edinet_code": "E01627",
        "name": "キヤノン",
        "industry": "電気機器",
        "gaap": "US-GAAP",
    },
    # --- Expansion: Electric & Gas (電気・ガス業) ---
    {
        "edinet_code": "E04501",
        "name": "東京電力ホールディングス",
        "industry": "電気・ガス業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E04502",
        "name": "中部電力",
        "industry": "電気・ガス業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E04513",
        "name": "東京ガス",
        "industry": "電気・ガス業",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Land Transport (陸運業) ---
    {
        "edinet_code": "E04084",
        "name": "東日本旅客鉄道",
        "industry": "陸運業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E04080",
        "name": "東海旅客鉄道",
        "industry": "陸運業",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Air Transport (空運業) ---
    {
        "edinet_code": "E04318",
        "name": "ANAホールディングス",
        "industry": "空運業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E04306",
        "name": "日本航空",
        "industry": "空運業",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Textiles (繊維製品) ---
    {
        "edinet_code": "E00535",
        "name": "東レ",
        "industry": "繊維製品",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Oil & Coal (石油・石炭製品) ---
    {
        "edinet_code": "E00817",
        "name": "ENEOSホールディングス",
        "industry": "石油・石炭製品",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Rubber (ゴム製品) ---
    {
        "edinet_code": "E01094",
        "name": "ブリヂストン",
        "industry": "ゴム製品",
        "gaap": "IFRS",
    },
    # --- Expansion: Glass & Ceramics (ガラス・土石製品) ---
    {
        "edinet_code": "E01139",
        "name": "AGC",
        "industry": "ガラス・土石製品",
        "gaap": "IFRS",
    },
    # --- Expansion: Non-ferrous Metals (非鉄金属) ---
    {
        "edinet_code": "E01220",
        "name": "住友電気工業",
        "industry": "非鉄金属",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E01196",
        "name": "三菱マテリアル",
        "industry": "非鉄金属",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Steel (鉄鋼) ---
    {
        "edinet_code": "E00664",
        "name": "日本製鉄",
        "industry": "鉄鋼",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E00676",
        "name": "神戸製鋼所",
        "industry": "鉄鋼",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Pulp & Paper (パルプ・紙) ---
    {
        "edinet_code": "E00602",
        "name": "王子ホールディングス",
        "industry": "パルプ・紙",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Mining (鉱業) ---
    {
        "edinet_code": "E00062",
        "name": "INPEX",
        "industry": "鉱業",
        "gaap": "IFRS",
    },
    # --- Expansion: Pharmaceuticals (医薬品) ---
    {
        "edinet_code": "E01476",
        "name": "第一三共",
        "industry": "医薬品",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01477",
        "name": "エーザイ",
        "industry": "医薬品",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01230",
        "name": "アステラス製薬",
        "industry": "医薬品",
        "gaap": "IFRS",
    },
    # --- Expansion: Machinery (機械) ---
    {
        "edinet_code": "E02302",
        "name": "クボタ",
        "industry": "機械",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E01766",
        "name": "ファナック",
        "industry": "電気機器",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E02317",
        "name": "小松製作所",
        "industry": "機械",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E02730",
        "name": "DMG森精機",
        "industry": "機械",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01303",
        "name": "SMC",
        "industry": "機械",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E02375",
        "name": "IHI",
        "industry": "機械",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E02350",
        "name": "川崎重工業",
        "industry": "輸送用機器",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Electrical Equipment (電気機器) ---
    {
        "edinet_code": "E01781",
        "name": "TDK",
        "industry": "電気機器",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01846",
        "name": "ローム",
        "industry": "電気機器",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E01775",
        "name": "富士通",
        "industry": "電気機器",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01786",
        "name": "日本電気",
        "industry": "電気機器",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01811",
        "name": "アドバンテスト",
        "industry": "電気機器",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01825",
        "name": "村田製作所",
        "industry": "電気機器",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Chemicals (化学) ---
    {
        "edinet_code": "E01379",
        "name": "富士フイルムホールディングス",
        "industry": "化学",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01357",
        "name": "資生堂",
        "industry": "化学",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01332",
        "name": "ユニ・チャーム",
        "industry": "化学",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01164",
        "name": "ライオン",
        "industry": "化学",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Food (食料品) ---
    {
        "edinet_code": "E00045",
        "name": "キリンホールディングス",
        "industry": "食料品",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E00064",
        "name": "日本ハム",
        "industry": "食料品",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E02274",
        "name": "日本たばこ産業",
        "industry": "食料品",
        "gaap": "IFRS",
    },
    # --- Expansion: Retail (小売業) ---
    {
        "edinet_code": "E03041",
        "name": "ニトリホールディングス",
        "industry": "小売業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E03357",
        "name": "良品計画",
        "industry": "小売業",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Transport Equipment (輸送用機器) ---
    {
        "edinet_code": "E02178",
        "name": "SUBARU",
        "industry": "輸送用機器",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E02170",
        "name": "マツダ",
        "industry": "輸送用機器",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E02168",
        "name": "三菱自動車工業",
        "industry": "輸送用機器",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Construction (建設業) ---
    {
        "edinet_code": "E00252",
        "name": "大林組",
        "industry": "建設業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E00248",
        "name": "鹿島建設",
        "industry": "建設業",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Real Estate (不動産業) ---
    {
        "edinet_code": "E01960",
        "name": "三井不動産",
        "industry": "不動産業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E00464",
        "name": "東急不動産ホールディングス",
        "industry": "不動産業",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Services / IT ---
    {
        "edinet_code": "E05070",
        "name": "エムスリー",
        "industry": "サービス業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E04146",
        "name": "セコム",
        "industry": "サービス業",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Logistics (陸運・倉庫) ---
    {
        "edinet_code": "E01903",
        "name": "ヤマトホールディングス",
        "industry": "陸運業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E04208",
        "name": "SGホールディングス",
        "industry": "陸運業",
        "gaap": "J-GAAP",
    },
    {
        "edinet_code": "E04193",
        "name": "三菱倉庫",
        "industry": "倉庫・運輸関連業",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Precision (精密機器) ---
    {
        "edinet_code": "E02113",
        "name": "オリンパス",
        "industry": "精密機器",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01706",
        "name": "シスメックス",
        "industry": "電気機器",
        "gaap": "IFRS",
    },
    {
        "edinet_code": "E01792",
        "name": "浜松ホトニクス",
        "industry": "電気機器",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Trading (卸売業) ---
    {
        "edinet_code": "E00396",
        "name": "丸紅",
        "industry": "卸売業",
        "gaap": "IFRS",
    },
    # --- Expansion: Rubber (ゴム製品) ---
    {
        "edinet_code": "E01098",
        "name": "住友ゴム工業",
        "industry": "ゴム製品",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Metal Products (金属製品) ---
    {
        "edinet_code": "E01294",
        "name": "LIXIL",
        "industry": "金属製品",
        "gaap": "IFRS",
    },
    # --- Expansion: Real Estate (不動産業) ---
    {
        "edinet_code": "E00453",
        "name": "野村不動産ホールディングス",
        "industry": "不動産業",
        "gaap": "J-GAAP",
    },
    # --- Expansion: Fishery (水産・農林業) ---
    {
        "edinet_code": "E00015",
        "name": "マルハニチロ",
        "industry": "水産・農林業",
        "gaap": "J-GAAP",
    },
]

# Total: ~102 companies
# IFRS: ~32, J-GAAP: ~65, US-GAAP: 3

# ---------------------------------------------------------------------------
# Table context templates
# ---------------------------------------------------------------------------

PRE_TEXT_TEMPLATES: dict[str, list[str]] = {
    "pl_comparison": [
        "以下は{company_name}の{period}連結損益計算書の抜粋である。",
    ],
    "bs_summary": [
        "以下は{company_name}の{period}連結貸借対照表の要約である。",
    ],
    "cf_summary": [
        "以下は{company_name}の{period}連結キャッシュ・フロー計算書の概要である。",
    ],
    "cross_statement": [
        "{company_name}({gaap}適用)の{period}における損益計算書および貸借対照表の主要項目を以下に示す。",
    ],
    "multi_year": [
        "{company_name}の過去{n_years}期にわたる業績推移を以下に示す。",
    ],
    "bs_consistency": [
        "以下は{company_name}の{period}連結貸借対照表である。",
    ],
}

POST_TEXT_TEMPLATES: dict[str, list[str]] = {
    "pl_comparison": [
        "当期は前期比で{revenue_direction}となった。",
    ],
    "bs_summary": [
        "総資産は前期比{asset_direction}。",
    ],
    "cf_summary": [
        "フリーキャッシュフローは{fcf_sign}であった。",
    ],
    "cross_statement": [
        "同社は資本効率の改善に取り組んでいる。",
    ],
    "multi_year": [
        "同社は中期経営計画のもと成長を目指している。",
    ],
    "bs_consistency": [
        "なお、金額は{scale}単位で表示している。",
    ],
}

# ---------------------------------------------------------------------------
# Subtask distribution targets
# ---------------------------------------------------------------------------

SUBTASK_TARGETS = {
    "numerical_reasoning": {"min": 450, "target": 550, "max": 650},
    "consistency_checking": {"min": 150, "target": 200, "max": 250},
    "temporal_reasoning": {"min": 200, "target": 250, "max": 300},
}

# Maximum questions from a single company (as fraction of total)
MAX_COMPANY_SHARE = 0.05

# Minimum DSL program steps for a question to be accepted
MIN_PROGRAM_STEPS = 1

# Numerical match tolerance for answer verification (5% for rounding)
ANSWER_TOLERANCE = 0.05
