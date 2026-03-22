import streamlit as st
import requests

st.set_page_config(page_title="产品知识库助手", page_icon="📚")
st.title("📚 产品知识库助手")

# 从 Streamlit Secrets 读取配置
FEISHU_APP_ID = st.secrets["feishu_app_id"]
FEISHU_APP_SECRET = st.secrets["feishu_app_secret"]
GLM_API_KEY = st.secrets["glm_api_key"]

def search_feishu(query):
    """搜索飞书文档"""
    resp = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    )
    token = resp.json()["tenant_access_token"]
    
    resp = requests.get(
        "https://open.feishu.cn/open-apis/search/v1/data",
        headers={"Authorization": f"Bearer {token}"},
        params={"query": query, "page_size": 3}
    )
    
    items = resp.json().get("data", {}).get("items", [])
    return [{"title": i["title"], "url": i["url"], "content": i.get("content", "")[:300]} for i in items]

def ask_glm(question, docs):
    """调用 GLM 回答"""
    context = "\n\n".join([f"【{d['title']}】{d['content']}" for d in docs])
    prompt = f"""基于以下知识库内容回答问题：

{context}

问题：{question}
要求：1.只说知识库中有的事实 2.用 bullet 点回答"""

    resp = requests.post(
        "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        headers={"Authorization": f"Bearer {GLM_API_KEY}"},
        json={
            "model": "glm-4",
            "messages": [
                {"role": "system", "content": "你是产品经理助手"},
                {"role": "user", "content": prompt}
            ]
        }
    )
    return resp.json()["choices"][0]["message"]["content"]

# 聊天界面
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("输入问题，例如：课程详情页改版影响哪些模块？"):
    st.session_state.messages.append({"role": "user", "content": question})
    
    with st.chat_message("user"):
        st.markdown(question)
    
    with st.chat_message("assistant"):
        with st.spinner("🔍 搜索中..."):
            try:
                docs = search_feishu(question)
                if docs:
                    answer = ask_glm(question, docs)
                    st.markdown(answer)
                    with st.expander("📄 参考文档"):
                        for d in docs:
                            st.markdown(f"[{d['title']}]({d['url']})")
                else:
                    st.info("未找到相关文档")
            except Exception as e:
                st.error(f"出错：{e}")
