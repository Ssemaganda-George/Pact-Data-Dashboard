# dashboard_autoEDA.py
import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
import plotly.graph_objects as go
import scipy.stats as stats
import pickle
from auth import auth, logout, check_session_timeout, update_activity

# Check auth
if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
    auth()
    st.stop()

# Check for session timeout
if check_session_timeout():
    st.stop()

# Update activity timestamp
update_activity()

# Main app for logged-in users
username = st.session_state["username"]

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="📊 Smart Auto EDA Dashboard", layout="wide")

st.title("PACT Automated EDA & Interactive Dashboard")
st.caption("Upload any dataset (CSV/Excel) and instantly explore insights, missing data, correlations, and visual trends.")

# -----------------------------
# SIDEBAR USER INFO AND LOGOUT
# -----------------------------
st.sidebar.header(f"Welcome, {username}.")
# st.sidebar.write(f"Email: {st.session_state['email']}")

# Session timeout indicator
if "last_activity" in st.session_state:
    import time
    time_since_activity = time.time() - st.session_state["last_activity"]
    remaining_time = (30 * 60) - time_since_activity  # 30 minutes timeout
    if remaining_time > 0:
        minutes_left = int(remaining_time // 60)
        st.sidebar.caption(f"Session expires in: {minutes_left} minutes")
    else:
        st.sidebar.caption("Session expired")

# Logout button with confirmation
if st.sidebar.button("Logout", type="primary"):
    # Use a modal-like approach with session state for confirmation
    st.session_state["show_logout_confirm"] = True

# Show logout confirmation if requested
if st.session_state.get("show_logout_confirm", False):
    st.sidebar.warning("Are you sure you want to logout?")
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("✅ Yes", key="confirm_logout"):
            st.session_state["show_logout_confirm"] = False
            logout()
    
    with col2:
        if st.button("❌ No", key="cancel_logout"):
            st.session_state["show_logout_confirm"] = False
            st.rerun()

st.sidebar.markdown("---")  # Separator line

# -----------------------------
# LOAD DATA
# -----------------------------
st.sidebar.header("Upload or Load Dataset")
uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

def load_data(uploaded_file):
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file, engine="openpyxl")
            st.toast("✅ Dataset loaded successfully!")
            return df
        except Exception as e:
            st.error(f"Error loading file: {e}")
            return None
    return None

if st.session_state["df"] is None:
    df = load_data(uploaded_file)
    if df is not None:
        st.session_state["df"] = df
        st.session_state["original_df"] = df.copy()
        st.session_state["original_shape"] = df.shape
        st.session_state["original_missing"] = df.isna().sum().sum()
        st.session_state["original_numeric"] = len(df.select_dtypes(include=['number']).columns)
        st.session_state["username"] = username  # Store username in session state
else:
    df = st.session_state["df"]

if df is None:
    st.info("Upload a dataset to continue.")
    st.stop()

original_df = st.session_state["original_df"]
original_shape = st.session_state["original_shape"]
original_missing = st.session_state["original_missing"]
original_numeric = st.session_state["original_numeric"]

# Reset button in sidebar
if st.sidebar.button("Reset to Original Data"):
    st.session_state["df"] = original_df.copy()
    df = st.session_state["df"]
    st.success("Data reset to original state.")
    # Re-identify column types
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=['number', 'datetime']).columns.tolist()
    date_cols = df.select_dtypes(include=['datetime']).columns.tolist()
    st.rerun()

# Session Management
st.sidebar.header("💾 Session Management")
session_name = st.sidebar.text_input("Session Name")
if st.sidebar.button("Save Session"):
    if session_name:
        user_sessions_dir = f"sessions/{username}"
        os.makedirs(user_sessions_dir, exist_ok=True)
        with open(f"{user_sessions_dir}/{session_name}.pkl", "wb") as f:
            pickle.dump(df, f)
        st.sidebar.success(f"Session '{session_name}' saved.")
    else:
        st.sidebar.error("Enter a session name.")

