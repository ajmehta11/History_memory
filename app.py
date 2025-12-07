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
        st.markdown("### 👤 Your Shopping Profile")
        st.markdown("---")

        # Key metrics in columns
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🛒 Products", prefs.get("total_products", 0))
        with col2:
            cat_count = len(prefs.get("category_preferences", {}))
            st.metric("📦 Categories", cat_count)

        st.markdown("---")

        # Top Categories with icons
        st.markdown("#### 🏷️ Top Categories")
        cat_icons = {
            "Electronics": "💻", "Clothing": "👕", "Shoes": "👟",
            "Mobile": "📱", "Software": "⚙️", "Deals": "🎁"
        }
        for cat in prefs.get("top_categories", [])[:5]:
            icon = cat_icons.get(cat, "📌")
            st.markdown(f"{icon} **{cat}**")

        st.markdown("---")

        # Favorite Brands with progress bars
        st.markdown("#### ⭐ Favorite Brands")
        top_brands = prefs.get("top_brands", [])[:5]
        if top_brands:
            # Calculate brand counts from category preferences
            brand_counts = {}
            for cat_data in prefs.get("category_preferences", {}).values():
                for brand, count in cat_data.get("brands", {}).items():
                    brand_counts[brand] = brand_counts.get(brand, 0) + count

            max_count = max(brand_counts.values()) if brand_counts else 1
            for brand in top_brands:
                count = brand_counts.get(brand, 0)
                if count > 0:
                    progress = count / max_count
                    st.markdown(f"**{brand}** ({count})")
                    st.progress(progress)
                else:
                    st.markdown(f"**{brand}**")

        st.markdown("---")

        # Favorite Colors with color swatches
        st.markdown("#### 🎨 Favorite Colors")
        color_map = {
            "Black": "#000000", "White": "#FFFFFF", "Midnight Ocean": "#1B4965",
            "Holiday Fairisle": "#C41E3A", "Pine Shadow": "#2F4F4F",
            "Titanium Orange": "#FF6347", "Nebula Noir": "#191970",
            "Clear": "#F0F8FF", "Anthracite": "#293133", "Gum Light Brown": "#C19A6B"
        }

        for color in prefs.get("top_colors", [])[:5]:
            hex_color = color_map.get(color, "#808080")
            border_color = "#888888" if color == "White" or color == "Clear" else hex_color
            st.markdown(
                f'<div style="display: flex; align-items: center; margin-bottom: 8px;">'
                f'<div style="width: 24px; height: 24px; background-color: {hex_color}; '
                f'border: 2px solid {border_color}; border-radius: 4px; margin-right: 10px;"></div>'
                f'<span><strong>{color}</strong></span></div>',
                unsafe_allow_html=True
            )

        st.markdown("---")

        # Category insights with expanders
        st.markdown("#### 📊 Category Insights")
        cat_prefs = prefs.get("category_preferences", {})

        # Sort categories by count
        sorted_cats = sorted(
            cat_prefs.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True
        )

        for cat, data in sorted_cats[:6]:
            count = data.get("count", 0)
            if count > 0:
                icon = cat_icons.get(cat, "📌")
                with st.expander(f"{icon} {cat} ({count} items)", expanded=False):
                    # Top brands in this category
                    top_cat_brands = data.get("top_brands", [])[:3]
                    if top_cat_brands:
                        st.markdown("**🏆 Top Brands:**")
                        for brand in top_cat_brands:
                            brand_count = data.get("brands", {}).get(brand, 0)
                            st.markdown(f"• {brand} ({brand_count})")

                    # Favorite colors in this category
                    fav_colors = data.get("favorite_colors", [])[:3]
                    if fav_colors:
                        st.markdown("**🎨 Popular Colors:**")
                        for color in fav_colors:
                            st.markdown(f"• {color}")

                    # Price range
                    price_range = data.get("price_range", {})
                    min_p = price_range.get("min")
                    max_p = price_range.get("max")
                    avg_p = price_range.get("avg")

                    if min_p and max_p:
                        st.markdown(f"**💰 Price Range:** ${min_p:.2f} - ${max_p:.2f}")
                        if avg_p:
                            st.markdown(f"**📈 Average:** ${avg_p:.2f}")

                    # Preferred sizes
                    pref_sizes = data.get("preferred_sizes", [])[:3]
                    if pref_sizes:
                        st.markdown("**📏 Sizes:**")
                        for size in pref_sizes:
                            if size and size != "Select":
                                st.markdown(f"• {size}")

                    # Preferred condition
                    pref_condition = data.get("preferred_condition")
                    if pref_condition:
                        st.markdown(f"**✨ Preferred:** {pref_condition}")

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
