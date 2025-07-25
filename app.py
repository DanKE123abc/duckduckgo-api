from itertools import islice

from duckduckgo_search import DDGS
from flask import Flask, request

app = Flask(__name__)


def run():
    if request.method == 'POST':
        keywords = request.form['q']
        max_results = int(request.form.get('max_results', 10))
    else:
        keywords = request.args.get('q')
        # 从请求参数中获取最大结果数，如果未指定，则默认为10
        max_results = int(request.args.get('max_results', 10))
    return keywords, max_results


@app.route('/suggest', methods=['GET', 'POST'])
def suggest():
    """获取搜索建议"""
    keywords, _ = run()  # 不需要 max_results 参数
    
    # 构建 Bing API 请求 URL
    encoded_query = quote(keywords.encode('utf8'))
    url = f"https://sg1.api.bing.com/qsonhs.aspx?type=cb&cb=callback&q={encoded_query}&PC=EMMX01"
    
    try:
        # 发送请求到 Bing API
        response = requests.get(url, timeout=5)
        response.raise_for_status()  # 检查 HTTP 错误
        
        # 直接解析响应内容
        try:
            # 提取 JSON 部分（去除 JSONP 包装）
            start_idx = response.text.find('{')
            end_idx = response.text.rfind('}') + 1
            if start_idx == -1 or end_idx == -1:
                return {"error": "无效的响应格式"}, 500
                
            json_str = response.text[start_idx:end_idx]
            data = json.loads(json_str)
            
            # 提取建议词
            suggestions = []
            for result in data.get("AS", {}).get("Results", []):
                for suggest in result.get("Suggests", []):
                    suggestions.append({
                        "text": suggest.get("Txt", ""),
                        "type": suggest.get("Type", ""),
                        "score": suggest.get("Sk", ""),
                        "hcs": suggest.get("HCS", 0)
                    })
            
            # 返回结构化结果
            return {
                "query": data.get("AS", {}).get("Query", ""),
                "full_results": data.get("AS", {}).get("FullResults", 0),
                "suggestions": suggestions
            }
            
        except (json.JSONDecodeError, KeyError) as e:
            return {"error": f"解析失败: {str(e)}"}, 500
        
    except requests.exceptions.RequestException as e:
        return {"error": f"API请求失败: {str(e)}"}, 500

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


@app.route('/searchImages', methods=['GET', 'POST'])
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


@app.route('/searchVideos', methods=['GET', 'POST'])
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
