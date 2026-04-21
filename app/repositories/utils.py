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

async def extract_series_title_llm(raw: str, github_token: str) -> str:
    import httpx
    import json
    
    url = "https://models.github.ai/inference/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {github_token}",
    }
    messages = [
        {"role": "system", "content": '''
            You are a specialized tool that extracts the core SERIES title from Japanese TV program names.
            Output ONLY a JSON object: {"title":"..."}. NO EXPLANATIONS.
            The series title is almost always the FIRST PART of the input string.
            Discard episode numbers (#3), subtitles in brackets, or secondary titles that come after the main title.
            '''},
        {"role": "user", "content": "逃がした魚は大きかったが釣りあげた魚が大きすぎた件　＃３「逃がした魚の淑女修行」"},
        {"role": "assistant", "content": '{"title": "逃がした魚は大きかったが釣りあげた魚が大きすぎた件"}'},
        {"role": "user", "content": "【推しの子】第2期　＃12"},
        {"role": "assistant", "content": '{"title": "【推しの子】"}'},
        {"role": "user", "content": "女神「異世界転生何になりたいですか」　俺「勇者の肋骨で」　ＡｎｉｃｈＵ"},
        {"role": "assistant", "content": '{"title": "女神「異世界転生何になりたいですか」　俺「勇者の肋骨で」"}'},
        {"role": "user", "content": "オタクに優しいギャルはいない!?　＃２【イマニメーションＷ】[デ][字]"},
        {"role": "assistant", "content": '{"title": "オタクに優しいギャルはいない!?"}'},
        {"role": "user", "content": "映画『スーパーマリオ／魔界帝国の女神』　★大人気ゲームをハリウッドが実写化!?"},
        {"role": "assistant", "content": '{"title": "スーパーマリオ/魔界帝国の女神"}'},
        {"role": "user", "content": "カーリング女子世界選手権２０２５　予選リーグ「日本」対「韓国」"},
        {"role": "assistant", "content": '{"title": "カーリング女子世界選手権２０２５"}'},
        {"role": "user", "content": "サンデーモーニング[字] “記録づくめ”酷暑に悲鳴▽記者殺害「ダブルタップ攻撃」とは"},
        {"role": "assistant", "content": '{"title": "サンデーモーニング"}'},
        {"role": "user", "content": f"{raw}\nTitle Extraction JSON:"}
    ]
    
    payload = {
        "messages": messages,
        "model": "openai/gpt-4o-mini",
        "temperature": 0.0,
        "max_tokens": 128,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            # Remove Markdown block if present
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?|```$", "", content, flags=re.MULTILINE).strip()
            
            # Try to find JSON if content contains more than just JSON
            if not content.startswith("{"):
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    content = match.group(0)

            result = json.loads(content)
            return result.get("title")
        except Exception as e:
            print(f"Failed to extract title with LLM:")
            print(e)
            if 'response' in locals():
                print(f"Raw Response Content: {response.text}")
            return None

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
    s = re.sub(r"\s*[:：〜～\-－/／]{1,2}\s*.*$", "", s)
    # - 末尾の特定のキーワード以降
    s = re.sub(r"\s+(?:決定戦|SP|スペシャル|総集編|見どころ|オリジナル版|特別編).*$", "", s)

    # 6. クリーニング
    s = re.sub(r"[-–――—〜～\s]+$", "", s)  # 末尾の記号
    s = re.sub(r"^\s+[-–――—〜～\s]+", "", s)  # 先頭の記号
    s = re.sub(r"\s{2,}", " ", s)          # 連続空白
    
    s = re.sub(r"(?i)AnichU+$", "", s)

    return s.strip()
