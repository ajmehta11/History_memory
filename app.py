import streamlit as st
import json
from pathlib import Path
import pandas as pd
from agent import agent

st.set_page_config(page_title="Shopping Assistant", page_icon="🛍️", layout="wide")

st.title("🛍️ Shopping Assistant")

# Load user preferences
prefs_path = Path(__file__).parent / "Tools" / "user_preferences.json"
if prefs_path.exists():
    with open(prefs_path, "r") as f:
        prefs = json.load(f)
else:
    prefs = None

# Sidebar with user preferences
if prefs:
    with st.sidebar:
        st.header("📊 Your Shopping Profile")

        st.metric("Total Products Viewed", prefs.get("total_products", 0))

        st.subheader("Top Categories")
        for cat in prefs.get("top_categories", [])[:5]:
            st.write(f"• {cat}")

        st.subheader("Favorite Brands")
        for brand in prefs.get("top_brands", [])[:5]:
            st.write(f"• {brand}")

        st.subheader("Favorite Colors")
        for color in prefs.get("top_colors", [])[:5]:
            st.write(f"• {color}")

        # Category breakdown
        st.subheader("Category Breakdown")
        cat_prefs = prefs.get("category_preferences", {})
        if cat_prefs:
            cat_data = []
            for cat, data in cat_prefs.items():
                cat_data.append({
                    "Category": cat,
                    "Count": data.get("count", 0)
                })
            if cat_data:
                df = pd.DataFrame(cat_data)
                st.bar_chart(df.set_index("Category"))

        # Price ranges by category
        st.subheader("Price Ranges")
        for cat, data in list(cat_prefs.items())[:5]:
            price_range = data.get("price_range", {})
            min_p = price_range.get("min")
            max_p = price_range.get("max")
            if min_p and max_p:
                st.write(f"**{cat}**: ${min_p:.0f} - ${max_p:.0f}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about products or your shopping history..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            result = agent.invoke(
                {"messages": [{"role": "user", "content": prompt}]}
            )
            response = result["messages"][-1].content
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
