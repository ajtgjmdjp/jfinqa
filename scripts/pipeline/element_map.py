"""Mapping from XBRL taxonomy element names to Japanese labels.

Covers the most common elements from J-GAAP (jppfs_cor), IFRS, and
US-GAAP taxonomies as used in EDINET filings.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Income Statement (PL)
# ---------------------------------------------------------------------------

PL_ELEMENTS: dict[str, str] = {
    # J-GAAP terms
    "NetSales": "売上高",
    "CostOfSales": "売上原価",
    "GrossProfit": "売上総利益",
    "SellingGeneralAndAdministrativeExpenses": "販売費及び一般管理費",
    "OperatingIncome": "営業利益",
    "NonOperatingIncome": "営業外収益",
    "NonOperatingExpenses": "営業外費用",
    "OrdinaryIncome": "経常利益",
    "ExtraordinaryIncome": "特別利益",
    "ExtraordinaryLoss": "特別損失",
    "IncomeBeforeIncomeTaxes": "税引前当期純利益",
    "IncomeTaxes": "法人税等",
    "ProfitLoss": "当期純利益",
    "ProfitLossAttributableToOwnersOfParent": "親会社株主に帰属する当期純利益",
    "ProfitLossAttributableToNonControllingInterests": "非支配株主に帰属する当期純利益",
    # IFRS terms
    "Revenue": "売上収益",
    "OperatingProfit": "営業利益",
    "ProfitBeforeTax": "税引前利益",
    "ProfitForThePeriod": "当期利益",
    "ProfitAttributableToOwnersOfParent": "親会社の所有者に帰属する当期利益",
    "ComprehensiveIncome": "包括利益",
    "OtherComprehensiveIncome": "その他の包括利益",
    # Additional line items
    "InterestIncome": "受取利息",
    "InterestExpense": "支払利息",
    "DividendIncome": "受取配当金",
    "ShareOfProfitOfInvestmentsAccountedForUsingEquityMethod": "持分法による投資利益",
    "DepreciationAndAmortization": "減価償却費",
    "ResearchAndDevelopmentExpenses": "研究開発費",
}

# ---------------------------------------------------------------------------
# Balance Sheet (BS)
# ---------------------------------------------------------------------------

BS_ELEMENTS: dict[str, str] = {
    # Assets
    "CurrentAssets": "流動資産",
    "CashAndDeposits": "現金及び預金",
    "CashAndCashEquivalents": "現金及び現金同等物",
    "NotesAndAccountsReceivableTrade": "受取手形及び売掛金",
    "AccountsReceivableTrade": "売掛金",
    "Inventories": "棚卸資産",
    "MerchandiseAndFinishedGoods": "商品及び製品",
    "ShortTermInvestmentSecurities": "有価証券",
    "OtherCurrentAssets": "その他の流動資産",
    "NoncurrentAssets": "固定資産",
    "PropertyPlantAndEquipment": "有形固定資産",
    "PropertyPlantAndEquipmentNet": "有形固定資産(純額)",
    "IntangibleAssets": "無形固定資産",
    "Goodwill": "のれん",
    "InvestmentsAndOtherAssets": "投資その他の資産",
    "InvestmentSecurities": "投資有価証券",
    "TotalAssets": "資産合計",
    # Liabilities
    "CurrentLiabilities": "流動負債",
    "ShortTermLoansPayable": "短期借入金",
    "NotesAndAccountsPayableTrade": "支払手形及び買掛金",
    "AccountsPayableTrade": "買掛金",
    "CurrentPortionOfLongTermLoansPayable": "1年内返済予定の長期借入金",
    "NoncurrentLiabilities": "固定負債",
    "LongTermLoansPayable": "長期借入金",
    "BondsPayable": "社債",
    "TotalLiabilities": "負債合計",
    # Net assets / Equity
    "NetAssets": "純資産合計",
    "ShareholdersEquity": "株主資本",
    "CapitalStock": "資本金",
    "CapitalSurplus": "資本剰余金",
    "RetainedEarnings": "利益剰余金",
    "TreasuryShares": "自己株式",
    "AccumulatedOtherComprehensiveIncome": "その他の包括利益累計額",
    "NonControllingInterests": "非支配株主持分",
    "TotalLiabilitiesAndNetAssets": "負債純資産合計",
    # IFRS equity
    "EquityAttributableToOwnersOfParent": "親会社の所有者に帰属する持分",
    "TotalEquity": "資本合計",
}

# ---------------------------------------------------------------------------
# Cash Flow Statement (CF)
# ---------------------------------------------------------------------------

CF_ELEMENTS: dict[str, str] = {
    "CashFlowsFromOperatingActivities": "営業活動によるキャッシュ・フロー",
    "CashFlowsFromInvestingActivities": "投資活動によるキャッシュ・フロー",
    "CashFlowsFromFinancingActivities": "財務活動によるキャッシュ・フロー",
    "EffectOfExchangeRateChangeOnCashAndCashEquivalents": (
        "現金及び現金同等物に係る換算差額"
    ),
    "NetIncreaseDecreaseInCashAndCashEquivalents": "現金及び現金同等物の増減額",
    "CashAndCashEquivalentsAtBeginningOfPeriod": "現金及び現金同等物の期首残高",
    "CashAndCashEquivalentsAtEndOfPeriod": "現金及び現金同等物の期末残高",
    # Operating CF details
    "DepreciationAndAmortizationOpeCF": "減価償却費",
    "IncreaseDecreaseInNotesAndAccountsReceivable": "売上債権の増減額",
    "IncreaseDecreaseInInventories": "棚卸資産の増減額",
    "IncreaseDecreaseInNotesAndAccountsPayable": "仕入債務の増減額",
    # Investing CF details
    "PurchaseOfPropertyPlantAndEquipment": "有形固定資産の取得による支出",
    "PurchaseOfInvestmentSecurities": "投資有価証券の取得による支出",
    # Financing CF details
    "ProceedsFromIssuanceOfBonds": "社債の発行による収入",
    "RedemptionOfBonds": "社債の償還による支出",
    "DividendsPaid": "配当金の支払額",
    "PurchaseOfTreasuryShares": "自己株式の取得による支出",
}

# ---------------------------------------------------------------------------
# Combined mapping
# ---------------------------------------------------------------------------

ALL_ELEMENTS: dict[str, str] = {**PL_ELEMENTS, **BS_ELEMENTS, **CF_ELEMENTS}


def to_japanese(element_name: str) -> str | None:
    """Convert an XBRL element name to its Japanese label.

    Returns ``None`` if the element is not in the mapping.
    """
    return ALL_ELEMENTS.get(element_name)


# Ordered list of PL items (display order in a standard income statement)
PL_DISPLAY_ORDER: list[str] = [
    "NetSales",
    "Revenue",
    "CostOfSales",
    "GrossProfit",
    "SellingGeneralAndAdministrativeExpenses",
    "OperatingIncome",
    "OperatingProfit",
    "NonOperatingIncome",
    "NonOperatingExpenses",
    "OrdinaryIncome",
    "ExtraordinaryIncome",
    "ExtraordinaryLoss",
    "IncomeBeforeIncomeTaxes",
    "ProfitBeforeTax",
    "IncomeTaxes",
    "ProfitLoss",
    "ProfitForThePeriod",
    "ProfitLossAttributableToOwnersOfParent",
    "ProfitAttributableToOwnersOfParent",
]

BS_DISPLAY_ORDER: list[str] = [
    "CurrentAssets",
    "CashAndDeposits",
    "CashAndCashEquivalents",
    "NotesAndAccountsReceivableTrade",
    "AccountsReceivableTrade",
    "Inventories",
    "NoncurrentAssets",
    "PropertyPlantAndEquipment",
    "IntangibleAssets",
    "Goodwill",
    "InvestmentsAndOtherAssets",
    "TotalAssets",
    "CurrentLiabilities",
    "NoncurrentLiabilities",
    "TotalLiabilities",
    "ShareholdersEquity",
    "CapitalStock",
    "RetainedEarnings",
    "TreasuryShares",
    "NetAssets",
    "TotalEquity",
    "TotalLiabilitiesAndNetAssets",
]

CF_DISPLAY_ORDER: list[str] = [
    "CashFlowsFromOperatingActivities",
    "CashFlowsFromInvestingActivities",
    "CashFlowsFromFinancingActivities",
    "EffectOfExchangeRateChangeOnCashAndCashEquivalents",
    "NetIncreaseDecreaseInCashAndCashEquivalents",
    "CashAndCashEquivalentsAtEndOfPeriod",
]
