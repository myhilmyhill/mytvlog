import unicodedata
from pydantic import BaseModel
import re

def extract_model_fields(model: type[BaseModel], row: dict, aliases: dict[str, str] = None) -> dict:
    aliases = aliases or {}
    result = {}
    keys = row.keys()
    for field_name in model.model_fields.keys():
        source_key = aliases.get(field_name, field_name)
        if source_key in keys:
            result[field_name] = row[source_key]
    return result

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
