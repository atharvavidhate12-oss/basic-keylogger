# utils.py
def compute_wpm_accuracy(typed_chars: int, errors: int, elapsed_seconds: float):
    elapsed_seconds = max(elapsed_seconds, 1e-6)
    words = typed_chars / 5.0
    wpm = words / (elapsed_seconds / 60.0)
    accuracy = 100.0 if typed_chars == 0 else max(0.0, ((typed_chars - errors) / typed_chars) * 100.0)
    return round(wpm, 2), round(accuracy, 2)
