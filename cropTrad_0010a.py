import cv2
import numpy as np
import os

def crop_with_width_ratio_logic(image_path, output_dir="output_ratio_crops"):
    # 画像の読み込み
    img_src = cv2.imread(image_path)
    if img_src is None:
        print("画像が見つかりません。")
        return

    # 出力フォルダ作成
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 固定パネル座標定義
    panel_coords = {
        "FrontLeft":  ((14, 14),   (472, 354)),
        "FrontRight": ((489, 14),  (946, 354)),
        "RearLeft":   ((14, 372),  (472, 713)),
        "RearRight":  ((489, 372), (946, 712))
    }
    
    # ロジック定数
    RATIO_DIVISOR = 3.82

    print(f"処理を開始します: {output_dir} へ保存中...")
    print(f"適用ロジック: New_Y = b + (Width / {RATIO_DIVISOR})")
    print("-" * 60)

    for pos_name, ((p_x1, p_y1), (p_x2, p_y2)) in panel_coords.items():
        # 1. パネル切り出し
        panel_img = img_src[p_y1:p_y2, p_x1:p_x2]
        
        # 2. 二極処理（二値化）
        gray = cv2.cvtColor(panel_img, cv2.COLOR_BGR2GRAY)
        # 背景(白)→黒、 コンテンツ(暗い色)→白
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        # 3. 最大の輪郭（白い四角）を見つける
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if contours:
            # 最大面積の輪郭を取得
            max_contour = max(contours, key=cv2.contourArea)
            rx, ry, rw, rh = cv2.boundingRect(max_contour)

            # ---------------------------------------------------------
            # ここでご指定のロジックを適用します
            # ---------------------------------------------------------
            
            # ① 元の矩形座標 (a, b) (c, d) を取得
            # a = global_x1, b = global_y1
            # c = global_x2, d = global_y2
            
            a = p_x1 + rx
            b = p_y1 + ry
            c = a + rw
            d = b + rh
            
            # ② 横幅 (c - a) を計算
            width = c - a  # これは rw と同じです
            
            # ③ 高さ方向のオフセット量を計算: (c-a) / 3.82
            offset_y = width / RATIO_DIVISOR
            
            # ④ クロップする新しいY座標 (a, b + offset)
            new_y_start = int(b + offset_y)
            
            # 安全策: 新しいYが下端(d)を超えないようにチェック
            if new_y_start >= d:
                print(f"[{pos_name}] Warning: 計算された開始位置が範囲外です。スキップします。")
                continue

            # ---------------------------------------------------------
            # 画像の切り出し実行
            # img[ y_start : y_end, x_start : x_end ]
            # ---------------------------------------------------------
            final_crop = img_src[new_y_start:d, a:c]

            # 保存
            filename = f"{pos_name}_RatioCrop.jpg"
            save_path = os.path.join(output_dir, filename)
            cv2.imwrite(save_path, final_crop)
            
            print(f"[{pos_name}]")
            print(f"  Base Rect : (x={a}, y={b}) - (x={c}, y={d})")
            print(f"  Width     : {width}")
            print(f"  Offset    : {offset_y:.2f} (pixel)")
            print(f"  New Crop  : y={new_y_start} から y={d} まで")
            print(f"  Saved     : {filename}")
            
        else:
            print(f"[{pos_name}] Warning: コンテンツが見つかりませんでした。")
        
        print("-" * 20)

    print("全処理が完了しました。")

# --- 実行 ---
target_image = "20251217154616_B_1003554301_TR.jpg"
crop_with_width_ratio_logic(target_image)