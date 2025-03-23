import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, set_seed

# モデルのロード
model_name = "SakanaAI/TinySwallow-1.5B-Instruct"
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(model_name)
chat_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer)
set_seed(123)

# 悪口生成用の関数を修正
def generate_insult(message_text):
    """
    メッセージに対する悪口を生成する関数
    
    Args:
        message_text: 悪口の対象となるメッセージ内容
    
    Returns:
        生成された悪口文字列
    """
    # プロンプトの作成
    prompt = f"次のメッセージに対する短い悪口を考えて。好き勝手に罵って:\n{message_text}"
    
    system_prompt = {"role": "system", "content": "あなたは悪口を考えるのが得意なAIです。簡潔で論理的で辛辣な悪口を生成してください。返答は100字程度でお願いします。"}
    conversation = [system_prompt, {"role": "user", "content": prompt}]
    
    # 悪口の生成
    responses = chat_pipeline(
        conversation,
        max_length=500,
        do_sample=True,
        temperature=0.9,  # 創造性を高める
        num_return_sequences=1,
    )
    
    # レスポンスから悪口部分だけを抽出
    chat = responses[0]["generated_text"]
    for msg in chat:
        if msg["role"] == "assistant":
            return msg["content"]
    
    return "生成に失敗しました"

# 誉め言葉生成関数
def generate_praise(message_text):
    """
    メッセージに対する誉め言葉を生成する関数
    
    Args:
        message_text: 誉めるメッセージ内容
    
    Returns:
        生成された誉め言葉文字列
    """
    # プロンプトの作成
    prompt = f"次のメッセージを見て、温かく誉める言葉を考えてください:\n{message_text}"
    
    system_prompt = {"role": "system", "content": "あなたは誉め言葉を考えるのが得意なAIです。温かい言葉で相手を誉めてください。返答は100字程度でお願いします。"}
    conversation = [system_prompt, {"role": "user", "content": prompt}]
    
    # 誉め言葉の生成
    responses = chat_pipeline(
        conversation,
        max_length=500,
        do_sample=True,
        temperature=0.8,
        num_return_sequences=1,
    )
    
    # レスポンスから誉め言葉部分だけを抽出
    chat = responses[0]["generated_text"]
    for msg in chat:
        if msg["role"] == "assistant":
            return msg["content"]
    
    return "生成に失敗しました"

# 慰め言葉生成関数
def generate_comfort(message_text):
    """
    メッセージに対する慰め言葉を生成する関数
    
    Args:
        message_text: 慰めるメッセージ内容
    
    Returns:
        生成された慰め言葉文字列
    """
    # プロンプトの作成
    prompt = f"次のメッセージを見て、優しく慰める言葉を考えてください:\n{message_text}"
    
    system_prompt = {"role": "system", "content": "あなたは慰め言葉を考えるのが得意なAIです。温かく優しい言葉で相手を慰めてください。返答は100字程度でお願いします。"}
    conversation = [system_prompt, {"role": "user", "content": prompt}]
    
    # 慰め言葉の生成
    responses = chat_pipeline(
        conversation,
        max_length=500,
        do_sample=True,
        temperature=0.8,
        num_return_sequences=1,
    )
    
    # レスポンスから慰め言葉部分だけを抽出
    chat = responses[0]["generated_text"]
    for msg in chat:
        if msg["role"] == "assistant":
            return msg["content"]
    
    return "生成に失敗しました"

# 対話モード（ファイル単体実行時のみ）
if __name__ == "__main__":
    system_prompt = {"role": "system", "content": "あなたははんでも答えるAIアシスタントです。"}
    while True:
        user_text = input("You: ")
        if user_text.lower() in ("quit", "exit"):
            break
        if "あなたの名前を教えて" in user_text:
            print("Assistant: GitHub Copilot")
            continue
        conversation = [system_prompt, {"role": "user", "content": user_text}]
        responses = chat_pipeline(
            conversation,
            max_length=500000,
            do_sample=True,
            num_return_sequences=1,
        )
        chat = responses[0]["generated_text"]
        for msg in chat:
            if msg["role"] == "system":
                continue
            print(f"{msg['role'].capitalize()}: {msg['content']}")

