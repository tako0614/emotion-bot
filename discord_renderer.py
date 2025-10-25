from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import textwrap
import os
import re
from typing import List, Tuple, Optional


def _load_font(size, weight='Regular'):
    # 優先してリポジトリ内のフォントを使用（gg-sans-2 の指定ウェイトを優先）
    # weight: 'Regular', 'Medium', 'Semibold', 'Bold'
    repo_dir = os.path.dirname(__file__)
    gg_sans_path = os.path.join(repo_dir, 'gg-sans-2', f'gg sans {weight}.ttf')
    gg_sans_regular_path = os.path.join(repo_dir, 'gg-sans-2', 'gg sans Regular.ttf')
    noto_path = os.path.join(repo_dir, 'NotoSansCJKjp-Regular.ttf')

    def _test_font(fp):
        try:
            f = ImageFont.truetype(fp, size)
        except Exception:
            return None
        # より確実なチェック：フォントが日本語グリフを持っているかを getmask で確認
        try:
            mask = f.getmask('あ')
            bbox = mask.getbbox()
            if bbox is not None and (bbox[2] - bbox[0]) > 0:
                return f
            # グリフが無い場合は None を返す
            return None
        except Exception:
            # getmask が利用できない場合は従来のテキスト描画で確認
            try:
                tmp = Image.new('RGB', (64, 64), (0, 0, 0))
                td = ImageDraw.Draw(tmp)
                bbox = td.textbbox((0, 0), 'あ', font=f)
                if bbox and (bbox[2] - bbox[0]) > 0:
                    return f
            except Exception:
                pass
            return None

    # まず指定ウェイトの gg-sans を試す
    if os.path.exists(gg_sans_path):
        f = _test_font(gg_sans_path)
        if f:
            print(f"使用フォント: {gg_sans_path}")
            return f

    # 指定ウェイトが見つからない場合は Regular を試す
    if weight != 'Regular' and os.path.exists(gg_sans_regular_path):
        f = _test_font(gg_sans_regular_path)
        if f:
            print(f"使用フォント（フォールバック）: {gg_sans_regular_path}")
            return f

    # 次に Noto（日本語対応）を試す
    if os.path.exists(noto_path):
        f = _test_font(noto_path)
        if f:
            print(f"使用フォント: {noto_path}")
            return f

    # システムフォントを試す（候補をいくつか）
    for sys_fp in ('arial.ttf', 'DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            f = ImageFont.truetype(sys_fp, size)
            print(f"使用システムフォント: {sys_fp}")
            return f
        except Exception:
            continue

    # 最終的なフォールバック
    return ImageFont.load_default()


def _get_fallback_fonts(size, weight='Regular'):
    """
    フォールバックフォントのリストを返す（優先順位順）
    各フォントには識別用のメタデータ（パス）を保持
    """
    fonts = []
    repo_dir = os.path.dirname(__file__)

    # 1. gg-sans (指定ウェイト)
    gg_sans_path = os.path.join(repo_dir, 'gg-sans-2', f'gg sans {weight}.ttf')
    if os.path.exists(gg_sans_path):
        try:
            font = ImageFont.truetype(gg_sans_path, size)
            # パス情報を保持（フォールバック判定用）
            font._font_path = gg_sans_path
            fonts.append(font)
            print(f"[フォント読込] gg-sans {weight}: {gg_sans_path}")
        except Exception as e:
            print(f"[フォント読込失敗] gg-sans {weight}: {e}")

    # 2. gg-sans (Regular)
    if weight != 'Regular':
        gg_sans_regular = os.path.join(repo_dir, 'gg-sans-2', 'gg sans Regular.ttf')
        if os.path.exists(gg_sans_regular):
            try:
                font = ImageFont.truetype(gg_sans_regular, size)
                font._font_path = gg_sans_regular
                fonts.append(font)
                print(f"[フォント読込] gg-sans Regular: {gg_sans_regular}")
            except Exception as e:
                print(f"[フォント読込失敗] gg-sans Regular: {e}")

    # 3. Noto Sans CJK (日本語対応) - 最優先にする
    noto_path = os.path.join(repo_dir, 'NotoSansCJKjp-Regular.ttf')
    print(f"[Notoフォント] パス: {noto_path}, 存在: {os.path.exists(noto_path)}")
    if os.path.exists(noto_path):
        try:
            font = ImageFont.truetype(noto_path, size)
            font._font_path = noto_path
            font._is_cjk = True  # CJK対応フラグ
            fonts.append(font)
            print(f"[フォント読込] Noto Sans CJK: {noto_path}")
        except Exception as e:
            print(f"[フォント読込失敗] Noto Sans CJK: {e}")
    else:
        print(f"[警告] Notoフォントが見つかりません: {noto_path}")

    # 4. システムフォント
    for sys_fp in ('arial.ttf', 'DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try:
            font = ImageFont.truetype(sys_fp, size)
            font._font_path = sys_fp
            fonts.append(font)
            print(f"[フォント読込] システムフォント: {sys_fp}")
        except Exception:
            continue

    # 5. デフォルトフォント
    if not fonts:
        font = ImageFont.load_default()
        font._font_path = 'default'
        fonts.append(font)
        print(f"[フォント読込] デフォルトフォント")

    print(f"[フォント読込完了] 合計 {len(fonts)} 個のフォントを読み込みました")
    return fonts


def _has_cjk_character(text):
    """
    テキストに日本語・中国語・韓国語の文字が含まれているかチェック
    """
    for char in text:
        code = ord(char)
        # CJK統合漢字、ひらがな、カタカナ、ハングルなど
        if (0x4E00 <= code <= 0x9FFF or  # CJK統合漢字
            0x3040 <= code <= 0x309F or  # ひらがな
            0x30A0 <= code <= 0x30FF or  # カタカナ
            0xAC00 <= code <= 0xD7AF or  # ハングル
            0x3400 <= code <= 0x4DBF or  # CJK拡張A
            0x20000 <= code <= 0x2A6DF): # CJK拡張B
            return True
    return False


def _draw_text_with_fallback(draw, pos, text, fonts, fill):
    """
    複数のフォントを使って文字列を描画する
    CJK文字が含まれている場合は自動的にNotoフォントを優先
    """
    if not text:
        return pos[0]

    x, y = pos

    # CJK文字が含まれている場合は、CJK対応フォントを最優先
    has_cjk = _has_cjk_character(text)

    if has_cjk:
        print(f"[CJK検出] テキスト: {text[:20]}... (has_cjk={has_cjk})")
        # fontsリストを並び替えて、CJK対応フォントを最初に
        reordered_fonts = []
        other_fonts = []
        for font in fonts:
            try:
                # _is_cjk フラグをチェック
                is_cjk_font = getattr(font, '_is_cjk', False)
                font_path = getattr(font, '_font_path', '').lower()

                if is_cjk_font or 'noto' in font_path or 'cjk' in font_path:
                    reordered_fonts.append(font)
                    print(f"  [CJK優先] {font_path}")
                else:
                    other_fonts.append(font)
            except Exception:
                other_fonts.append(font)
        fonts = reordered_fonts + other_fonts
        print(f"  [フォント順序] CJK: {len(reordered_fonts)}, その他: {len(other_fonts)}")

    # フォントを順番に試行
    for i, font in enumerate(fonts):
        try:
            font_path = getattr(font, '_font_path', 'unknown')
            # テキスト全体を一度に描画
            draw.text((x, y), text, font=font, fill=fill)
            # 幅を計算
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
            x += width
            if has_cjk:
                print(f"  [描画成功] フォント: {font_path}, 幅: {width}")
            return x
        except Exception as e:
            # デバッグ用: どのフォントで失敗したか記録
            if has_cjk or i == 0:  # CJKまたは最初のフォントのエラーのみ表示
                print(f"  [描画失敗] フォント {getattr(font, '_font_path', 'unknown')}: {e}")
            continue

    # すべて失敗した場合はデフォルトフォントで描画
    print(f"[警告] すべてのフォントで描画失敗: {text[:20]}...")
    try:
        fallback = fonts[0] if fonts else ImageFont.load_default()
        draw.text((x, y), text, font=fallback, fill=fill)
        bbox = draw.textbbox((0, 0), text, font=fallback)
        x += bbox[2] - bbox[0]
    except Exception as e:
        print(f"[エラー] フォールバック描画も失敗: {e}")

    return x


def _parse_markdown(text):
    """
    Markdown構文をパースしてトークンのリストを返す
    各トークンは (text, style) のタプル
    style: {'bold': bool, 'italic': bool, 'code': bool, 'strikethrough': bool}
    """
    tokens = []

    # カスタム絵文字は保護する
    emoji_pattern = r'(<a?:\w+:\d+>)'

    # Markdown構文のパターン（優先順位順）
    # *** 太字斜体 ***, **太字**, *斜体*, `コード`, ~~取り消し線~~
    patterns = [
        (r'\*\*\*(.+?)\*\*\*', {'bold': True, 'italic': True}),  # ***太字斜体***
        (r'___(.+?)___', {'bold': True, 'italic': True}),  # ___太字斜体___
        (r'\*\*(.+?)\*\*', {'bold': True}),  # **太字**
        (r'__(.+?)__', {'bold': True}),  # __太字__
        (r'\*(.+?)\*', {'italic': True}),  # *斜体*
        (r'_(.+?)_', {'italic': True}),  # _斜体_
        (r'`([^`]+)`', {'code': True}),  # `コード`
        (r'~~(.+?)~~', {'strikethrough': True}),  # ~~取り消し線~~
    ]

    def parse_segment(segment):
        """再帰的にMarkdownをパースする"""
        # カスタム絵文字をチェック
        if re.match(emoji_pattern, segment):
            return [(segment, {})]

        result = []
        remaining = segment

        while remaining:
            # 最も早く出現するパターンを見つける
            earliest_match = None
            earliest_pos = len(remaining)
            matched_style = {}

            for pattern, style in patterns:
                match = re.search(pattern, remaining)
                if match and match.start() < earliest_pos:
                    earliest_match = match
                    earliest_pos = match.start()
                    matched_style = style

            if earliest_match:
                # マッチ前のテキストを追加
                if earliest_pos > 0:
                    result.append((remaining[:earliest_pos], {}))

                # マッチしたテキストを追加（スタイル付き）
                result.append((earliest_match.group(1), matched_style))

                # 残りのテキストを処理
                remaining = remaining[earliest_match.end():]
            else:
                # パターンが見つからない場合は残りをそのまま追加
                if remaining:
                    result.append((remaining, {}))
                break

        return result

    # 絵文字とテキストを分離
    parts = re.split(emoji_pattern, text)
    for part in parts:
        if part:
            tokens.extend(parse_segment(part))

    return tokens


def render_discord_like_message(author_name, content, avatar=None, role_color=None, primary_guild=None, emoji_images=None, width=1100, max_width=900, min_width=420, timestamp=None):
    """
    Discord風メッセージを画像化してBytesIOを返す。

    Parameters:
        author_name (str): ユーザー名
        content (str): メッセージ内容（複数行可）
        avatar_path (str|None): アバター画像のパス（無ければ丸い色ブロック）
        width (int): 出力画像の幅

    Returns:
        io.BytesIO: PNGデータが入ったバッファ（seekは0の状態）
    """
    # スタイル設定
    bg_color = '#36393F'  # Discordダーク
    username_color = '#FFFFFF'
    username_sub_color = '#7289DA'  # ユーザー名色（Discordっぽい）
    text_color = '#DDDDDD'

    padding = 24
    avatar_size = 56  # ユーザーの要望によりアイコンを少し大きめに（56x56）に変更
    gap = 16

    # フォント（ユーザー指定により両方 21px に設定）
    username_font = _load_font(21)
    text_font = _load_font(21)

    # テキストの折り返し（カスタム絵文字対応）
    max_text_width = width - (padding * 2 + avatar_size + gap)

    # emoji_images は token -> bytes のマッピング（例: '<:name:123>' -> b'...')
    if emoji_images is None:
        emoji_images = {}

    # role_color の正規化: '#rrggbb' 形式に統一する
    def _sanitize_hex_color(c):
        if not c:
            return None
        # 整形済み '#rrggbb' の場合
        if isinstance(c, str):
            m = re.match(r'^#?([0-9a-fA-F]{6})$', c.strip())
            if m:
                return f"#{m.group(1).lower()}"
        return None

    role_color = _sanitize_hex_color(role_color)

    # フォールバックフォントを準備
    fallback_fonts = _get_fallback_fonts(21, 'Regular')
    fallback_fonts_bold = _get_fallback_fonts(21, 'Bold')

    # 一時描画オブジェクト
    tmp_img = Image.new('RGBA', (10, 10))
    tmp_draw = ImageDraw.Draw(tmp_img)

    # Markdownをパースしてトークンに分割
    paragraphs = content.split('\n')
    lines = []  # 各行は [(text, style, is_emoji)] のリスト

    def measure_token(text, style, is_emoji=False):
        # 絵文字トークンの場合は画像の幅
        if is_emoji and text in emoji_images:
            try:
                with Image.open(io.BytesIO(emoji_images[text])) as im_e:
                    return im_e.width
            except Exception:
                return 24

        # コードや太字の場合は適切なフォントを使う
        if style.get('bold'):
            font = fallback_fonts_bold[0] if fallback_fonts_bold else text_font
        else:
            font = text_font

        bbox = tmp_draw.textbbox((0, 0), text, font=font)
        width = bbox[2] - bbox[0]

        # コードブロックの場合は背景のパディングを追加
        if style.get('code'):
            width += 8  # 左右のパディング

        return width

    emoji_token_re = re.compile(r'(<a?:\w+:\d+>)')

    for paragraph in paragraphs:
        # まずMarkdownをパース
        md_tokens = _parse_markdown(paragraph)

        # トークンをさらに絵文字で分割
        expanded_tokens = []
        for text, style in md_tokens:
            # 絵文字トークンで分割
            parts = emoji_token_re.split(text)
            for part in parts:
                if part:
                    is_emoji = part.startswith('<') and part.endswith('>')
                    expanded_tokens.append((part, style, is_emoji))

        # 行組み立て（折り返し処理）
        cur_line = []
        cur_width = 0
        for token in expanded_tokens:
            text, style, is_emoji = token
            w = measure_token(text, style, is_emoji)

            if cur_width + w > max_text_width and cur_line:
                lines.append(cur_line)
                cur_line = [token]
                cur_width = w
            else:
                cur_line.append(token)
                cur_width += w

        # 末尾の行を追加
        if cur_line:
            lines.append(cur_line)

    # 各行の実際のピクセル幅を計測して必要なテキスト幅を算出
    line_pixel_widths = []
    for line_tokens in lines:
        wsum = 0
        for text, style, is_emoji in line_tokens:
            wsum += measure_token(text, style, is_emoji)
        line_pixel_widths.append(wsum)

    text_pixel_width = max(line_pixel_widths) if line_pixel_widths else 0

    # ユーザー名やサーバータグの横幅も考慮する（サーバータグがある場合は追加幅を確保）
    try:
        tmp_for_name = Image.new('RGBA', (10, 10))
        td_name = ImageDraw.Draw(tmp_for_name)
        name_bbox = td_name.textbbox((0, 0), author_name, font=username_font)
        name_w_est = name_bbox[2] - name_bbox[0]
    except Exception:
        name_w_est = 0

    tag_extra_width = 0
    try:
        # primary_guild は dict-like を想定: {'tag': 'abcd', 'badge': bytes|path|PIL.Image, 'identity_enabled': bool}
        if primary_guild and primary_guild.get('identity_enabled', True) and primary_guild.get('tag'):
            tag_font = _load_font(15, weight='Semibold')
            td_tmp = Image.new('RGBA', (10, 10))
            td_draw = ImageDraw.Draw(td_tmp)
            t_bbox = td_draw.textbbox((0, 0), primary_guild.get('tag'), font=tag_font)
            t_w = t_bbox[2] - t_bbox[0]
            # 内側パディングとバッジの余裕を見込む
            badge_present = bool(primary_guild.get('badge'))
            badge_pad = 20 if badge_present else 0
            tag_extra_width = 8 + t_w + 8 + badge_pad
    except Exception:
        tag_extra_width = 0

    # 必要な総幅を計算（左右パディング + アバター領域 + ギャップ + テキスト幅）
    required_width = padding * 2 + avatar_size + gap + int(text_pixel_width)
    # ユーザー名行（名前＋サーバータグ）による幅も考慮
    try:
        required_width = max(required_width, padding * 2 + avatar_size + gap + int(name_w_est) + 8 + int(tag_extra_width))
    except Exception:
        pass
    # 最大・最小幅で制限
    final_width = max(min(required_width, max_width), min_width)
    # 最終的な幅を width 変数として使用
    width = int(final_width)

    # 行高さ計算（Pillow のバージョン差に対応）
    # 一時的な描画オブジェクトでフォントメトリクスを取得
    try:
        # 多くの環境で利用可能なメトリクス取得
        ascent, descent = text_font.getmetrics()
        line_height = ascent + descent + 8
    except Exception:
        # フォールバックでテキストのバウンディングボックスを使う
        bbox = tmp_draw.textbbox((0, 0), 'A', font=text_font)
        line_height = (bbox[3] - bbox[1]) + 8

    content_height = line_height * max(1, len(lines))

    # ユーザー名行の高さを計測して全体高さを決定
    try:
        name_bbox = tmp_draw.textbbox((0, 0), author_name, font=username_font)
        name_height = name_bbox[3] - name_bbox[1]
    except Exception:
        name_height = username_font.size if hasattr(username_font, 'size') else 36

    height = padding * 2 + max(avatar_size, name_height + 8 + content_height)

    # キャンバス作成
    im = Image.new('RGBA', (width, height), bg_color)
    draw = ImageDraw.Draw(im)

    # アバター
    avatar_x = padding
    avatar_y = padding
    if avatar:
        try:
            # avatar can be bytes, BytesIO, or a filesystem path
            if isinstance(avatar, (bytes, bytearray)):
                av = Image.open(io.BytesIO(avatar)).convert('RGBA')
            elif isinstance(avatar, io.BytesIO):
                avatar.seek(0)
                av = Image.open(avatar).convert('RGBA')
            elif isinstance(avatar, str) and os.path.exists(avatar):
                av = Image.open(avatar).convert('RGBA')
            else:
                raise ValueError('unsupported avatar type')

            # リサイズ（高品質）
            av = av.resize((avatar_size, avatar_size), Image.LANCZOS)
            # 円形マスクを高解像度で作ってからリサンプルすることでアンチエイリアスを改善
            try:
                hr = 4  # high-res multiplier
                mask_hr = Image.new('L', (avatar_size * hr, avatar_size * hr), 0)
                mask_draw_hr = ImageDraw.Draw(mask_hr)
                mask_draw_hr.ellipse((0, 0, avatar_size * hr, avatar_size * hr), fill=255)
                mask = mask_hr.resize((avatar_size, avatar_size), Image.LANCZOS)
            except Exception:
                # フォールバック
                mask = Image.new('L', (avatar_size, avatar_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)

            im.paste(av, (avatar_x, avatar_y), mask)
        except Exception:
            # 失敗したら単色の円を描画
            draw.ellipse((avatar_x, avatar_y, avatar_x+avatar_size, avatar_y+avatar_size), fill='#99AAB5')
    else:
        # 色付きの円（ランダム性は避けるため固定色）
        draw.ellipse((avatar_x, avatar_y, avatar_x+avatar_size, avatar_y+avatar_size), fill='#99AAB5')

    # ユーザー名
    name_x = avatar_x + avatar_size + gap
    name_y = avatar_y
    # role_color が渡されていればユーザー名の色として使用
    username_fill = username_color
    try:
        if role_color:
            # role_color は '#rrggbb' 形式の文字列に正規化済み
            username_fill = role_color
    except Exception:
        username_fill = username_color

    # ユーザー名をフォールバック対応で描画
    username_fallback_fonts = _get_fallback_fonts(21, 'Regular')
    _draw_text_with_fallback(draw, (name_x, name_y), author_name, username_fallback_fonts, username_fill)

    # --- サーバータグ描画 (primary_guild) ---
    tag_drawn = False
    tag_total_w = 0
    try:
        if primary_guild and primary_guild.get('identity_enabled', True) and primary_guild.get('tag'):
            tag_text = primary_guild.get('tag')
            tag_font = _load_font(15, weight='Semibold')
            tmp_t = Image.new('RGBA', (10, 10))
            td_t = ImageDraw.Draw(tmp_t)
            t_bbox = td_t.textbbox((0, 0), tag_text, font=tag_font)
            t_w = t_bbox[2] - t_bbox[0]

            pad_x = 8
            pad_y = 4
            badge_img = primary_guild.get('badge')
            badge_w = 0
            badge_h = 0
            bi = None
            if badge_img:
                try:
                    if isinstance(badge_img, (bytes, bytearray)):
                        bi = Image.open(io.BytesIO(badge_img)).convert('RGBA')
                    elif isinstance(badge_img, Image.Image):
                        bi = badge_img
                    elif isinstance(badge_img, str) and os.path.exists(badge_img):
                        bi = Image.open(badge_img).convert('RGBA')
                    else:
                        bi = None
                except Exception:
                    bi = None

            if bi:
                badge_h = max(12, name_height - 4)
                badge_w = int(bi.width * (badge_h / bi.height)) if bi.height else badge_h

            tag_h = name_height
            tag_total_w = pad_x * 2 + t_w + (badge_w + 4 if badge_w else 0)

            # 名前の右側に描画
            try:
                name_bbox_local = tmp_draw.textbbox((0, 0), author_name, font=username_font)
                name_w_local = name_bbox_local[2] - name_bbox_local[0]
            except Exception:
                name_w_local = username_font.size if hasattr(username_font, 'size') else 36

            rect_x0 = name_x + name_w_local + 8
            rect_y0 = name_y + (name_height - tag_h) // 2
            rect_x1 = rect_x0 + tag_total_w
            rect_y1 = rect_y0 + tag_h

            # 角丸矩形（Pillow のバージョンが古い場合は矩形）
            try:
                draw.rounded_rectangle((rect_x0, rect_y0, rect_x1, rect_y1), radius=4, fill='#2F3136', outline='#202225')
            except Exception:
                draw.rectangle((rect_x0, rect_y0, rect_x1, rect_y1), fill='#2F3136')

            cur_x = rect_x0 + pad_x
            if bi and badge_w:
                try:
                    bi_resized = bi.resize((badge_w, badge_h), Image.LANCZOS)
                    badge_y = rect_y0 + (tag_h - badge_h) // 2
                    im.paste(bi_resized, (int(cur_x), int(badge_y)), bi_resized)
                    cur_x += badge_w + 4
                except Exception:
                    pass

            text_y = rect_y0 + (tag_h - (t_bbox[3] - t_bbox[1])) // 2
            # タグテキストをフォールバック対応で描画
            tag_fallback_fonts = _get_fallback_fonts(15, 'Semibold')
            _draw_text_with_fallback(draw, (cur_x, text_y), tag_text, tag_fallback_fonts, '#FFFFFF')
            tag_drawn = True
    except Exception:
        # タグ描画に失敗しても無視
        tag_drawn = False
        tag_total_w = 0

    # タイムスタンプが渡されていればユーザー名の右側に小さめのフォントで描画
    if timestamp:
        try:
            # timestamp が datetime オブジェクトの場合は文字列化
            import datetime as _dt
            if isinstance(timestamp, _dt.datetime):
                # ローカルタイムに変換して表示（HH:MM の24時間形式）
                try:
                    ts_local = timestamp.astimezone()
                except Exception:
                    ts_local = timestamp
                ts_str = ts_local.strftime('%H:%M')
            else:
                ts_str = str(timestamp)

            time_font = _load_font(16)
            # ユーザー名の幅を測って右側に余白を置いて描画
            try:
                tmp = Image.new('RGBA', (10, 10))
                td = ImageDraw.Draw(tmp)
                name_bbox = td.textbbox((0, 0), author_name, font=username_font)
                name_w = name_bbox[2] - name_bbox[0]
            except Exception:
                name_w = username_font.size if hasattr(username_font, 'size') else 36

            # サーバータグが描画されていればそれ分だけ右にオフセット
            # 時刻の X 座標（名前の右側に余白を置く）
            time_x = name_x + name_w + 8
            try:
                if tag_drawn and tag_total_w:
                    time_x += int(tag_total_w) + 8
            except Exception:
                pass

            # 時刻は 16px フォントで、20px の領域の中央に置く
            try:
                time_box_h = 20
                tmp_time = Image.new('RGBA', (10, 10))
                td_time = ImageDraw.Draw(tmp_time)
                t_bbox = td_time.textbbox((0, 0), ts_str, font=time_font)
                t_h = t_bbox[3] - t_bbox[1]

                # 名前行の中央 Y を基準に時刻を中央揃えする（より正確な中央寄せ）
                center_y = name_y + name_height / 2
                time_y = int(center_y - (t_h / 2))
                # 安全のため、time_y が name_y を下回ったり name_y+name_height を超えないように制限
                if time_y < name_y:
                    time_y = name_y
                if time_y + t_h > name_y + name_height:
                    # はみ出す場合は上に寄せる
                    time_y = int(name_y + name_height - t_h)
            except Exception:
                # フォールバック（既存の簡易配置）
                time_y = name_y + (username_font.size - 12 if hasattr(username_font, 'size') else 4)

            # 時刻は灰色で描画
            time_fill = '#99AAB5'
            draw.text((time_x, time_y), ts_str, font=time_font, fill=time_fill)
        except Exception:
            # タイムスタンプ描画は失敗しても無視
            pass

    # メッセージテキスト（トークンごとに描画、Markdown対応）
    text_x = name_x
    text_y = name_y + name_height + 8
    for i, line_tokens in enumerate(lines):
        x = text_x
        y = text_y + i * line_height

        for text, style, is_emoji in line_tokens:
            if is_emoji and text in emoji_images:
                # 絵文字画像を描画
                try:
                    em_img = Image.open(io.BytesIO(emoji_images[text])).convert('RGBA')
                    em_h = line_height - 4
                    em_w = int(em_img.width * (em_h / em_img.height)) if em_img.height else em_h
                    em_img = em_img.resize((em_w, em_h), Image.LANCZOS)
                    im.paste(em_img, (int(x), int(y)), em_img)
                    x += em_w + 2
                except Exception:
                    # フォールバックでテキスト描画
                    x = _draw_text_with_fallback(draw, (x, y), text, fallback_fonts, text_color)
            else:
                # スタイルに応じてテキストを描画
                # フォント選択
                if style.get('bold'):
                    fonts = fallback_fonts_bold
                else:
                    fonts = fallback_fonts

                # 色選択
                if style.get('code'):
                    fill_color = '#FFFFFF'  # コードは白
                else:
                    fill_color = text_color

                # コードの背景を描画
                if style.get('code'):
                    # 背景の矩形を描画
                    bbox = tmp_draw.textbbox((0, 0), text, font=fonts[0])
                    text_w = bbox[2] - bbox[0]
                    text_h = bbox[3] - bbox[1]
                    bg_x0 = x - 2
                    bg_y0 = y - 2
                    bg_x1 = x + text_w + 2
                    bg_y1 = y + text_h + 2
                    try:
                        draw.rounded_rectangle((bg_x0, bg_y0, bg_x1, bg_y1), radius=3, fill='#202225')
                    except Exception:
                        draw.rectangle((bg_x0, bg_y0, bg_x1, bg_y1), fill='#202225')

                # テキスト描画（フォールバック対応）
                start_x = x
                x = _draw_text_with_fallback(draw, (x, y), text, fonts, fill_color)

                # 取り消し線を描画
                if style.get('strikethrough'):
                    bbox = tmp_draw.textbbox((0, 0), text, font=fonts[0])
                    text_h = bbox[3] - bbox[1]
                    strike_y = y + text_h // 2
                    draw.line((start_x, strike_y, x, strike_y), fill=fill_color, width=2)

    # 余白を持たせた保存
    # 最終的に透明部分が残らないよう、背景色で合成して RGB にする
    try:
        bg = Image.new('RGB', im.size, bg_color)
        if im.mode == 'RGBA':
            bg.paste(im, mask=im.split()[3])  # alpha チャネルをマスクとして合成
        else:
            bg.paste(im)
        out = io.BytesIO()
        bg.save(out, format='PNG')
        out.seek(0)
        return out
    except Exception:
        # フォールバックで元のイメージを保存
        out = io.BytesIO()
        im.save(out, format='PNG')
        out.seek(0)
        return out


def render_messages_stack(message_items, width=None, max_width=900, bg_color='#36393F'):
    """
    複数メッセージを縦に積んだ画像を返す。

    message_items: list of dict with keys: author_name, content, avatar (bytes|path|None), role_color (hex|None), emoji_images (dict token->bytes)
    width: 固定幅を指定（None なら内部で算出）
    """
    # 各メッセージを個別にレンダリングして PIL.Image に変換
    imgs = []
    for item in message_items:
        buf = render_discord_like_message(
            item.get('author_name', ''),
            item.get('content', ''),
            avatar=item.get('avatar'),
            role_color=item.get('role_color'),
            primary_guild=item.get('primary_guild'),
            emoji_images=item.get('emoji_images', {}),
            timestamp=item.get('timestamp', None),
            width=width or max_width,
            max_width=max_width
        )
        try:
            im = Image.open(buf).convert('RGB')
            imgs.append(im)
        except Exception:
            # バッファから開けない場合はスキップ
            continue

    if not imgs:
        # 空の場合は空画像を返す
        out = io.BytesIO()
        Image.new('RGB', (min(420, max_width), 80), bg_color).save(out, format='PNG')
        out.seek(0)
        return out

    # 幅は max of widths but capped by max_width
    total_width = min(max((im.width for im in imgs)), max_width)
    # 合成高さを計算
    total_height = sum(im.height for im in imgs)

    # 新しい画像を作る
    dst = Image.new('RGB', (total_width, total_height), bg_color)
    y = 0
    for im in imgs:
        # 横幅が合わない場合は左右に余白を入れて中央に寄せる
        if im.width != total_width:
            x = (total_width - im.width) // 2
        else:
            x = 0
        dst.paste(im, (x, y))
        y += im.height

    out = io.BytesIO()
    dst.save(out, format='PNG')
    out.seek(0)
    return out
