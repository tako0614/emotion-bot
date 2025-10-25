"""
デフォルトのキャラクター画像（タコっぽいキャラクター）を作成するスクリプト
"""
from PIL import Image, ImageDraw
import os


def create_tako_character():
    """スクリーンショットのようなタコキャラクターを作成"""
    # キャンバスサイズ
    width = 300
    height = 300

    # 透明背景のキャンバス
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 体の色（赤）
    body_color = (255, 85, 85)  # 明るい赤
    eye_color = (0, 0, 0)
    white_color = (255, 255, 255)

    # 体（正方形っぽい丸）
    body_x = 75
    body_y = 40
    body_width = 150
    body_height = 130
    draw.rounded_rectangle(
        [(body_x, body_y), (body_x + body_width, body_y + body_height)],
        radius=20,
        fill=body_color
    )

    # 目（斜めの線 ">" "<" のような感じ）
    # 左目
    left_eye_points = [
        (115, 90),
        (125, 95),
        (115, 100)
    ]
    draw.line(left_eye_points[0] + left_eye_points[1], fill=eye_color, width=4)
    draw.line(left_eye_points[1] + left_eye_points[2], fill=eye_color, width=4)

    # 右目
    right_eye_points = [
        (185, 90),
        (175, 95),
        (185, 100)
    ]
    draw.line(right_eye_points[0] + right_eye_points[1], fill=eye_color, width=4)
    draw.line(right_eye_points[1] + right_eye_points[2], fill=eye_color, width=4)

    # 頬紅（小さい楕円）
    # 左頬
    draw.ellipse([(95, 110), (110, 120)], fill=(255, 150, 150))
    # 右頬
    draw.ellipse([(190, 110), (205, 120)], fill=(255, 150, 150))

    # 口（小さい "~" のような線）
    mouth_y = 130
    draw.arc([(135, mouth_y), (165, mouth_y + 15)], 0, 180, fill=eye_color, width=3)

    # 足（複数の四角い足）
    leg_width = 18
    leg_height = 60
    leg_spacing = 5
    leg_start_y = body_y + body_height - 10

    # 足の数: 5本
    num_legs = 5
    total_leg_width = num_legs * leg_width + (num_legs - 1) * leg_spacing
    leg_start_x = body_x + (body_width - total_leg_width) // 2

    for i in range(num_legs):
        leg_x = leg_start_x + i * (leg_width + leg_spacing)
        draw.rectangle(
            [(leg_x, leg_start_y), (leg_x + leg_width, leg_start_y + leg_height)],
            fill=body_color
        )

        # 足の先端を少し丸く
        draw.ellipse(
            [(leg_x - 2, leg_start_y + leg_height - 5),
             (leg_x + leg_width + 2, leg_start_y + leg_height + 5)],
            fill=body_color
        )

    # 保存
    repo_dir = os.path.dirname(__file__)
    output_path = os.path.join(repo_dir, 'character.png')
    img.save(output_path)
    print(f"キャラクター画像を作成しました: {output_path}")


if __name__ == '__main__':
    create_tako_character()
