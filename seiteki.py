from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

tokenizer = AutoTokenizer.from_pretrained("oshizo/japanese-sexual-moderation-v2")
model = AutoModelForSequenceClassification.from_pretrained("oshizo/japanese-sexual-moderation-v2")
classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)

def classify_sexual_content(text: str) -> str:
    result = classifier(text)[0]
    score = result["score"]
    if score <= 0.2:
        return 0
    elif score <= 0.4:
        return 1
    elif score <= 0.6:
        return 2
    elif score <= 0.8:
        return 3
    else:
        return 4

# テキストを分類
text = "チンコ食べたい"
result = classify_sexual_content(text)
print(result)  # 0