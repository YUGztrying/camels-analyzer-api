"""
Poste-code mappings for BCEAO bank and WAEMU microfinance (SFD) templates.

Maps the Spreading App's normalized poste codes → flat calculator field names
that camels_calculator.py expects.

Each mapping entry is either:
  - A string (single poste code)
  - A list of strings (sum of poste codes)
  - A dict with 'poste' and 'use' keys (for bank assets with brut/amort/net columns)
"""

# ============================================================================
# BANK (banque) — BCEAO PCB format
# ============================================================================

BANK_MAP = {
    # ----- Balance Sheet: Assets (actifs) -----
    "cash_reserves_requirements": "ACTIF_01",           # Caisse, Banque Centrale, CCP
    "due_from_banks":            "ACTIF_03",            # Créances interbancaires
    "gross_loans":               {"poste": "ACTIF_04",  # Créances sur la clientèle
                                  "use": "brut_amount"},
    "loan_loss_provisions":      {"poste": "ACTIF_04",  # Amort/Prov on client loans
                                  "use": "amort_prov_amount"},
    "investment_securities":     ["ACTIF_02", "ACTIF_05", "ACTIF_06"],  # Govt + bonds + equities
    "fixed_assets":              ["ACTIF_13", "ACTIF_14"],              # Intangible + tangible
    "other_assets":              ["ACTIF_07", "ACTIF_08", "ACTIF_09"],
    "total_assets":              "ACTIF_TOTAL",

    # ----- Balance Sheet: Liabilities (passifs) -----
    "deposits":                  "PASSIF_03",            # Dettes à l'égard de la clientèle
    "interbank_liabilities":     ["PASSIF_01", "PASSIF_02"],
    "short_term_borrowings":     "PASSIF_04",            # Debt securities issued
    "long_term_debt":            "PASSIF_08",            # Subordinated debt
    "other_liabilities":         ["PASSIF_05", "PASSIF_06", "PASSIF_07"],

    # Equity
    "paid_in_capital":           "PASSIF_10",
    "reserves":                  ["PASSIF_12", "PASSIF_13", "PASSIF_14"],
    "retained_earnings":         "PASSIF_15",
    "net_profit":                "PASSIF_16",            # Résultat de l'exercice (BS)
    "total_equity":              "PASSIF_09",            # Capitaux propres section total

    # ----- Income Statement (compte_resultats) -----
    "interest_income":           "CR_01",
    "interest_expenses":         "CR_02",
    "net_interest_income":       None,  # computed: CR_01 - CR_02
    "fees_commissions":          ["CR_04"],               # Commission income
    "commission_expenses":       "CR_05",
    "trading_income":            ["CR_06", "CR_07"],      # Trading + investment gains
    "other_banking_income":      "CR_08",
    "other_banking_charges":     "CR_09",
    "operating_income":          "CR_10",                 # PNB (Produit Net Bancaire)
    "operating_expenses":        "CR_12",                 # Charges générales d'exploitation
    "depreciation":              "CR_13",                 # Dotations aux amortissements
    "cost_of_risk":              "CR_15",                 # Coût du risque (provision charge)
    "operating_result":          "CR_16",
    "income_tax":                "CR_19",
    "net_income":                "CR_20",
}


# ============================================================================
# MICROFINANCE (microfinance) — WAEMU SFD/RCS format
# ============================================================================

