from odds import validate_probability


def calculate_edge(model_probability, implied_probability) -> float:
    model = validate_probability(model_probability)
    implied = validate_probability(implied_probability)
    return model - implied
