import unicodedata
from pydantic import BaseModel
import re
import json

def extract_model_fields(model: type[BaseModel], row: dict, aliases: dict[str, str] = None) -> dict:
    aliases = aliases or {}
    result = {}
    keys = row.keys()
    for field_name in model.model_fields.keys():
        source_key = aliases.get(field_name, field_name)
        if source_key in keys:
            result[field_name] = row[source_key]
    return result

async def extract_series_title_llm(raw: str, api_key: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key).aio
    response = await client.models.generate_content(
        model='gemini-2.5-flash',
        contents=f'''
        命令:
        与えられた番組表の文字列から「純粋な番組名」のみを抽出してください。
        【除外すべきノイズの定義】
            話数・回数: ＃10、(96)、第1夜 などの表記。
            放送枠・ジャンル: 【連続テレビ小説】、【ヌマニメーション】、日5、AnichU などの枠名。
            番組付随記号: [字]、[デ]、[再]、★、▽ などの記号。
            サブタイトル・詳細: 「」内や ～ 以降に続くエピソード名、および対戦カード（「日本」対「韓国」など）。
            宣伝文句: 記号以降に続く解説テキスト（例：★大人気ゲームを〜）。
        【例外ルール】
            **【推しの子】**のように、タイトル自体に【】が含まれる場合は、それを維持すること。
            世界選手権2025のように、年号がタイトルの一部である場合は維持すること。
        出力形式:
        JSON形式 {{"title": "抽出結果"}} で出力してください。

        対象文字列: {raw}
        ''',
        config=types.GenerateContentConfig(
            response_mime_type='application/json'
        )
    )
    data = json.loads(response.text)
    return data.get("title")

def extract_series_title(raw: str) -> str:
    """
    番組名の文字列からシリーズ名になりそうな最小タイトルを抽出する
    """
    s = raw.strip()

    # 全角英数→半角（必要なら）
    # ここでは見やすさのために最低限の正規化だけ
    s = unicodedata.normalize("NFKC", s)

    # 1. 放送属性タグなど [字][再] などを削除
    s = re.sub(r"\[[^\]]+\]", "", s)

    # 2. 装飾・シリーズ外注記 【連続テレビ小説】など削除
    # ただし、【推しの子】のようなタイトル自体が括弧で囲まれているケースは除外
    s = re.sub(r"【(?!推しの子】)[^】]+】", "", s)

    # 3. サブタイトル括弧を削除 「…」や『…』など
    s = re.sub(r"[（(<].*?[）)>]", "", s)

    # 4. シリーズ内属性 (期・章・Season・話数など) を削除
    # - 第xx期, 第xx章, 第xx話, xx期, xx部 etc.
    s = re.sub(r"第?[\d一二三四五六七八九十百]+[期章部回話目夜節]", " ", s)
    # - Season x, Part x, xnd Season, Vol.x etc.
    s = re.sub(r"(?i)(?:Season|Part|Vol|Volume|#|＃|♯)\.?\s*\d+", " ", s)
    s = re.sub(r"(?i)\d+(?:st|nd|rd|th)\s*Season", " ", s)
    # - ローマ数字 (孤立または末尾)
    s = re.sub(r"\s+[IVXLCDMivxlcdm]+(?:\s|$|\[|（|「|【)", " ", s)
    s = re.sub(r"(?<=[^\s])[IVXLCDMivxlcdm]+$", " ", s)

    # 5. サブタイトル・副題を削除
    # - スペースの後の 「」 『』 () [] （） 【】 など
    s = re.sub(r"\s+([\"“★☆▽▼「『(（\[【].*)", " ", s)
    # - 記号で区切られた後半部分
    s = re.sub(r"\s*[:：〜～\-ー－/／]{1,2}\s*.*$", "", s)
    # - 末尾の特定のキーワード以降
    s = re.sub(r"\s+(?:決定戦|SP|スペシャル|総集編|見どころ|オリジナル版|特別編).*$", "", s)

    # 6. クリーニング
    s = re.sub(r"[-–――—〜～\s]+$", "", s)  # 末尾の記号
    s = re.sub(r"^\s+[-–――—〜～\s]+", "", s)  # 先頭の記号
    s = re.sub(r"\s{2,}", " ", s)          # 連続空白
    
    s = re.sub(r"(?i)AnichU+$", "", s)

    return s.strip()