MFI_MAP = {
    # ----- Balance Sheet: Assets (actifs) -----
    "cash_reserves_requirements": ["MFA_A10", "MFA_A12"],  # Cash + bank accounts
    "due_from_banks":             ["MFA_A2A", "MFA_A2H", "MFA_A2I", "MFA_A2J",
                                   "MFA_A3A", "MFA_A3B", "MFA_A3C"],  # Deposits + loans to FIs
    "gross_loans":                ["MFA_B2D", "MFA_B2N", "MFA_B30", "MFA_B40",
                                   "MFA_B65", "MFA_B70"],  # All client credits + NPLs
    "npls_mn":                    ["MFA_B70",              # Client NPLs (section total)
                                   "MFA_A70"],             # + FI NPLs
    "investment_securities":      "MFA_C10",               # Titres de placement
    "fixed_assets":               ["MFA_D30", "MFA_D40",   # Exploitation + hors exploitation
                                   "MFA_D23", "MFA_D24", "MFA_D25"],  # + in progress
    "other_assets":               ["MFA_C30", "MFA_C40", "MFA_C55",
                                   "MFA_C6A", "MFA_C6G", "MFA_C6Q",
                                   "MFA_D10", "MFA_D1A"],
    "total_assets":               "MFA_TOTAL_ACTIF",

    # ----- Balance Sheet: Liabilities (passifs) -----
    "deposits":                   ["MFP_G10", "MFP_G15", "MFP_G2A",
                                   "MFP_G30", "MFP_G35"],  # All member/client deposits
    "interbank_liabilities":      ["MFP_F1A", "MFP_F2A", "MFP_F2B",
                                   "MFP_F2C", "MFP_F2D"],  # FI deposits received
    "short_term_borrowings":      ["MFP_F3E", "MFP_G60"],  # Short-term borrowings
    "long_term_debt":             ["MFP_F3F", "MFP_F55",   # Long-term borrowings + allocated
                                   "MFP_L41"],             # Subordinated debt
    "other_liabilities":          ["MFP_H10", "MFP_H40", "MFP_H6A",
                                   "MFP_H6G", "MFP_H6P"],

    # Equity
    "paid_in_capital":            ["MFP_L60", "MFP_L65"],  # Capital + endowment fund
    "reserves":                   ["MFP_L50", "MFP_L55", "MFP_L59"],  # Premium + reserves + reval
    "retained_earnings":          "MFP_L70",
    "net_profit":                 "MFP_L80",               # Résultat de l'exercice (BS)
    "total_equity":               "_compute_mfi_equity",   # Sum of equity components
    "provisions_for_risks":       ["MFP_L30", "MFP_L35"],  # Provisions for risks

    # ----- Income Statement (compte_resultats) -----
    # Interest income: sum of all product lines (V categories)
    "interest_income":            ["MFP_V08", "MFP_V3A"],  # FI interest + client interest
    "interest_expenses":          ["MFC_R08", "MFC_R3A"],  # FI charges + client charges
    "net_interest_income":        None,  # computed

    "fees_commissions":           ["MFP_V6U", "MFP_V6F"],  # Service fees + off-balance sheet
    "other_banking_income":       ["MFP_V4B", "MFP_V5B",   # Securities + financial investments
                                   "MFP_V6A", "MFP_V7A"],  # FX + other financial products
    "other_banking_charges":      ["MFC_R4B", "MFC_R5B",
                                   "MFC_R5E", "MFC_R6A",
                                   "MFC_R6F", "MFC_R7A"],

    # Operating expenses
    "staff_costs":                "MFC_S02",               # Personnel
    "operating_expenses":         "MFC_Z28",               # Total operating expenses
    "depreciation":               ["MFC_T51"],             # Depreciation on fixed assets
    "cost_of_risk":               "MFC_T6B",               # Provisions + write-offs

    # Bottom line
    "income_tax":                 "MFC_T82",               # Impôts sur les excédents
    "net_income":                 "CR_20",                  # Net income (bank CR format)
    # Fallback for MFI net income from the charge/product totals
    "mfi_total_products":         "MFP_X84",               # Total products
    "mfi_total_charges":          "MFC_T84",               # Total charges
    "mfi_net_income_alt":         "MFP_L75",               # Excédent des produits sur charges
}


# ============================================================================
# Computed fields — derived after extraction
# ============================================================================

def compute_derived_fields(data: dict, type_institution: str) -> dict:
    """Add fields that are computed from other extracted fields."""

    # Net interest income
    if data.get("net_interest_income") is None:
        ii = data.get("interest_income", 0) or 0
        ie = data.get("interest_expenses", 0) or 0
        data["net_interest_income"] = ii - ie

    # Total equity for MFI (sum components if not directly available)
    if type_institution == "microfinance" and not data.get("total_equity"):
        equity_parts = [
            data.get("paid_in_capital", 0) or 0,
            data.get("reserves", 0) or 0,
            data.get("retained_earnings", 0) or 0,
            data.get("net_profit", 0) or 0,
        ]
        data["total_equity"] = sum(equity_parts)

    # Total liabilities = total_assets - total_equity
    ta = data.get("total_assets", 0) or 0
    te = data.get("total_equity", 0) or 0
    if ta and te:
        data["total_liabilities"] = ta - te

    # MFI net income fallback
    if type_institution == "microfinance" and not data.get("net_income"):
        alt = data.get("mfi_net_income_alt")
        if alt:
            data["net_income"] = alt
        else:
            tp = data.get("mfi_total_products", 0) or 0
            tc = data.get("mfi_total_charges", 0) or 0
            if tp or tc:
                data["net_income"] = tp - tc

    # Operating income (for cost-to-income calculation)
    if not data.get("operating_income"):
        nii = data.get("net_interest_income", 0) or 0
        fees = data.get("fees_commissions", 0) or 0
        other_inc = data.get("other_banking_income", 0) or 0
        other_chg = data.get("other_banking_charges", 0) or 0
        data["operating_income"] = nii + fees + other_inc - other_chg

    # Provision expenses (for cost-of-risk calculation) = cost_of_risk IS the provision charge
    if not data.get("provision_expenses"):
        data["provision_expenses"] = data.get("cost_of_risk", 0)

    # Loan loss provisions (balance sheet stock) — for banks use extracted value,
    # for MFI approximate from provisions_for_risks if not available
    if not data.get("loan_loss_provisions") and type_institution == "microfinance":
        data["loan_loss_provisions"] = data.get("provisions_for_risks", 0)

    # Foreclosed assets (not tracked separately in either template)
    if data.get("foreclosed_assets") is None:
        data["foreclosed_assets"] = 0

    # NPLs for banks — not directly in the balance sheet poste codes
    # (would need regulatory data or manual input via irp_overrides)
    # Leave as-is if not populated

    return data


def get_mapping(type_institution: str) -> dict:
    """Return the appropriate mapping for the institution type."""
    if type_institution == "banque":
        return BANK_MAP
    elif type_institution == "microfinance":
        return MFI_MAP
    else:
        raise ValueError(f"Unknown institution type: {type_institution}")
