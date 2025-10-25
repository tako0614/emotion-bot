from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import textwrap
import os
import re


def _load_font(size):
    # 優先してリポジトリ内のフォントを使用（gg-sans-2 の Regular を優先）
    repo_dir = os.path.dirname(__file__)
    gg_sans_path = os.path.join(repo_dir, 'gg-sans-2', 'gg sans Regular.ttf')
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

    # まず gg-sans を試す
    if os.path.exists(gg_sans_path):
        f = _test_font(gg_sans_path)
        if f:
            print(f"使用フォント: {gg_sans_path}")
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


def render_discord_like_message(author_name, content, avatar=None, role_color=None, emoji_images=None, width=1100, max_width=900, min_width=420, timestamp=None):
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

    # トークン化：カスタム絵文字トークンを分割して扱う
    emoji_token_re = re.compile(r'(<a?:\w+:\d+>)')

    paragraphs = content.split('\n')
    lines = []  # 各行は文字列またはトークンのリストにする
    # 一時描画オブジェクト
    tmp_img = Image.new('RGBA', (10, 10))
    tmp_draw = ImageDraw.Draw(tmp_img)

    def measure_token(tok):
        # 絵文字トークンの場合は画像の幅、そうでなければテキスト幅
        if tok.startswith('<') and tok.endswith('>') and tok in emoji_images:
            try:
                with Image.open(io.BytesIO(emoji_images[tok])) as im_e:
                    w = im_e.width
            except Exception:
                w = username_font.size
            return w
        else:
            bbox = tmp_draw.textbbox((0, 0), tok, font=text_font)
            return bbox[2] - bbox[0]

    for paragraph in paragraphs:
        # 分割してトークン配列を作る
        parts = [p for p in emoji_token_re.split(paragraph) if p != '']
        # 行組み立て
        cur_line = []
        cur_width = 0
        for part in parts:
            w = measure_token(part)
            # 単語内分割は考慮せず、パート単位で折り返す
            if cur_width + w > max_text_width and cur_line:
                lines.append(cur_line)
                cur_line = [part]
                cur_width = w
            else:
                cur_line.append(part)
                cur_width += w
        # 末尾の行を追加
        if cur_line:
            lines.append(cur_line)

    # 各行の実際のピクセル幅を計測して必要なテキスト幅を算出
    line_pixel_widths = []
    for parts in lines:
        wsum = 0
        for part in parts:
            wsum += measure_token(part)
        line_pixel_widths.append(wsum)

    text_pixel_width = max(line_pixel_widths) if line_pixel_widths else 0

    # 必要な総幅を計算（左右パディング + アバター領域 + ギャップ + テキスト幅）
    required_width = padding * 2 + avatar_size + gap + int(text_pixel_width)
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

    draw.text((name_x, name_y), author_name, font=username_font, fill=username_fill)

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

            time_font = _load_font(14)
            # ユーザー名の幅を測って右側に余白を置いて描画
            try:
                tmp = Image.new('RGBA', (10, 10))
                td = ImageDraw.Draw(tmp)
                name_bbox = td.textbbox((0, 0), author_name, font=username_font)
                name_w = name_bbox[2] - name_bbox[0]
            except Exception:
                name_w = username_font.size if hasattr(username_font, 'size') else 36

            time_x = name_x + name_w + 8
            time_y = name_y + (username_font.size - 12 if hasattr(username_font, 'size') else 4)
            # 時刻は灰色で描画
            time_fill = '#99AAB5'
            draw.text((time_x, time_y), ts_str, font=time_font, fill=time_fill)
        except Exception:
            # タイムスタンプ描画は失敗しても無視
            pass

    # メッセージテキスト（トークンごとに描画。絵文字トークンは画像を埋め込む）
    text_x = name_x
    text_y = name_y + name_height + 8
    for i, line_parts in enumerate(lines):
        x = text_x
        y = text_y + i * line_height
        for part in line_parts:
            if part.startswith('<') and part.endswith('>') and part in emoji_images:
                # 絵文字画像を描画（フォントサイズに合わせて高さを調整）
                try:
                    em_img = Image.open(io.BytesIO(emoji_images[part])).convert('RGBA')
                    # 高さを line_height に合わせる
                    em_h = line_height - 4
                    em_w = int(em_img.width * (em_h / em_img.height)) if em_img.height else em_h
                    em_img = em_img.resize((em_w, em_h), Image.LANCZOS)
                    im.paste(em_img, (int(x), int(y)), em_img)
                    x += em_w + 2
                except Exception:
                    # フォールバックで名前を描画
                    draw.text((x, y), part, font=text_font, fill=text_color)
                    w = tmp_draw.textbbox((0, 0), part, font=text_font)[2]
                    x += w
            else:
                draw.text((x, y), part, font=text_font, fill=text_color)
                w = tmp_draw.textbbox((0, 0), part, font=text_font)[2]
                x += w

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