saved_sessions = [f.replace(".pkl", "") for f in os.listdir(f"sessions/{username}") if f.endswith(".pkl")] if os.path.exists(f"sessions/{username}") else []
if saved_sessions:
    load_session = st.sidebar.selectbox("Load Session", ["None"] + saved_sessions)
    if load_session != "None" and st.sidebar.button("Load Selected Session"):
        with open(f"sessions/{username}/{load_session}.pkl", "rb") as f:
            st.session_state["df"] = pickle.load(f)
        df = st.session_state["df"]
        st.sidebar.success(f"Session '{load_session}' loaded.")
        # Re-identify column types
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=['number', 'datetime']).columns.tolist()
        date_cols = df.select_dtypes(include=['datetime']).columns.tolist()
        st.rerun()

# -----------------------------
# DATA CLEANING & CONVERSION
# -----------------------------
st.subheader("Automatic Data Cleaning & Type Conversion")

# Convert date-like columns
for col in df.columns:
    if df[col].dtype == "object":
        try:
            df[col] = pd.to_datetime(df[col])
        except Exception:
            continue

# Handle missing values
with st.expander("Missing Values Handling"):
    missing_summary = df.isna().sum()
    missing_cols = missing_summary[missing_summary > 0]
    if not missing_cols.empty:
        st.warning(f"⚠️ Missing values found in {len(missing_cols)} columns.")
        st.write(missing_cols)
        selected_cols = st.multiselect("Select columns to handle missing values:", missing_cols.index.tolist())
        if selected_cols:
            for col in selected_cols:
                st.subheader(f"Handling for {col}")
                method = st.selectbox(f"Select method for {col}:", ["None", "Mean", "Median", "Mode", "Forward Fill", "Backward Fill", "Custom Value"], key=f"method_{col}")
                if method == "Custom Value":
                    custom_val = st.text_input(f"Enter custom value for {col}:", key=f"custom_{col}")
            if st.button("Apply Missing Value Handling"):
                with st.spinner("Processing missing values..."):
                    for col in selected_cols:
                        method = st.session_state[f"method_{col}"]  
                        if method != "None":
                            if method == "Custom Value":
                                custom_val = st.session_state[f"custom_{col}"]
                                df[col] = df[col].fillna(custom_val)
                            elif method == "Forward Fill":
                                df[col] = df[col].fillna(method='ffill')
                            elif method == "Backward Fill":
                                df[col] = df[col].fillna(method='bfill')
                            else:
                                if df[col].dtype in ['number']:
                                    if method == "Mean":
                                        df[col] = df[col].fillna(df[col].mean())
                                    elif method == "Median":
                                        df[col] = df[col].fillna(df[col].median())
                                    elif method == "Mode":
                                        mode_val = df[col].mode()
                                        df[col] = df[col].fillna(mode_val[0] if not mode_val.empty else 0)
                                else:
                                    if method == "Mode":
                                        mode_val = df[col].mode()
                                        df[col] = df[col].fillna(mode_val[0] if not mode_val.empty else "Unknown")
                                    else:
                                        df[col] = df[col].fillna("Unknown")
                st.toast("✅ Missing values handled.")

# Manual Type Conversion
with st.expander("Feature Type Conversion"):
    col_to_convert = st.selectbox("Select column to convert:", df.columns.tolist())
    conversion_type = st.selectbox("Select conversion type:", ["Datetime", "Numeric", "Categorical"])
    if st.button("Convert"):
        try:
            if conversion_type == "Datetime":
                df[col_to_convert] = pd.to_datetime(df[col_to_convert])
            elif conversion_type == "Numeric":
                df[col_to_convert] = pd.to_numeric(df[col_to_convert], errors='coerce')
            elif conversion_type == "Categorical":
                df[col_to_convert] = df[col_to_convert].astype('category')
            st.success(f"Converted {col_to_convert} to {conversion_type}.")
            # Re-identify column types after conversion
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            categorical_cols = df.select_dtypes(exclude=['number', 'datetime']).columns.tolist()
            date_cols = df.select_dtypes(include=['datetime']).columns.tolist()
        except Exception as e:
            st.error(f"Conversion failed: {e}")

