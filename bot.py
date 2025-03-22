import discord
from discord.ext import commands
import matplotlib.pyplot as plt
import numpy as np
import io
import traceback
import random  # ランダム化のためにインポート追加
import os
from dotenv import load_dotenv  # python-dotenv パッケージを追加
from emotion import get_emotion_scores

# 環境変数から設定を読み込む
load_dotenv()  # .env ファイルを読み込む

# Discordボットの設定
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 日本語フォントの設定（使用環境に合わせて変更）
plt.rcParams['font.family'] = 'MS Gothic'  # Windowsの場合
# plt.rcParams['font.family'] = 'Hiragino Sans'  # Macの場合
# plt.rcParams['font.family'] = 'IPAexGothic'  # Linuxの場合

@bot.event
async def on_ready():
    print(f'ボットの準備完了。ログイン名: {bot.user}')

@bot.event
async def on_message(message):
    # ボット自身のメッセージは無視
    if message.author == bot.user:
        return
        
    # 「きもち」というリプライを検出
    if message.reference and message.content == "きもち":
        # リプライ先のメッセージを取得
        referenced_msg = await message.channel.fetch_message(message.reference.message_id)
        
        # メッセージの内容がない場合は処理しない
        if not referenced_msg.content:
            await message.reply("テキストメッセージにのみ反応できます。")
            return
            
        # リプライ先メッセージの感情分析
        text = referenced_msg.content
        
        try:
            # 全ての感情スコアを取得
            emotion_scores = get_emotion_scores(text)
            print(f"Raw emotion scores: {emotion_scores}")
            
            # 先にneutralを明示的に除外（大文字小文字を区別しない）
            emotion_scores = {k: v for k, v in emotion_scores.items() 
                             if k.lower() != 'neutral'}
            print(f"After removing neutral: {emotion_scores}")
            
            # スコアが存在するか確認
            if not emotion_scores:
                await message.reply("感情スコアを取得できませんでした。別のテキストで試してください。")
                return
                
            # スコア上位5つを選択（neutralを除外したので最大5つ）
            top_emotions = get_top_emotions(emotion_scores, 5)
            print(f"Top emotions: {top_emotions}")
            
            # スコアをスケーリング
            scaled_emotions = scale_emotion_scores(top_emotions)
            print(f"Scaled emotions: {scaled_emotions}")
            
            # 5角形グラフの生成
            fig = create_emotion_polygon(scaled_emotions)
            
            # グラフを画像に変換
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close(fig)
            
            # グラフと元メッセージをリプライ
            file = discord.File(buf, filename='emotions.png')
            await message.reply(f'メッセージ: "{text}"\n感情分析結果:', file=file)
        except KeyError as ke:
            print(f"キーエラーが発生しました: {ke}")
            traceback.print_exc()
            await message.reply(f"感情解析中にキーエラーが発生しました: {ke}")
        except Exception as e:
            print(f"エラーが発生しました: {e}")
            import traceback
            traceback.print_exc()  # より詳細なエラー情報を表示
            await message.reply(f"処理中にエラーが発生しました: {e}")

# スコアが高い感情を取得する関数
def get_top_emotions(emotion_scores, n=5):  # デフォルトを5に変更（6から5へ）
    """
    感情スコアの中から上位n個を選択する
    """
    # 辞書が空の場合にエラー回避
    if not emotion_scores:
        raise ValueError("感情スコアが空です")
    
    # neutralを再確認して除外（大文字小文字を区別しない）
    filtered_scores = {}
    for k, v in emotion_scores.items():
        if k.lower() != 'neutral':
            filtered_scores[k] = v
        else:
            print(f"Excluded neutral emotion: {k} with score {v}")
    
    emotion_scores = filtered_scores
    
    # スコア値がゼロでないものだけを対象にする
    non_zero_scores = {k: v for k, v in emotion_scores.items() if v > 0.001}  # しきい値を調整
    
    # 非ゼロのスコアがない場合は、元のすべてのスコアから選択
    if not non_zero_scores:
        print("警告: すべての感情スコアがほぼゼロです")
        non_zero_scores = emotion_scores
    
    # スコアで降順ソートして上位n個を選択
    top_n = sorted(non_zero_scores.items(), key=lambda x: x[1], reverse=True)[:min(n, len(non_zero_scores))]
    
    # 選択された感情が少なくとも1つ以上あることを確認
    if not top_n:
        raise ValueError("有効な感情スコアがありません")
    
    return dict(top_n)

