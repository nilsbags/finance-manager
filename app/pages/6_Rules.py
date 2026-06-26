"""Page: manage the category taxonomy view and the auto-categorization rules."""

import streamlit as st

import categories
import database
import rules

st.set_page_config(
    page_title="Categories & Rules · Finance Manager", page_icon="⚙️", layout="wide"
)
database.init_db()

st.title("⚙️ Categories & Rules")
st.caption(
    "Rules match a case-insensitive substring in the description and assign a "
    "category + subcategory. They apply in order — the first match wins."
)

tab_rules, tab_taxonomy = st.tabs(["Rules", "Category overview"])

# --------------------------------------------------------------------------- #
# Rules tab
# --------------------------------------------------------------------------- #
with tab_rules:
    # --- Add a rule -------------------------------------------------------- #
    st.subheader("Add a rule")
    with st.form("add_rule", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        pattern = c1.text_input("If description contains", placeholder="e.g. BILLA")
        category = c2.selectbox("Category", categories.all_categories(include_uncategorized=False))
        subcategory = c3.selectbox("Subcategory", [""] + categories.subcategories(category))
        submitted = st.form_submit_button("Add rule", type="primary")
        if submitted:
            if pattern.strip():
                database.add_rule(pattern, category, subcategory)
                label = f"{category} › {subcategory}" if subcategory else category
                st.success(f'Added rule: "{pattern.strip()}" → {label}')
                st.rerun()
            else:
                st.warning("A pattern is required.")

    # --- Bulk actions ------------------------------------------------------ #
    n_rules = database.count_rules()
    a1, a2, a3 = st.columns([2, 1, 1])
    a1.metric("Active rules", n_rules)
    if a2.button("Load starter rules", help="Add any built-in rules you don't already have"):
        added = database.reload_starter_rules()
        st.success(f"Added {added} starter rule(s).")
        st.rerun()
    if a3.button("Apply rules now", type="primary", help="Re-categorize uncategorized transactions"):
        changed = rules.apply_rules_to_existing(only_uncategorized=True)
        st.success(f"Updated {changed} transaction(s).")

    st.divider()

    # --- Existing rules, grouped by category ------------------------------- #
    st.subheader("Existing rules")
    rule_rows = database.fetch_rules()
    if not rule_rows:
        st.info("No rules yet. Add one above or load the starter rules.")
    else:
        # Group rules under their top-level category for a tidy overview.
        grouped: dict[str, list] = {}
        for row in rule_rows:
            grouped.setdefault(row["category"], []).append(row)

        for category in sorted(grouped):
            color = categories.color_for(category)
            st.markdown(
                f"<span style='display:inline-block;width:10px;height:10px;border-radius:50%;"
                f"background:{color};margin-right:6px'></span>**{category}** "
                f"<span style='opacity:0.6'>({len(grouped[category])})</span>",
                unsafe_allow_html=True,
            )
            for row in grouped[category]:
                c1, c2, c3 = st.columns([3, 3, 1])
                c1.markdown(f'&nbsp;&nbsp;contains **"{row["pattern"]}"**', unsafe_allow_html=True)
                c2.markdown(f'→ {row["subcategory"] or "—"}')
                if c3.button("Delete", key=f"del_{row['id']}"):
                    database.delete_rule(row["id"])
                    st.rerun()

# --------------------------------------------------------------------------- #
# Category overview tab
# --------------------------------------------------------------------------- #
with tab_taxonomy:
    st.subheader("Category taxonomy")
    st.caption("The full set of categories and their subcategories used across the app.")
    cols = st.columns(3)
    for i, (category, subs) in enumerate(categories.TAXONOMY.items()):
        with cols[i % 3]:
            color = categories.color_for(category)
            with st.container(border=True):
                st.markdown(
                    f"<span style='display:inline-block;width:12px;height:12px;border-radius:50%;"
                    f"background:{color};margin-right:8px'></span>**{category}**",
                    unsafe_allow_html=True,
                )
                st.markdown("\n".join(f"- {s}" for s in subs))
