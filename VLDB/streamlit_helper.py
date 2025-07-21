import streamlit as st

def display_sort_info(sort_info):
    with st.expander("📊 Selected Sort Option", expanded=True):
        # Title section with highlight
        st.markdown(
            f"<div style='background-color:#fff3e0; padding:10px; border-radius:5px; border-left:4px solid #FF5722;'>"
            f"<h3 style='margin:0; color:#333;'>Sort Attribute: "
            f"<span style='color:#D84315; background-color:#FBE9E7; padding:2px 6px; border-radius:3px;'>{sort_info['Sort Attribute']}</span>"
            f"</h3></div>",
            unsafe_allow_html=True
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Convert interestingness to float if needed
        interestingness = float(sort_info['Interestingness'])
        
        # Create two columns for the data
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("<div style='background-color:#f9f9f9; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
            st.markdown("#### 🗂️ Column Information")
            st.markdown(f"**Base Column:** `{sort_info['Base Column']}`")
            st.markdown(f"**Required Column:** `{sort_info['Required Column']}`")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Display column status
            is_present = sort_info.get('Column present', 'No') == 'Yes'
            status_bg = "#E8F5E9" if is_present else "#FFEBEE"
            status_color = "#2E7D32" if is_present else "#C62828"
            status_icon = "✅" if is_present else "❌"
            status_text = "Column is available" if is_present else "Column needs augmentation"
            
            st.markdown(
                f"<div style='background-color:{status_bg}; padding:10px; border-radius:5px;'>"
                f"<h4 style='margin:0; color:{status_color};'>{status_icon} {status_text}</h4>"
                f"</div>",
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown("<div style='background-color:#f3e5f5; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
            st.markdown("#### 💡 Insight Value")
            # Create a progress bar for interestingness
            st.progress(interestingness)
            st.markdown(f"**Interestingness Score:** `{interestingness:.2f}`")
            st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Description box
            st.markdown("<div style='background-color:#e8eaf6; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
            st.markdown("#### 📝 Description")
            st.markdown(f"*{sort_info['Description']}*")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Add action buttons at the bottom
        st.markdown("<br>", unsafe_allow_html=True)
        col_btn1, col_btn2 = st.columns([1, 1])
        
        with col_btn1:
            if not is_present:
                st.button("🔍 Augment Missing Data", type="primary", key="augment_data")
            else:
                st.button("✅ Apply Sort", type="primary", key="apply_sort")
        
        with col_btn2:
            st.button("🔄 Select Different Option", key="select_different")


