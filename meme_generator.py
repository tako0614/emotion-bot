from PIL import Image, ImageDraw, ImageFont
import io
import os
import colorsys
from typing import Optional, Tuple


def _load_font(size, weight='Regular'):
    """フォントを読み込む"""
    repo_dir = os.path.dirname(__file__)
    gg_sans_path = os.path.join(repo_dir, 'gg-sans-2', f'gg sans {weight}.ttf')
    gg_sans_regular_path = os.path.join(repo_dir, 'gg-sans-2', 'gg sans Regular.ttf')
    noto_path = os.path.join(repo_dir, 'NotoSansCJKjp-Regular.ttf')

    # 優先順位でフォントを試行
    for font_path in [gg_sans_path, gg_sans_regular_path, noto_path]:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue

    # システムフォント
    for sys_fp in ('arial.ttf', 'DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(sys_fp, size)
        except Exception:
            continue

    return ImageFont.load_default()


def create_rainbow_gradient(text: str, start_hue: float = 0.0) -> list:
    """
    文字ごとに虹色のグラデーションカラーを生成

    Args:
        text: テキスト
        start_hue: 開始色相（0.0-1.0）

    Returns:
        list of RGB tuples
    """
    colors = []
    text_len = len(text)

    for i, char in enumerate(text):
        # 文字位置に応じて色相を変化させる
        hue = (start_hue + (i / max(text_len, 1))) % 1.0
        saturation = 0.9
        value = 0.95

        # HSVからRGBに変換
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))

    return colors


def draw_text_with_rainbow(
    draw: ImageDraw.Draw,
    position: Tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont,
    start_hue: float = 0.0
) -> int:
    """
    虹色のテキストを描画

    Args:
        draw: ImageDraw オブジェクト
        position: 描画位置 (x, y)
        text: テキスト
        font: フォント
        start_hue: 開始色相

    Returns:
        描画後のx座標
    """
    x, y = position
    colors = create_rainbow_gradient(text, start_hue)

    for char, color in zip(text, colors):
        # 影を描画（より目立たせる）
        shadow_offset = 3
        draw.text((x + shadow_offset, y + shadow_offset), char, font=font, fill=(0, 0, 0, 180))

        # メインテキストを描画
        draw.text((x, y), char, font=font, fill=color)

        # 次の文字の位置を計算
        bbox = draw.textbbox((0, 0), char, font=font)
        char_width = bbox[2] - bbox[0]
        x += char_width

    return x


