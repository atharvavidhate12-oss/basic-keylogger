# test_metrics.py
from utils import compute_wpm_accuracy

def test_zero_chars():
    wpm, acc = compute_wpm_accuracy(0, 0, 1.0)
    assert wpm == 0.0
    assert acc == 100.0

def test_typical_case():
    wpm, acc = compute_wpm_accuracy(250, 5, 60.0)  # 250 chars = 50 words, 60s -> 50 WPM
    assert wpm == 50.0
    assert acc == round(((250-5)/250)*100.0, 2)

def test_high_error():
    wpm, acc = compute_wpm_accuracy(20, 20, 30.0)
    assert acc == 0.0
