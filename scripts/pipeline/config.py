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
]

# Total: ~45 companies
# IFRS: 12, J-GAAP: 30, US-GAAP: 3

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
    "numerical_reasoning": {"min": 200, "target": 250, "max": 300},
    "consistency_checking": {"min": 50, "target": 75, "max": 100},
    "temporal_reasoning": {"min": 50, "target": 75, "max": 100},
}

# Maximum questions from a single company (as fraction of total)
MAX_COMPANY_SHARE = 0.05

# Minimum DSL program steps for a question to be accepted
MIN_PROGRAM_STEPS = 2

# Numerical match tolerance for answer verification
ANSWER_TOLERANCE = 0.01
