import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, set_seed

# モデルのロード
model_name = "SakanaAI/TinySwallow-1.5B-Instruct"
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(model_name)
chat_pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer)
set_seed(123)

# 悪口生成用の関数を追加
def generate_insult(user_name, user_messages):
    """
    ユーザー名とそのメッセージリストから悪口を生成する関数
    
    Args:
        user_name: ユーザーの名前
        user_messages: ユーザーのメッセージのリスト
    
    Returns:
        生成された悪口文字列
    """
    # メッセージを結合（長すぎる場合は最新の5つだけ使用）
    if len(user_messages) > 5:
        sample_messages = user_messages[-5:]
    else:
        sample_messages = user_messages
        
    message_text = "\n".join(sample_messages)
    
    # プロンプトの作成
    prompt = f"{user_name}というユーザーの最近のメッセージ:\n{message_text}\n\n{user_name}への短い悪口を考えて。好き勝手に罵って。"
    
    system_prompt = {"role": "system", "content": "あなたは悪口を考えるのが得意なAIです。簡潔で論理的で辛辣な悪口を生成してください。返答は100字程度でお願いします。"}
    conversation = [system_prompt, {"role": "user", "content": prompt}]
    
    # 悪口の生成
    responses = chat_pipeline(
        conversation,
        max_length=1000,
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

