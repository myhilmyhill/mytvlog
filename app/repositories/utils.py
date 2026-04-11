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

    # 4. 話数・#番号・第xx回などを削除
    s = re.sub(r"[＃#♯]\d+", "", s)
    s = re.sub(r"第\d+[回話目夜]?", "", s)

    # 5. 番組詳細と思われるテキスト（副題など）を削除
    s = re.sub(r"\s+([\"“★▽「『].*|予選リーグ.*)", "", s)

    # 6. 余分な記号類の掃除
    s = re.sub(r"[-–――〜～\s]+$", "", s)  # 末尾の記号
    s = re.sub(r"\s{2,}", " ", s)          # 連続空白
    
    s = re.sub(r"AnichU+$", "", s, flags=re.IGNORECASE)

    return s.strip()
