import os
from typing import List

from transformers import pipeline

MODEL_NAME = os.getenv("MODEL_NAME", "mrm8488/bert-tiny-finetuned-sms-spam-detection")

# The model's config has no label names, so map the raw ids ourselves.
LABEL_MAP = {"LABEL_0": "ham", "LABEL_1": "spam"}


class SpamClassifier:
    def __init__(self, model_name: str = MODEL_NAME):
        self.model_name = model_name
        self.pipe = pipeline("text-classification", model=model_name, tokenizer=model_name)

    def predict(self, texts: List[str]) -> List[dict]:
        results = self.pipe(texts, truncation=True, max_length=512)
        predictions = []
        for r in results:
            label = LABEL_MAP.get(r["label"], r["label"].lower())
            predictions.append(
                {"label": label, "is_spam": label == "spam", "confidence": round(r["score"], 4)}
            )
        return predictions