# 感情スコアをスケーリングする関数を追加
def scale_emotion_scores(scores):
    """
    小さな感情スコアを視覚化しやすくスケーリングする
    方法1: 最大値を1.0にスケーリング
    方法2: すべての値を一定倍にする
    方法3: 最小閾値を設定（一定値以下は最低値にする）
    """
    if not scores:
        return {}
        
    # 最大値を基準にスケーリング
    max_val = max(scores.values())
    if max_val > 0:
        return {k: v/max_val for k, v in scores.items()}
    
    return scores  # スケーリングできない場合は元の値を返す

# グラフ作成関数を修正（動的に感情の数に対応）
def create_emotion_polygon(emotion_scores):
    # データの検証
    if not emotion_scores:
        raise ValueError("感情スコアが空です")
    
    # 念のため最終確認でneutralを除外
    emotion_scores = {k: v for k, v in emotion_scores.items() if k.lower() != 'neutral'}
    
    # 感情の英語から日本語への対応表 - 新しいモデルの形式に対応
    emotion_names_ja = {
        "amaze": "びっくり！",
        "anger": "おこったぞおおおお",
        "dislike": "きらい、",
        "excite": "興奮するぅうう",
        "fear": "こわいよぉ",
        "joy": "うれしいい！",
        "like": "好き♡",
        "relief": "安心すりゅぅ",
        "sad": "悲しいよぉ",
        "shame": "恥ずかしい ///"
    }
    
    # 英語のラベルを日本語に変換
    japanese_scores = {}
    for eng_key, score in emotion_scores.items():
        ja_key = emotion_names_ja.get(eng_key)
        if ja_key:
            japanese_scores[ja_key] = score
        else:
            # 未知の感情ラベルの場合はデバッグ出力して英語のまま使用
            japanese_scores[eng_key] = score
            print(f"警告: 未知の感情ラベル '{eng_key}' が検出されました")
    
    # 日本語変換後のスコアで置き換え
    emotion_scores = japanese_scores
    print(f"日本語に変換後: {emotion_scores}")
    
    # カテゴリーの順序をランダム化する
    items = list(emotion_scores.items())
    random.shuffle(items)  # 順序をランダムに並べ替え
    emotion_scores = dict(items)
    print(f"ランダム化後の順序: {emotion_scores}")
    
    # カテゴリーとスコアを取得
    categories = list(emotion_scores.keys())
    values = [emotion_scores[cat] for cat in categories]
    
    # データ検証
    if len(categories) < 1:
        raise ValueError("表示する感情がありません")
    
    # 角度の計算 - カテゴリが1つしかない場合の特別処理
    num_categories = len(categories)
    if num_categories == 1:
        # 1つだけの場合は円グラフに変更
        fig, ax = plt.subplots(figsize=(8, 8))
        ax.bar([categories[0]], [values[0]], width=0.5)
        ax.set_ylim(0, 1)
        plt.title(f"感情分析結果: {categories[0]}", fontsize=16)
        return fig
    
    # 角度の計算 (n等分) とデータの繰り返し
    angles = np.linspace(0, 2 * np.pi, num_categories, endpoint=False).tolist()
    values += values[:1]  # 最初の値を最後にも追加して円を閉じる
    angles += angles[:1]  # 最初の角度を最後にも追加

    # 極座標プロットの設定
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # データ描画
    ax.plot(angles, values, linewidth=3, linestyle='-', marker='o', markersize=10)
    ax.fill(angles, values, alpha=0.4)

    # 軸ラベル設定 - すでに日本語に変換済みなので追加の変換は不要
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories)  # そのまま使用

    # 半径の範囲を0～1に設定
    ax.set_ylim(0, 1)
    
    # グリッド設定
    ax.grid(True, linewidth=1.0, alpha=0.4)
    
    # 目盛りを非表示に設定
    ax.set_rticks([])  # 半径方向の目盛りを消す
    
    # ラベルサイズを3倍程度に拡大（10→30）
    ax.tick_params(labelsize=30)
    
    # タイトルを削除（以下の行をコメントアウト）
    # plt.title("感情分析結果（上位5つ）", fontsize=16, pad=20)
    
    return fig

# ボットトークンを設定してボットを実行
bot.run(os.getenv('DISCORD_TOKEN'))  # .envファイルからトークンを読み込む