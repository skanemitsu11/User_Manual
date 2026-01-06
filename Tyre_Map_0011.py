import pandas as pd
import cv2
import numpy as np
import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageDraw, ImageFont
import math

# ==========================================
# 設定エリア
# ==========================================
# キャンバス設定
CANVAS_W = 1280
CANVAS_H = 720
BACKGROUND_COLOR = (242, 242, 242) # 背景色 (RGB) ここを変更すると反映されます

# 画像配置エリア（余白調整）
IMAGE_SCALE_RATIO = 0.70 
HEADER_MARGIN = 80 

# 引き出し線の角度設定
LINE_ANGLE_DEG = 5.5  # 真上から右に振る角度

# フォント設定 (Windows標準のYu Gothicを想定)
FONT_PATH_BOLD = "C:/Windows/Fonts/YuGothB.ttc"
FONT_PATH_REGULAR = "C:/Windows/Fonts/YuGothM.ttc"

# フォントサイズ
SIZE_LOC = 24     # 場所
SIZE_VAL = 20     # 数値
SIZE_NOTE = 22    # 注釈

# テキストラベル変換マップ
POS_LABEL_MAP = {
    "FL": "左前 / Front Left",
    "FR": "右前 / Front Right",
    "RL": "左後 / Rear Left",
    "RR": "右後 / Rear Right"
}

# 色設定 (RGB)
COLOR_TEXT_BLACK = (0, 0, 0)      # 場所名や注釈の文字色
COLOR_LINE_BLACK = (0, 0, 0)      # 場所名の下線色
COLOR_VAL_POINT  = (255, 0, 0)    # 赤点の色
# ※前回は青でしたが、今回は「黒色で横線を引く」などの文脈があったため、視認性重視で黒に近い色、あるいは前回の濃い青(0,0,200)を維持します。
COLOR_VAL_LINE   = (0, 200, 255)  # 引き出し線の色 (水色/青系)
COLOR_VAL_TEXT   = (0, 0, 0)      # 数値の文字色