# Identify column types
numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
categorical_cols = df.select_dtypes(exclude=['number', 'datetime']).columns.tolist()
date_cols = df.select_dtypes(include=['datetime']).columns.tolist()

# -----------------------------
# DATA OVERVIEW
# -----------------------------
st.markdown("## 📋 Dataset Overview")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Rows", f"{df.shape[0]:,}")
col2.metric("Columns", f"{df.shape[1]:,}")
col3.metric("Numeric Columns", len(numeric_cols))
col4.metric("Categorical Columns", len(categorical_cols))

with st.expander("Preview Dataset Head"):
    st.dataframe(df.head(), use_container_width=True)

with st.expander("Descriptive Statistics"):
    st.dataframe(df.describe(include='all'), use_container_width=True)

# -----------------------------
# AUTO INSIGHTS GENERATION
# -----------------------------
with st.expander("Feature Descriptions"):
    if st.button("Generate Insights"):
        with st.spinner("Generating insights..."):
            insights = []

            if len(numeric_cols) > 0:
                for col in numeric_cols:
                    mean_val = df[col].mean()
                    max_val = df[col].max()
                    min_val = df[col].min()
                    std_val = df[col].std()
                    insights.append(f"**{col}** → Mean: {mean_val:.2f}, Range: ({min_val:.2f} - {max_val:.2f}), Std: {std_val:.2f}")

            if len(categorical_cols) > 0:
                for col in categorical_cols:
                    top_cat = df[col].value_counts().idxmax()
                    top_count = df[col].value_counts().max()
                    insights.append(f"**{col}** → Most frequent: {top_cat} ({top_count} occurrences)")

            if insights:
                for i in insights:
                    st.markdown(f"- {i}")
            else:
                st.info("No insights could be generated — please check your data types.")

