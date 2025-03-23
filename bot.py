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
import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.font_manager as fm  # フォント管理のためのインポート追加

# 環境変数から設定を読み込む
load_dotenv()  # .env ファイルを読み込む

# Discordボットの設定
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# カスタムフォントを登録して使用する関数
def setup_custom_font():
    custom_font_path = "./NotoSansCJKjp-Regular.ttf"
    if os.path.exists(custom_font_path):
        print(f"カスタムフォントを登録します: {custom_font_path}")
        try:
            # フォントを明示的に登録
            font_prop = fm.FontProperties(fname=custom_font_path)
            custom_font = fm.FontEntry(
                fname=custom_font_path,
                name=font_prop.get_name(),
                style='normal',
                variant='normal',
                weight='normal',
                stretch='normal',
                size='medium'
            )
            fm.fontManager.ttflist.insert(0, custom_font)
            print(f"フォント登録成功: {font_prop.get_name()}")
            return font_prop.get_name()
        except Exception as e:
            print(f"カスタムフォントの登録に失敗しました: {e}")
    return None

# 利用可能な日本語フォントを検出する関数
def get_available_japanese_font():
    # まず指定のTTFファイルを確認
    custom_font_path = "./NotoSansCJKjp-Regular.ttf"
    if os.path.exists(custom_font_path):
        return setup_custom_font()
    
    # Ubuntu環境で一般的に利用可能な日本語フォント候補
    font_candidates = [
        "Noto Sans CJK JP",  # 正しいフォント名に修正
        'MS Gothic',  # Windows用も一応残す
        'IPAGothic',  # 他の一般的な日本語フォント
    ]
    
    for font in font_candidates:
        try:
            fm.findfont(font, fallback_to_default=False)
            print(f"利用可能な日本語フォントを発見: {font}")
            return font
        except:
            pass
    
    print("日本語フォントが見つかりませんでした。デフォルトフォントを使用します。")
    return 'sans-serif'

# 日本語フォントの設定（システムに合わせて自動検出）
plt.style.use('default')
# まずカスタムフォントを直接登録
custom_font_name = setup_custom_font()
if custom_font_name:
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = [custom_font_name]
    plt.rcParams['font.family'] = custom_font_name
else:
    # カスタムフォントが登録できなかった場合は従来の方法で検出
    japanese_font = get_available_japanese_font()
    plt.rcParams['font.family'] = japanese_font

# Discord色の設定は維持
plt.rcParams['axes.facecolor'] = '#36393F'  # 背景色をDiscordのダークテーマ色に変更
plt.rcParams['figure.facecolor'] = '#36393F'  # 外枠も同じ色に統一
plt.rcParams['axes.edgecolor'] = '#ffffff'  # 軸の色を白に
plt.rcParams['axes.labelcolor'] = 'white'  # ラベルの色
plt.rcParams['xtick.color'] = 'white'  # X軸の目盛りの色
plt.rcParams['ytick.color'] = 'white'  # Y軸の目盛りの色

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
        # 新しいモデルの感情マッピング
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
        fig, ax = plt.subplots(figsize=(12, 8))  # 16:9のアスペクト比に変更
        
        # カスタムカラーで装飾したバー - 青系の色に変更
        color = '#5865F2'  # Discord Blurple（Discordの青色）に変更
        bar = ax.bar([categories[0]], [values[0]], width=0.5, color=color, alpha=0.9)
        ax.set_ylim(0, 1.1)  # 少し余裕を持たせる
        
        # 枠線の色を変更
        for spine in ax.spines.values():
            spine.set_color('#ffffff')
        
        # タイトルを装飾
        plt.title(f"感情分析結果: {categories[0]}", fontsize=18, color='white', fontweight='bold')
        
        # バーの上に値を表示
        ax.text(0, values[0] + 0.05, f"{values[0]:.2f}", ha='center', fontsize=14, color='#7289DA')
        
        # グリッドを追加 - 白色で鮮明に
        ax.yaxis.grid(True, linestyle='-', alpha=0.7, color='white', linewidth=1.5)
        
        # 背景色を設定
        ax.set_facecolor('#36393F')  # 既に設定済み
        fig.patch.set_facecolor('#36393F')  # 外枠もDiscordの背景色に
        
        return fig
    
    # 角度の計算 (n等分) とデータの繰り返し
    angles = np.linspace(0, 2 * np.pi, num_categories, endpoint=False).tolist()
    values += values[:1]  # 最初の値を最後にも追加して円を閉じる
    angles += angles[:1]  # 最初の角度を最後にも追加

    # 極座標プロットの設定
    fig, ax = plt.subplots(figsize=(12, 9), subplot_kw={'projection': 'polar'})
    
    # 背景色とグリッドの設定
    ax.set_facecolor('#36393F')  # Discordのダークテーマカラー
    fig.patch.set_facecolor('#36393F')  # 外枠も同じ色に
    
    # 角度の設定
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    # カスタムカラーマップを作成
    colors = [(0.35, 0.4, 0.95, 0.7), (0.45, 0.6, 0.95, 0.8), (0.55, 0.7, 0.95, 0.9)]  # 青系グラデーション
    cmap = LinearSegmentedColormap.from_list('custom_cmap', colors, N=256)
    
    # データ描画
    line = ax.plot(angles, values, linewidth=4, linestyle='-', color='#7289DA')[0]  # データ線は青のまま、太く
    # グラデーションカラーで塗り潰し
    ax.fill(angles, values, alpha=0.7, color='#5865F2')  # 透明度を下げてよりはっきりと
    
    # マーカーを別途追加（より大きく装飾的に）
    ax.scatter(angles[:-1], values[:-1], s=180, c='#40E0D0', alpha=1.0, 
               edgecolors='#00BFFF', linewidth=3, zorder=10)  # サイズと線の太さを増加
    
    # 放射状の線を白色で太く、はっきりと設定
    ax.grid(True, color='white', alpha=0.7, linestyle='-', linewidth=1.5)
    
    # 軸ラベル設定 - Ubuntu環境を考慮してフォントサイズを調整
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=24)  # フォントサイズを調整（40から24に）
    
    # 半径の範囲を設定
    ax.set_ylim(0, 1)
    
    # 同心円のグリッド線をスタイリング - 白色で鮮明に
    ax.set_rticks([0.25, 0.5, 0.75, 1.0])  # より目立つ値に調整
    gridlines = ax.yaxis.get_gridlines()
    for gl in gridlines:
        gl.set_color('white')
        gl.set_alpha(0.6)  # 透明度を下げてはっきりと
        gl.set_linestyle('-')
        gl.set_linewidth(1.5)  # 線を太く
    
    # 目盛りを非表示に設定
    ax.set_yticklabels([])  # 数値を非表示
    
    # ラベルサイズを拡大（色はすでに白っぽい色に設定済み）
    ax.tick_params(labelsize=40, colors='white', grid_color='white')
    
    # 外枠を非表示
    ax.spines['polar'].set_visible(False)
    
    return fig

# ボットトークンを設定してボットを実行
bot.run(os.getenv('DISCORD_TOKEN'))  # .envファイルからトークンを読み込む