def select_inputs():
    root = tk.Tk()
    root.withdraw()
    print("ポップアップで画像ディレクトリを選択してください...")
    img_dir = filedialog.askdirectory(title="【1/2】画像ディレクトリを選択")
    if not img_dir: return None, None
    print(f"画像ディレクトリ: {img_dir}")
    print("ポップアップでCSVファイルを選択してください...")
    csv_path = filedialog.askopenfilename(title="【2/2】CSVファイルを選択", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
    if not csv_path: return None, None
    print(f"CSVファイル: {csv_path}")
    return img_dir, csv_path

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except:
        return ImageFont.load_default()

def process_one_entry(target_filename, row_data, img_dir, output_dir, fonts):
    base_stem = os.path.splitext(target_filename)[0]
    output_filename = f"Image_0011_{base_stem}.jpg"
    save_path = os.path.join(output_dir, output_filename)

    # 1. OpenCVでベース作成
    # 設定されたBACKGROUND_COLOR (RGB) を OpenCV用 (BGR) に変換して適用
    bg_bgr = BACKGROUND_COLOR[::-1]

    # 【修正】np.fullでは色が正しく反映されない場合があるため、
    # ゼロ埋めした配列に対して色を代入する確実な方法に変更しました。
    canvas_cv = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)
    canvas_cv[:] = bg_bgr
    
    half_w = CANVAS_W // 2
    half_h = CANVAS_H // 2
    
    areas = {
        "FL": {"rect": (0, 0, half_w, half_h)},
        "FR": {"rect": (half_w, 0, half_w, half_h)},
        "RL": {"rect": (0, half_h, half_w, half_h)},
        "RR": {"rect": (half_w, half_h, half_w, half_h)}
    }

    placed_images_info = {}

    # --- 画像配置 ---
    for pos in ["FL", "FR", "RL", "RR"]:
        img_path = os.path.join(img_dir, f"{base_stem}_{pos}_cropped.jpg")
        
        if os.path.exists(img_path):
            img = cv2.imread(img_path)
            if img is None: 
                # 画像読み込み失敗時はグレーの矩形を表示
                img = np.full((400, 600, 3), 200, dtype=np.uint8)
        else:
            # 画像が存在しない場合は少し明るいグレーの矩形を表示
            img = np.full((400, 600, 3), 240, dtype=np.uint8)
            
        org_h, org_w = img.shape[:2]
        ax, ay, aw, ah = areas[pos]["rect"]
        
        target_w = aw * IMAGE_SCALE_RATIO
        target_h = ah * IMAGE_SCALE_RATIO
        scale = min(target_w / org_w, target_h / org_h)
        new_w = int(org_w * scale)
        new_h = int(org_h * scale)
        
        resized_img = cv2.resize(img, (new_w, new_h))
        
        available_h = ah - HEADER_MARGIN
        offset_x = ax + (aw - new_w) // 2
        offset_y = ay + HEADER_MARGIN + (available_h - new_h) // 2
        
        canvas_cv[offset_y:offset_y+new_h, offset_x:offset_x+new_w] = resized_img
        
        placed_images_info[pos] = {
            "scale": scale,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "img_w": new_w,
            "img_h": new_h,
            "ax": ax, "ay": ay, "aw": aw, "ah": ah,
            "top_y": offset_y 
        }

    # --- PIL描画 ---
    canvas_cv = cv2.cvtColor(canvas_cv, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(canvas_cv)
    draw = ImageDraw.Draw(img_pil)
    
    font_loc = fonts["loc"]
    font_val = fonts["val"]
    font_note = fonts["note"]

    for pos in ["FL", "FR", "RL", "RR"]:
        info = placed_images_info[pos]
        
        # 場所名
        loc_text = POS_LABEL_MAP[pos]
        bbox = draw.textbbox((0, 0), loc_text, font=font_loc)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        loc_x = info["ax"] + 20
        loc_y = info["ay"] + 20
        
        draw.text((loc_x, loc_y), loc_text, font=font_loc, fill=COLOR_TEXT_BLACK)
        line_y = loc_y + text_h + 4
        draw.line([(loc_x - 5, line_y), (loc_x + text_w +5 , line_y)], fill=COLOR_LINE_BLACK, width=3)

        # 数値データ
        img_top_y = info["top_y"]
        
        # 角度計算用
        tan_angle = math.tan(math.radians(LINE_ANGLE_DEG))

        for i in range(1, 8):
            col_val, col_x, col_y = str(i), f"{i}_x", f"{i}_y"
            
            if (pos, col_x) not in row_data.index: continue
            val = row_data[(pos, col_val)]
            x = row_data[(pos, col_x)]
            y = row_data[(pos, col_y)]
            
            if pd.isna(x) or pd.isna(y) or pd.isna(val): continue

            # --- 【追加】座標が(0,0)の場合はスキップ ---
            try:
                if float(x) == 0 and float(y) == 0: continue
            except: pass
            # ----------------------------------------

            try:
                if float(val) == 0: continue
            except: pass

            # ターゲット座標
            target_px = int(x * info["scale"] + info["offset_x"])
            target_py = int(y * info["scale"] + info["offset_y"])

            val_str = f"{float(val):.1f}"
            
            # --- High/Low の決定 (交互) ---
            is_high = (i % 2 != 0)
            
            # Y座標決定 (下線の高さ)
            if is_high:
                underline_y = img_top_y - 50
            else:
                underline_y = img_top_y - 20
            
            # --- X座標の計算 (角度固定) ---
            # target_py から underline_y までの高さ
            height_diff = target_py - underline_y
            
            # 真上から右へ角度がついているので、高さに応じてXが右へずれる
            # dx = height * tan(theta)
            dx = height_diff * tan_angle
            
            # 下線の左端X座標
            line_start_x = target_px + dx
            
            # テキスト描画位置
            bbox = draw.textbbox((0, 0), val_str, font=font_val)
            t_w = bbox[2] - bbox[0]
            t_h = bbox[3] - bbox[1]
            
            text_x = line_start_x
            text_y = underline_y - t_h - 2 - 3
            
            line_end_x = text_x + t_w
            
            # 描画
            r = 3
            draw.ellipse(
                (target_px - r, target_py - r, target_px + r, target_py + r),
                fill=COLOR_VAL_POINT, outline=None
            )
            
            draw.text((text_x, text_y), val_str, font=font_val, fill=COLOR_VAL_TEXT)
            
            draw.line([(line_start_x, underline_y), (line_end_x, underline_y)], 
                      fill=COLOR_VAL_LINE, width=3)
            
            # 点から下線左端へ線を引く (角度5.5degになっているはず)
            draw.line([(target_px, target_py), (line_start_x, underline_y)], 
                      fill=COLOR_VAL_LINE, width=3)

    # 注釈
    note_text = "※数値は参考値であり、結果の正確性を保証するものではありません"
    bbox = draw.textbbox((0, 0), note_text, font=font_note)
    note_w = bbox[2] - bbox[0]
    note_h = bbox[3] - bbox[1]
    
    note_x = CANVAS_W - note_w - 20
    note_y = CANVAS_H - note_h - 20
    draw.text((note_x, note_y), note_text, font=font_note, fill=COLOR_TEXT_BLACK)

    img_pil.save(save_path, quality=95)
    print(f"Saved: {output_filename}")

def main():
    img_dir, csv_path = select_inputs()
    if img_dir is None or csv_path is None: return

    print("Loading fonts...")
    fonts = {
        "loc": load_font(FONT_PATH_BOLD, SIZE_LOC),
        "val": load_font(FONT_PATH_BOLD, SIZE_VAL),
        "note": load_font(FONT_PATH_REGULAR, SIZE_NOTE)
    }

    print("Loading CSV...")
    try:
        df = pd.read_csv(csv_path, header=[0, 1])
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    print("Processing start...")
    file_col_key = df.columns[0]
    
    count = 0
    for index, row in df.iterrows():
        target_filename = row[file_col_key]
        
        if pd.isna(target_filename) or str(target_filename).strip() == "":
            print(f"Empty cell at row {index + 3}. Process finished.")
            break
            
        print(f"[{count+1}] Processing: {target_filename}")
        try:
            process_one_entry(str(target_filename), row, img_dir, img_dir, fonts)
            count += 1
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            
    print(f"\nAll Done. Generated {count} images.")

if __name__ == "__main__":
    main()