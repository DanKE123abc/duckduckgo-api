from itertools import islice
import json
import aiohttp
from urllib.parse import quote
from ddgs import DDGS
import re
from flask import Flask, request
import markdown
from markdownify import markdownify as mdify
from bs4 import BeautifulSoup
import tiktoken

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
        ddgs_gen = ddgs.text(keywords)
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
        ddgs_gen = ddgs.images(keywords)
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
        ddgs_gen = ddgs.videos(keywords)
        # 从搜索结果中获取最大结果数
        for r in islice(ddgs_gen, max_results):
            results.append(r)

    # 返回一个json响应，包含搜索结果
    return {'results': results}


@app.route('/fetch', methods=['GET', 'POST'])
async def fetch():
    keywords, max_results = run()
    url = keywords
    # 把 max_results 当“最大字数”用
    try:
        max_words = int(max_results) if max_results else 20000
    except (ValueError, TypeError):
        max_words = 20000

    headers = {
        "DNT": "1",
        "X-Retain-Images": "none",
        "X-Return-Format": "markdown",
    }
    async with aiohttp.ClientSession() as sess:
        async with sess.get(f"https://r.jina.ai/{url}", headers=headers) as r:
            r.raise_for_status()
            raw_md = await r.text()

    html = markdown.markdown(raw_md, extensions=['extra', 'codehilite'])
    soup = BeautifulSoup(html, 'lxml')
    for a in soup.find_all('a'):
        a.unwrap()
    for img in soup.find_all('img'):
        img.decompose()
    for noise in soup.select('header, footer, .advertisement, .sidebar'):
        noise.decompose()
    main = soup.find('article') or soup.find('main')
    if main:
        soup = BeautifulSoup(str(main), 'lxml')
    clean_md = mdify(str(soup), heading_style="ATX")

    # 直接截断最终 clean Markdown
    if len(clean_md) > max_words:
        clean_md = clean_md[:max_words]
        # 防止把代码块或单词劈开，回退到最近空格
        last_space = clean_md.rfind(' ')
        if last_space > max_words * 0.9:
            clean_md = clean_md[:last_space]

    return {"results": clean_md}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)