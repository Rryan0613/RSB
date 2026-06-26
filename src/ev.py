def american_to_decimal(odds):
    if odds > 0:
        return 1 + odds / 100
    return 1 + 100 / abs(odds)

def implied_probability(odds):
    return 1 / american_to_decimal(odds)

def ev_per_unit(model_probability, odds):
    decimal_odds = american_to_decimal(odds)
    return model_probability * (decimal_odds - 1) - (1 - model_probability)

def edge(model_probability, odds):
    return model_probability - implied_probability(odds)
