from aios_core.ml.conversion_predictor import ConversionPredictor


def test_predictor_initialization():
    predictor = ConversionPredictor()
    assert predictor.trained == False
    assert predictor.weights is None

def test_predict_without_training():
    predictor = ConversionPredictor()
    template = {"content": "Hello {{name}}!"}
    score = predictor.predict(template)
    assert score == 0.1

def test_predict_with_features():
    predictor = ConversionPredictor()
    predictor.trained = True
    predictor.weights = [0.001, 0.05, 0.15, 0.1, 0.05, 0.002]
    template = {"content": "Hello {{name}}! Special discount for you!"}
    score = predictor.predict(template)
    assert 0.0 <= score <= 1.0

def test_train_model():
    predictor = ConversionPredictor()
    templates = [{"content": f"Template {i}"} for i in range(15)]
    conversions = [0.1 * (i % 10) for i in range(15)]
    predictor.train(templates, conversions)
    assert predictor.trained == True
    assert predictor.weights is not None
