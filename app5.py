import streamlit as st
import mysql.connector
import pandas as pd
from collections import Counter
import re
import pdfkit
import os
import matplotlib.pyplot as plt
import base64

# Function to connect to MySQL
def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='123456',
        database='brand_analysis'
    )
    return connection

# Function to verify login
def verify_login(name, password):
    expected_password = name[:3].lower() + '@123'
    return password == expected_password

# Function to fetch unique names
def get_unique_names():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT DISTINCT name FROM brand_insights")
    names = [row[0] for row in cursor.fetchall()]
    cursor.close()
    connection.close()
    return names

# Function to fetch business details
def get_business_details(name):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
    SELECT business_id, name, address, postal_code, business_ratings, csat, nps, strengths, areas_for_improvement
    FROM brand_insights
    WHERE name = %s
    """, (name,))
    results = cursor.fetchall()
    cursor.close()
    connection.close()
    
    df = pd.DataFrame(results)
    
    if not df.empty:
        avg_rating = df['business_ratings'].mean()
        highest_rated = df.loc[df['business_ratings'].idxmax()]
        lowest_rated = df.loc[df['business_ratings'].idxmin()]
        
        # Common strengths and areas for improvement
        strengths = ' '.join(df['strengths'].dropna())
        areas_for_improvement = ' '.join(df['areas_for_improvement'].dropna())
        
        strengths_words = re.findall(r'\b\w+\b', strengths.lower())
        areas_words = re.findall(r'\b\w+\b', areas_for_improvement.lower())
        
        common_strengths = Counter(strengths_words).most_common()
        common_areas = Counter(areas_words).most_common()
        
        # Limit to top 3
        top_common_strengths = [word for word, count in common_strengths[:3]]
        top_common_areas = [word for word, count in common_areas[:3]]
        
        return {
            'all_details': df,
            'avg_rating': avg_rating,
            'highest_rated': highest_rated,
            'lowest_rated': lowest_rated,
            'common_strengths': top_common_strengths,
            'common_areas_for_improvement': top_common_areas
        }
    else:
        return None

# Function to save plot as an image and return its base64 string
def save_plot_as_image(fig, filename):
    fig.savefig(filename, format='png')
    with open(filename, 'rb') as file:
        img_base64 = base64.b64encode(file.read()).decode('utf-8')
    return img_base64

# Function to generate PDF
def generate_pdf(html_content, filename):
    path_to_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'  # Update this path
    config = pdfkit.configuration(wkhtmltopdf=path_to_wkhtmltopdf)
    pdfkit.from_string(html_content, filename, configuration=config)

# Streamlit App---------------------------------------------------------------------------------------------------------------------
st.title('Brand Insights Login')

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'selected_name' not in st.session_state:
    st.session_state.selected_name = None

# Login page
if not st.session_state.logged_in:
    unique_names = get_unique_names()

    with st.form(key='login_form'):
        selected_name = st.selectbox('Select your unique name:', unique_names)
        password = st.text_input('Enter your password:', type='password')
        submit_button = st.form_submit_button('Login')

        if submit_button:
            if verify_login(selected_name, password):
                st.session_state.logged_in = True
                st.session_state.selected_name = selected_name
                st.write("Login successful! Redirecting to details page...")
                st.session_state.page = 'details'
            else:
                st.error('Invalid username or password.')

# Business details page
if st.session_state.logged_in:
    if 'page' not in st.session_state or st.session_state.page == 'details':
        st.write(f"Welcome, {st.session_state.selected_name}!")

        details = get_business_details(st.session_state.selected_name)
        if details:
            # Display all details of each business_id
            st.write('Business Details for All Locations:')
            st.dataframe(details['all_details'])
            
            # Display statistical analysis
            st.write(f"Total locations analyzed: {len(details['all_details'])}")
            st.write(f"Average business rating: {details['avg_rating']:.2f}")
            st.write(f"Highest rated location: {details['highest_rated']['address']} (Rating: {details['highest_rated']['business_ratings']})")
            st.write(f"Lowest rated location: {details['lowest_rated']['address']} (Rating: {details['lowest_rated']['business_ratings']})")
            
            # Plot business ratings distribution
            st.write("Distribution of Business Ratings:")
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.hist(details['all_details']['business_ratings'], bins=10, edgecolor='k', alpha=0.7)
            ax.set_title('Distribution of Business Ratings')
            ax.set_xlabel('Business Rating')
            ax.set_ylabel('Frequency')
            st.pyplot(fig)
            ratings_img_base64 = save_plot_as_image(fig, 'ratings_distribution.png')
            
            # Plot pie charts for strengths and areas for improvement
            st.write("Top 3 Strengths across All Locations:")
            fig, ax = plt.subplots(figsize=(7, 7))
            ax.pie([count for word, count in Counter(re.findall(r'\b\w+\b', ' '.join(details['common_strengths']).lower())).items()], 
                   labels=details['common_strengths'], autopct='%1.1f%%')
            ax.set_title('Top 3 Strengths')
            st.pyplot(fig)
            strengths_img_base64 = save_plot_as_image(fig, 'strengths_pie.png')
            
            st.write("Top 3 Areas for Improvement across All Locations:")
            fig, ax = plt.subplots(figsize=(7, 7))
            ax.pie([count for word, count in Counter(re.findall(r'\b\w+\b', ' '.join(details['common_areas_for_improvement']).lower())).items()], 
                   labels=details['common_areas_for_improvement'], autopct='%1.1f%%')
            ax.set_title('Top 3 Areas for Improvement')
            st.pyplot(fig)
            areas_img_base64 = save_plot_as_image(fig, 'areas_pie.png')

            # Generate HTML content for PDF with embedded images
            html_content = f"""
            <h1>Business Report for {st.session_state.selected_name}</h1>
            <p>Total locations analyzed: {len(details['all_details'])}</p>
            <p>Average business rating: {details['avg_rating']:.2f}</p>
            <p>Highest rated location: {details['highest_rated']['address']} (Rating: {details['highest_rated']['business_ratings']})</p>
            <p>Lowest rated location: {details['lowest_rated']['address']} (Rating: {details['lowest_rated']['business_ratings']})</p>
            <h2>Distribution of Business Ratings:</h2>
            <img src="data:image/png;base64,{ratings_img_base64}" alt="Ratings Distribution">
            <h2>Top 3 strengths across all locations:</h2>
            <p>{', '.join(details['common_strengths'])}</p>
            <img src="data:image/png;base64,{strengths_img_base64}" alt="Strengths Pie Chart">
            <h2>Top 3 areas for improvement across all locations:</h2>
            <p>{', '.join(details['common_areas_for_improvement'])}</p>
            <img src="data:image/png;base64,{areas_img_base64}" alt="Areas for Improvement Pie Chart">
            """
            
            pdf_filename = f"{st.session_state.selected_name}_report.pdf"
            
            if st.button("Generate PDF"):
                generate_pdf(html_content, pdf_filename)
                st.success(f"PDF report generated: {pdf_filename}")
                
                with open(pdf_filename, "rb") as file:
                    st.download_button(
                        label="Download PDF",
                        data=file,
                        file_name=pdf_filename,
                        mime="application/octet-stream"
                    )

        else:
            st.error('No business details found for the selected name.')

        if st.button('Logout'):
            st.session_state.logged_in = False
            st.session_state.selected_name = None
            st.session_state.page = None  # Redirect back to login page
            st.write("Logged out. Please log in again.")
