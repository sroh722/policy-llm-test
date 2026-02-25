from src.batch_config import TAXONOMY

FEWSHOT_BLOCK = f"""
You are building a dataset of industrial policy and regulatory instruments.

Label instrument_type as exactly one of:
{TAXONOMY}

Guidance:
- "grant" = non-repayable funding support (often with a cap)
- "subsidy" = financial support that may include rebates/price support/general aid
- "tax_credit" = tax deduction/credit/allowance tied to expenditures or investment
- "loan" = repayable financing / concessional credit
- "export_control" = licensing/export restriction/dual-use controls
- "local_content" = domestic content/sourcing/production requirements
- "procurement" = government purchasing preference/requirements
- "standard" = technical/quality/compliance standards

Return ONLY JSON with keys:
- instrument_type (string)
- confidence (0 to 1)
- target_sector (string or null)
- funding_amount_or_cap (string or null)
- eligibility_rules (list of strings)
- evidence_span (short exact quote <= 20 words from the text)

Examples:
Text: "The government provides a non-repayable grant up to HKD 10 million for automation equipment."
JSON: {{"instrument_type":"grant","confidence":0.9,"target_sector":"manufacturing","funding_amount_or_cap":"up to HKD 10 million","eligibility_rules":["supports automation equipment"],"evidence_span":"grant up to HKD 10 million"}}

Text: "A tax deduction of 200% applies to qualifying R&D expenditures."
JSON: {{"instrument_type":"tax_credit","confidence":0.9,"target_sector":"R&D","funding_amount_or_cap":null,"eligibility_rules":["qualifying R&D expenditures"],"evidence_span":"tax deduction of 200%"}}

Text: "Exports of dual-use advanced chips require an export license."
JSON: {{"instrument_type":"export_control","confidence":0.9,"target_sector":"semiconductors","funding_amount_or_cap":null,"eligibility_rules":["export license required"],"evidence_span":"require an export license"}}

Text: "Firms must meet 60% domestic content to qualify for incentives."
JSON: {{"instrument_type":"local_content","confidence":0.9,"target_sector":null,"funding_amount_or_cap":null,"eligibility_rules":["60% domestic content"],"evidence_span":"60% domestic content"}}
""".strip()