def generate_meme_image(
    text: str,
    bg_color: str = 'black',
    rainbow_text: bool = False,
    font_size: int = 60,
    swap_layout: bool = False,
    author_name: str = '',
    font_name: str = 'default',
    avatar_image: bytes = None
) -> io.BytesIO:
    """
    ミーム画像を生成

    Args:
        text: 表示するテキスト
        bg_color: 背景色 ('black' or 'white')
        rainbow_text: 虹色テキストを使用するか
        font_size: フォントサイズ
        swap_layout: レイアウトを左右反転するか
        author_name: 作者名（下部に小さく表示）
        font_name: フォント名（'default', 'noto', 'gg-sans'）
        avatar_image: ユーザーのアバター画像（bytes）

    Returns:
        BytesIO: PNG画像データ
    """
    # 画像サイズ
    width = 1280
    height = 720

    # 背景色の設定
    if bg_color == 'white':
        bg = (255, 255, 255)
        text_color = (0, 0, 0)
        date_color = (100, 100, 100)
    else:  # black
        bg = (0, 0, 0)
        text_color = (255, 255, 255)
        date_color = (150, 150, 150)

    # キャンバス作成
    img = Image.new('RGB', (width, height), bg)

    # アバター画像を背景として使用（斜めのグラデーションマスク付き）
    if avatar_image:
        try:
            avatar_img = Image.open(io.BytesIO(avatar_image)).convert('RGB')

            # アバター画像のアスペクト比を保ってトリミング
            # 画面の高さに合わせて、中央部分を切り取る
            avatar_aspect = avatar_img.width / avatar_img.height
            target_aspect = width / height

            if avatar_aspect > target_aspect:
                # アバター画像が横長すぎる場合、左右をトリミング
                new_width = int(avatar_img.height * target_aspect)
                left = (avatar_img.width - new_width) // 2
                avatar_cropped = avatar_img.crop((left, 0, left + new_width, avatar_img.height))
            else:
                # アバター画像が縦長すぎる場合、上下をトリミング
                new_height = int(avatar_img.width / target_aspect)
                top = (avatar_img.height - new_height) // 2
                avatar_cropped = avatar_img.crop((0, top, avatar_img.width, top + new_height))

            # トリミングした画像を画面全体にリサイズ
            avatar_full = avatar_cropped.resize((width, height), Image.LANCZOS)

            # 斜めのグラデーションマスクを作成
            mask = Image.new('L', (width, height), 0)

            # グラデーションの幅（ぼかしの範囲）
            gradient_width = 150

            # 画像:テキスト = 1:3 または 3:1 の割合
            # 左側配置の場合: 左25%が画像、右75%がテキスト
            # 右側配置の場合: 左75%がテキスト、右25%が画像
            if swap_layout:
                # 右側に配置（右下から左上へ）- 右25%が画像
                # 画像領域の中心: 87.5% (75% + 12.5%)
                avatar_center = int(width * 0.875)
                gradient_start = int(width * 0.75)
            else:
                # 左側に配置（左下から右上へ）- 左25%が画像
                # 画像領域の中心: 12.5%
                avatar_center = int(width * 0.125)
                gradient_start = int(width * 0.25)

            # 各ピクセルごとにグラデーションを計算
            for y in range(height):
                for x in range(width):
                    # 斜めの距離を計算（y座標で少し傾ける）
                    diagonal_offset = int(y * 0.2)  # 傾きを少し緩やかに

                    if swap_layout:
                        # 右側の場合は右から左へ
                        adjusted_x = x + diagonal_offset

                        # グラデーション範囲内でアルファ値を計算
                        if adjusted_x > gradient_start + gradient_width:
                            alpha = 255  # 完全に表示
                        elif adjusted_x > gradient_start:
                            # グラデーション範囲内
                            ratio = (adjusted_x - gradient_start) / gradient_width
                            alpha = int(255 * ratio)
                        else:
                            alpha = 0  # 完全に透明
                    else:
                        # 左側の場合は左から右へ
                        adjusted_x = x - diagonal_offset

                        # グラデーション範囲内でアルファ値を計算
                        if adjusted_x < gradient_start - gradient_width:
                            alpha = 255  # 完全に表示
                        elif adjusted_x < gradient_start:
                            # グラデーション範囲内
                            ratio = (gradient_start - adjusted_x) / gradient_width
                            alpha = int(255 * ratio)
                        else:
                            alpha = 0  # 完全に透明

                    mask.putpixel((x, y), alpha)

            # マスクを使ってアバター画像を合成
            img.paste(avatar_full, (0, 0), mask)

        except Exception as e:
            print(f"アバター画像の読み込みに失敗: {e}")

    draw = ImageDraw.Draw(img, 'RGBA')

    # フォントの読み込み
    repo_dir = os.path.dirname(__file__)

    # フォント名に応じてパスを選択
    if font_name == 'noto':
        font_path = os.path.join(repo_dir, 'NotoSansCJKjp-Regular.ttf')
    elif font_name == 'gg-sans':
        font_path = os.path.join(repo_dir, 'gg-sans-2', 'gg sans Bold.ttf')
    else:
        # デフォルト（自動選択）
        font_path = None
        font = _load_font(font_size, 'Bold')

    if font_path and os.path.exists(font_path):
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = _load_font(font_size, 'Bold')
    elif font_path:
        font = _load_font(font_size, 'Bold')

    # テキスト領域の計算（画像:テキスト = 1:3 の割合）
    text_padding = 80

    if swap_layout:
        # 左側にテキスト（75%の領域）
        text_area_left = text_padding
        text_area_right = int(width * 0.75) - text_padding
    else:
        # 右側にテキスト（75%の領域、デフォルト）
        text_area_left = int(width * 0.25) + text_padding
        text_area_right = width - text_padding

    text_area_width = text_area_right - text_area_left

    # テキストを複数行に分割
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + word + " "
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]

        if line_width <= text_area_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line.strip())
            current_line = word + " "

    if current_line:
        lines.append(current_line.strip())

    # テキストの描画位置を計算
    line_height = font_size + 20
    total_text_height = line_height * len(lines)
    text_start_y = (height - total_text_height) // 2

    # テキストを描画
    for i, line in enumerate(lines):
        y = text_start_y + i * line_height

        # 中央揃え
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        x = text_area_left + (text_area_width - line_width) // 2

        if rainbow_text:
            # 虹色で描画
            draw_text_with_rainbow(draw, (x, y), line, font, start_hue=i * 0.1)
        else:
            # 影を描画
            shadow_offset = 3
            draw.text((x + shadow_offset, y + shadow_offset), line, font=font, fill=(0, 0, 0, 180))

            # 通常のテキスト
            draw.text((x, y), line, font=font, fill=text_color)

    # 日付を右下に描画
    date_text = "2025-10-28"
    date_font = _load_font(20)
    date_bbox = draw.textbbox((0, 0), date_text, font=date_font)
    date_width = date_bbox[2] - date_bbox[0]
    date_height = date_bbox[3] - date_bbox[1]

    date_x = width - date_width - 30
    date_y = height - date_height - 20
    draw.text((date_x, date_y), date_text, font=date_font, fill=date_color)

    # 作者名を右下（日付の上）に描画
    if author_name:
        author_font = _load_font(18)
        author_text = f"- {author_name}"
        author_bbox = draw.textbbox((0, 0), author_text, font=author_font)
        author_width = author_bbox[2] - author_bbox[0]
        author_height = author_bbox[3] - author_bbox[1]

        author_x = width - author_width - 30
        author_y = date_y - author_height - 10
        draw.text((author_x, author_y), author_text, font=author_font, fill=date_color)

    # 透かし（takomc.com）を左下に小さく描画
    watermark_text = "takomc.com"
    watermark_font = _load_font(16)
    watermark_bbox = draw.textbbox((0, 0), watermark_text, font=watermark_font)
    watermark_height = watermark_bbox[3] - watermark_bbox[1]

    watermark_x = 30
    watermark_y = height - watermark_height - 20

    # 透かしは半透明で描画
    watermark_alpha = 150
    if bg_color == 'white':
        watermark_color = (100, 100, 100, watermark_alpha)
    else:
        watermark_color = (150, 150, 150, watermark_alpha)

    draw.text((watermark_x, watermark_y), watermark_text, font=watermark_font, fill=watermark_color)

    # BytesIOに保存（圧縮なし、最高品質）
    buf = io.BytesIO()
    img.save(buf, format='PNG', compress_level=0, optimize=False)
    buf.seek(0)

    return buf


