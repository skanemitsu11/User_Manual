import cv2
import numpy as np
import pandas as pd
import glob
import os
import argparse
import sys
import tkinter as tk
from tkinter import filedialog

def find_red_dots(image_path):
    """
    画像から赤色の点を検出し、その中心座標（x, y）のリストを返します。
    """
    # 画像の読み込み
    img = cv2.imread(image_path)
    
    if img is None:
        print(f"エラー: 画像ファイル '{image_path}' が見つかりませんでした。")
        return []

    # BGRからHSV色空間に変換 (色抽出をしやすくするため)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # 赤色のHSV範囲を定義
    # 範囲1: 色相 0~10 (明度・彩度は広めに設定)
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    
    # 範囲2: 色相 170~180
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])

    # 2つの範囲でマスクを作成し、結合
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = mask1 + mask2

    # ノイズ除去 (モルフォロジー変換: オープニング処理)
    kernel = np.ones((3,3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # 輪郭（赤点の領域）を検出
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    coordinates = []
    
    # 確認用画像作成（必要に応じてコメントアウト）
    output_img = img.copy()

    for i, contour in enumerate(contours):
        # 面積によるフィルタリング
        area = cv2.contourArea(contour)
        if area < 5:
            continue

        # 重心を求める
        M = cv2.moments(contour)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            
            coordinates.append((cX, cY))
            
            # 確認用描画
            cv2.circle(output_img, (cX, cY), 5, (0, 255, 0), 2)
            cv2.putText(output_img, f"{cX},{cY}", (cX - 20, cY - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # 確認用画像の保存（デバッグ用）
    # result_filename = 'result_' + os.path.basename(image_path)
    # cv2.imwrite(result_filename, output_img)
    
    return coordinates

def update_csv_with_coords(image_dir, csv_path):
    """
    指定ディレクトリの画像を処理し、結果をCSVに書き込みます。
    """
    print(f"CSVファイルを読み込み中: {csv_path}")
    try:
        # ヘッダーが2行あるため header=[0, 1] を指定
        # index_col=0 で1列目(file_name)をインデックスとして扱う
        df = pd.read_csv(csv_path, header=[0, 1], index_col=0)
    except Exception as e:
        print(f"CSV読み込みエラー: {e}")
        return

    # 指定ディレクトリ内のjpgファイルを取得
    image_files = glob.glob(os.path.join(image_dir, "*.jpg"))
    print(f"{len(image_files)} 個の画像ファイルが見つかりました。処理を開始します...")

    for img_path in image_files:
        file_name = os.path.basename(img_path)
        
        # ファイル名からID（先頭30文字）を抽出
        # 例: 20251209165425_A_1003344239_TR_FL_cropped.jpg -> 20251209165425_A_1003344239_TR
        if len(file_name) < 30:
            continue
            
        file_id = file_name[:30]
        
        # CSV内にこのIDが存在するか確認
        # CSVのキーが "ID" なのか "ID.jpg" なのか両方チェックする
        match_key = None
        if file_id in df.index:
            match_key = file_id
        elif f"{file_id}.jpg" in df.index:
            match_key = f"{file_id}.jpg"
        
        if match_key is None:
            print(f"スキップ: CSVにIDが見つかりません ({file_id})")
            continue

        # ポジション (FL, FR, RL, RR) の特定
        pos = None
        for p in ["FL", "FR", "RL", "RR"]:
            if f"_{p}_" in file_name:
                pos = p
                break
        
        if pos is None:
            print(f"スキップ: ポジション不明 ({file_name})")
            continue

        # 赤点座標を取得
        coords = find_red_dots(img_path)
        
        # 座標のソート
        # FL, RL: 右の値から順に (X座標の降順: 大きい値 -> 小さい値)
        # FR, RR: 左の値から順に (X座標の昇順: 小さい値 -> 大きい値)
        if pos in ["FL", "RL"]:
            coords.sort(key=lambda x: x[0], reverse=True)
        else:
            coords.sort(key=lambda x: x[0])

        # CSVデータフレームの更新
        print(f"更新中: {file_name} -> {pos} (検出数: {len(coords)})")
        
        # 検出点数 (n_point) を更新
        if (pos, 'n_point') in df.columns:
             df.loc[match_key, (pos, 'n_point')] = len(coords)

        # 各座標を書き込み
        for i, (cx, cy) in enumerate(coords):
            point_idx = i + 1 # 1始まり
            
            # カラム名の定義: 1, 1_x, 1_y など
            # CSVのヘッダー構造に合わせてタプルで指定 (Level1, Level2)
            col_flag = (pos, f"{point_idx}")
            col_x = (pos, f"{point_idx}_x")
            col_y = (pos, f"{point_idx}_y")
            
            # カラムが存在すれば書き込む
            if col_x in df.columns and col_y in df.columns:
                df.loc[match_key, col_x] = cx
                df.loc[match_key, col_y] = cy
                
                # フラグ列(番号だけの列)があれば 1 を立てる
                if col_flag in df.columns:
                    df.loc[match_key, col_flag] = 1
            else:
                # 定義されている点数枠(例:7点)を超えた場合は書き込めないので無視
                pass

    # CSV保存
    output_dir = os.path.dirname(csv_path) if os.path.dirname(csv_path) else "."
    output_csv = os.path.join(output_dir, "updated_" + os.path.basename(csv_path))
    
    try:
        df.to_csv(output_csv)
        print(f"\n全ての処理が完了しました。結果を '{output_csv}' に保存しました。")
    except Exception as e:
        print(f"ファイル保存エラー: {e}")

if __name__ == "__main__":
    # コマンドライン引数の設定（引数がある場合はそちらを優先）
    parser = argparse.ArgumentParser(description="画像内の赤点座標を検出しCSVを更新します。")
    parser.add_argument("--image_dir", type=str, help="画像ファイルが格納されているフォルダパス")
    parser.add_argument("--csv_path", type=str, help="読み込むCSVファイルのパス")
    args = parser.parse_args()

    target_dir = args.image_dir
    target_csv = args.csv_path

    # Tkinterのルートウィンドウ作成（非表示）
    root = tk.Tk()
    root.withdraw()

    # 引数で指定されていない場合、ダイアログで選択
    if not target_dir:
        print("処理対象の画像フォルダを選択してください...")
        target_dir = filedialog.askdirectory(title="処理対象の画像フォルダを選択してください")

    if not target_dir:
        print("フォルダが選択されませんでした。プログラムを終了します。")
        sys.exit(1)

    if not target_csv:
        print("対象のCSVファイルを選択してください...")
        target_csv = filedialog.askopenfilename(
            title="対象のCSVファイルを選択してください",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

    if not target_csv:
        print("CSVファイルが選択されませんでした。プログラムを終了します。")
        sys.exit(1)

    # パスの存在確認
    if not os.path.exists(target_dir):
        print(f"エラー: 画像フォルダが見つかりません -> {target_dir}")
        sys.exit(1)
    
    if not os.path.exists(target_csv):
        print(f"エラー: CSVファイルが見つかりません -> {target_csv}")
        sys.exit(1)

    print(f"処理対象フォルダ: {target_dir}")
    print(f"対象CSVファイル: {target_csv}")
    
    # メイン処理実行
    update_csv_with_coords(target_dir, target_csv)