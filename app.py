from itertools import islice
import json
import aiohttp
from urllib.parse import quote
from duckduckgo_search import DDGS
from flask import Flask, request

app = Flask(__name__)


def run():
    if request.method == 'POST':
        keywords = request.form['q']
        max_results = int(request.form.get('max_results', 10))
    else:
        keywords = request.args.get('q')
        max_results = int(request.args.get('max_results', 10))
    return keywords, max_results


@app.route('/suggest', methods=['GET', 'POST'])
async def suggest():
    keywords, _ = run()

    # 构建 Bing API 请求 URL
    encoded_query = quote(keywords.encode('utf8'))
    url = f"https://sg1.api.bing.com/qsonhs.aspx?type=cb&cb=callback&q={encoded_query}&PC=EMMX01"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response.raise_for_status()
                response_text = await response.text()

                # 提取 JSON 部分
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx == -1 or end_idx == -1:
                    return {"error": "无效的响应格式"}, 500

                json_str = response_text[start_idx:end_idx]
                data = json.loads(json_str)

                # 提取所有建议词的文本
                suggestions = []
                for result in data.get("AS", {}).get("Results", []):
                    for suggest in result.get("Suggests", []):
                        text = suggest.get("Txt")
                        if text:  # 确保文本不为空
                            suggestions.append(text)
                return {"suggestions": suggestions}

    except aiohttp.ClientError as e:
        return {"error": f"API请求失败: {str(e)}"}, 500
    except (json.JSONDecodeError, KeyError) as e:
        return {"error": f"解析失败: {str(e)}"}, 500

@app.route('/search', methods=['GET', 'POST'])
async def search():
    keywords, max_results = run()
    results = []
    with DDGS() as ddgs:
        # 使用DuckDuckGo搜索关键词
        ddgs_gen = ddgs.text(keywords, safesearch='Off', timelimit='y', backend="lite")
        # 从搜索结果中获取最大结果数
        for r in islice(ddgs_gen, max_results):
            results.append(r)

    # 返回一个json响应，包含搜索结果
    return {'results': results}


@app.route('/search_images', methods=['GET', 'POST'])
async def search_images():
    keywords, max_results = run()
    results = []
    with DDGS() as ddgs:
        # 使用DuckDuckGo搜索关键词
        ddgs_gen = ddgs.images(keywords, safesearch='Off', timelimit=None)
        # 从搜索结果中获取最大结果数
        for r in islice(ddgs_gen, max_results):
            results.append(r)

    # 返回一个json响应，包含搜索结果
    return {'results': results}


@app.route('/search_videos', methods=['GET', 'POST'])
async def search_videos():
    keywords, max_results = run()
    results = []
    with DDGS() as ddgs:
        # 使用DuckDuckGo搜索关键词
        ddgs_gen = ddgs.videos(keywords, safesearch='Off', timelimit=None, resolution="high")
        # 从搜索结果中获取最大结果数
        for r in islice(ddgs_gen, max_results):
            results.append(r)

    # 返回一个json响应，包含搜索结果
    return {'results': results}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)