# -----------------------------
# VISUAL EXPLORATION
# -----------------------------
with st.expander("Visual Explorations"):
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Numeric", "Categorical", "Time Series", "Correlations", "Heatmaps", "Statistical Tests"])

    with tab1:
        if numeric_cols:
            x_col = st.selectbox("X-axis", numeric_cols)
            y_col = st.selectbox("Y-axis", numeric_cols, index=min(1, len(numeric_cols)-1))
            chart_type = st.radio("Chart Type", ["Scatter", "Bar", "Box", "Line"], horizontal=True)
            if chart_type == "Scatter":
                fig = px.scatter(df, x=x_col, y=y_col, color=df[categorical_cols[0]] if categorical_cols else None)
            elif chart_type == "Bar":
                fig = px.bar(df, x=x_col, y=y_col)
            elif chart_type == "Box":
                fig = px.box(df, y=y_col, x=x_col)
            else:
                fig = px.line(df, x=x_col, y=y_col)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No numeric columns detected.")

    with tab2:
        if categorical_cols and numeric_cols:
            cat_col = st.selectbox("Category", categorical_cols)
            val_col = st.selectbox("Value", numeric_cols)
            chart_type = st.radio("Chart Type", ["Bar Chart", "Pie Chart"], horizontal=True)
            grouped_data = df.groupby(cat_col)[val_col].mean().reset_index()
            if chart_type == "Bar Chart":
                fig = px.bar(grouped_data, x=cat_col, y=val_col,
                             title=f"Average {val_col} by {cat_col}")
            else:  # Pie Chart
                fig = px.pie(grouped_data, values=val_col, names=cat_col,
                             title=f"Average {val_col} Distribution by {cat_col}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Need at least one categorical and numeric column.")

    with tab3:
        if date_cols and numeric_cols:
            date_col = st.selectbox("Date", date_cols)
            val_col = st.selectbox("Value", numeric_cols, key="time_val2")
            trend = df.groupby(date_col)[val_col].mean().reset_index()
            fig = px.line(trend, x=date_col, y=val_col, title=f"{val_col} Over Time")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No date or numeric columns found.")

    with tab4:
        if len(numeric_cols) > 1:
            corr = df[numeric_cols].corr()
            fig = px.imshow(corr, text_auto=True, aspect="auto", title="🔗 Correlation Heatmap",
                           color_continuous_scale='RdBu_r', zmin=-1, zmax=1)
            fig.update_layout(width=700, height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            # Show strongest correlations
            st.subheader("🎯 Strongest Correlations")
            corr_pairs = []
            for i in range(len(corr.columns)):
                for j in range(i+1, len(corr.columns)):
                    corr_pairs.append({
                        'Variable 1': corr.columns[i],
                        'Variable 2': corr.columns[j],
                        'Correlation': corr.iloc[i, j]
                    })
            
            if corr_pairs:
                corr_df = pd.DataFrame(corr_pairs)
                corr_df = corr_df.reindex(corr_df['Correlation'].abs().sort_values(ascending=False).index)
                st.dataframe(corr_df.head(10))
        else:
            st.info("Not enough numeric columns for correlation heatmap.")

    with tab5:
        st.subheader("🔥 Advanced Heatmap Visualizations")
        
        heatmap_type = st.selectbox("Select Heatmap Type:", [
            "Correlation Matrix",
            "Missing Values Pattern", 
            "Data Distribution",
            "Pivot Table Heatmap"
        ])
        
        if heatmap_type == "Correlation Matrix" and len(numeric_cols) > 1:
            # Enhanced correlation heatmap
            selected_numeric = st.multiselect("Select columns for correlation:", numeric_cols, default=numeric_cols)
            if selected_numeric:
                corr = df[selected_numeric].corr()
                
                # Customization options
                col1, col2 = st.columns(2)
                with col1:
                    color_scale = st.selectbox("Color Scale:", ['RdBu_r', 'viridis', 'plasma', 'coolwarm'])
                with col2:
                    show_values = st.checkbox("Show Values", value=True)
                
                fig = px.imshow(corr, 
                               text_auto=show_values, 
                               aspect="auto", 
                               title="📊 Enhanced Correlation Heatmap",
                               color_continuous_scale=color_scale,
                               zmin=-1, zmax=1)
                fig.update_layout(width=800, height=600)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Please select at least two numeric columns for correlation.")
            
        elif heatmap_type == "Missing Values Pattern":
            # Missing values heatmap
            missing_data = df.isnull()
            if missing_data.sum().sum() > 0:
                fig = px.imshow(missing_data.T, 
                              aspect="auto", 
                              title="🕳️ Missing Values Pattern (Yellow = Missing)",
                              color_continuous_scale=['blue', 'yellow'])
                fig.update_layout(
                    xaxis_title="Row Index",
                    yaxis_title="Columns"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("🎉 No missing values found in the dataset!")
        
        elif heatmap_type == "Data Distribution":
            # Data distribution heatmap
            if numeric_cols:
                selected_cols = st.multiselect("Select columns for distribution heatmap:", 
                                             numeric_cols, 
                                             default=numeric_cols[:5])
                if selected_cols:
                    # Normalize data for better visualization
                    normalized_data = df[selected_cols].apply(lambda x: (x - x.min()) / (x.max() - x.min()) if x.max() != x.min() else x)
                    
                    fig = px.imshow(normalized_data.T, 
                                  aspect="auto",
                                  title="📈 Normalized Data Distribution Heatmap",
                                  color_continuous_scale='viridis')
                    fig.update_layout(
                        xaxis_title="Row Index",
                        yaxis_title="Variables"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No numeric columns available for distribution heatmap.")
        
        elif heatmap_type == "Pivot Table Heatmap":
            # Pivot table heatmap
            if categorical_cols and numeric_cols:
                col1, col2, col3 = st.columns(3)
                with col1:
                    pivot_index = st.selectbox("Rows (Index):", categorical_cols)
                with col2:
                    pivot_columns = st.selectbox("Columns:", categorical_cols, 
                                               index=1 if len(categorical_cols) > 1 else 0)
                with col3:
                    pivot_values = st.selectbox("Values:", numeric_cols)
                
                try:
                    pivot_table = df.pivot_table(
                        index=pivot_index, 
                        columns=pivot_columns, 
                        values=pivot_values, 
                        aggfunc='mean'
                    )
                    
                    fig = px.imshow(pivot_table, 
                                  text_auto=True,
                                  aspect="auto",
                                  title=f"📊 Pivot Heatmap: {pivot_values} by {pivot_index} vs {pivot_columns}",
                                  color_continuous_scale='blues')
                    fig.update_layout(
                        xaxis_title=pivot_columns,
                        yaxis_title=pivot_index
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                except Exception as e:
                    st.error(f"Could not create pivot heatmap: {e}")
            else:
                st.info("Need both categorical and numeric columns for pivot heatmap.")
        
    with tab6:
        if len(categorical_cols) > 1:
            st.subheader("📊 Chi-Square Tests for Categorical Variables")
            target = st.selectbox("Select Target Variable (Categorical):", categorical_cols)
            features = st.multiselect("Select Features (Categorical):", [c for c in categorical_cols if c != target], default=[])
            
            if features:
                results = []
                for feature in features:
                    try:
                        contingency_table = pd.crosstab(df[target], df[feature])
                        if contingency_table.size > 1:  
                            chi2, p, dof, expected = stats.chi2_contingency(contingency_table)
                            results.append({
                                "Feature": feature,
                                "Chi2 Statistic": round(chi2, 2),
                                "p-value": round(p, 4),
                                "Degrees of Freedom": dof
                            })
                        else:
                            results.append({
                                "Feature": feature,
                                "Chi2 Statistic": "N/A",
                                "p-value": "N/A",
                                "Degrees of Freedom": "N/A"
                            })
                    except Exception as e:
                        results.append({
                            "Feature": feature,
                            "Chi2 Statistic": "Error",
                            "p-value": str(e),
                            "Degrees of Freedom": "N/A"
                        })
                
                results_df = pd.DataFrame(results)
                st.dataframe(results_df, use_container_width=True)
                st.info("**Interpretation**: Low p-value (< 0.05) suggests significant association between feature and target.")
            else:
                st.info("Please select at least one feature to perform tests.")
        else:
            st.info("Need at least two categorical columns for statistical tests.")

# -----------------------------
# DATA CLEANING SUMMARY
# -----------------------------
st.markdown("## 📊 Data Cleaning Summary")
st.write(f"**Original Rows:** {original_shape[0]:,}, **Current Rows:** {df.shape[0]:,}")
st.write(f"**Original Columns:** {original_shape[1]:,}, **Current Columns:** {df.shape[1]:,}")
st.write(f"**Original Missing Values:** {original_missing:,}, **Current Missing Values:** {df.isna().sum().sum():,}")
st.write(f"**Original Numeric Columns:** {original_numeric}, **Current Numeric Columns:** {len(numeric_cols)}")
st.info("Note: Manual type conversions and missing value handling may have altered column types and data.")

# -----------------------------
# DOWNLOAD CLEANED DATA
# -----------------------------
st.markdown("## 💾 Export Cleaned Data")
csv = df.to_csv(index=False).encode('utf-8')
st.download_button("⬇ Download Cleaned Dataset", csv, "cleaned_data.csv", "text/csv")

st.success("✅ Auto EDA complete! Explore, visualize, and export your insights.")

# Persist changes to session state
st.session_state["df"] = df
