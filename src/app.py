import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from database import RestaurantDatabase
from llm_agent import LLMAgent
import matplotlib.pyplot as plt
from PIL import Image

# Set page configuration
st.set_page_config(
    page_title="FoodieSpot Reservation System",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
@st.cache_resource
def get_database():
    return RestaurantDatabase()

db = get_database()

# Initialize LLM Agent (this will need an API key)
@st.cache_resource
def get_llm_agent():
    return LLMAgent(db_instance=db)

# Create session state variables
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'current_view' not in st.session_state:
    st.session_state.current_view = "chat"
if 'reservation_details' not in st.session_state:
    st.session_state.reservation_details = {}

# Custom CSS
st.markdown("""
<style>
    .chat-message {
        padding: 1.5rem; 
        border-radius: 0.5rem; 
        margin-bottom: 1rem; 
        display: flex;
        align-items: flex-start;
        color: #333333;
    }
    .chat-message.user {
        background-color: #F0F2F6;
        text-align: right;
        margin-left: 15%;
        color: #000000;
    }
    .chat-message.assistant {
        background-color: #E0F7FA;
        margin-right: 15%;
        color: #000000;
    }
    .chat-message .avatar {
        width: 40px;
        height: 40px;
        margin-right: 1rem;
    }
    .chat-message .message {
        flex-grow: 1;
    }
    .stButton button {
        width: 100%;
        border-radius: 20px;
        height: 3rem;
        font-size: 1rem;
        font-weight: bold;
    }
    .restaurant-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .restaurant-title {
        font-weight: bold;
        font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar with app options
with st.sidebar:
    st.title("🍽️ FoodieSpot")
    st.subheader("Restaurant Reservation System")
    
    # Navigation
    if st.button("💬 Chat with Assistant", use_container_width=True):
        st.session_state.current_view = "chat"
    if st.button("🔍 Browse Restaurants", use_container_width=True):
        st.session_state.current_view = "browse"
    if st.button("📝 My Reservations", use_container_width=True):
        st.session_state.current_view = "reservations"
    
    st.divider()
    
    # User information for reservations
    st.subheader("Your Information")
    user_name = st.text_input("Name", value="Kaushal Kishore")
    user_email = st.text_input("Email", value="kaushal@gmail.com")
    
    st.divider()
    st.caption("FoodieSpot AI Reservation System")
    st.caption("Version 1.0.0")

# Main content area
if st.session_state.current_view == "chat":
    st.header("Chat with Our Reservation Assistant")
    
    # Display chat history
    for message in st.session_state.conversation_history:
        if message["role"] == "user":
            with st.container():
                st.markdown(f"""
                <div class="chat-message user">
                    <div class="message">
                        {message["content"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            with st.container():
                st.markdown(f"""
                <div class="chat-message assistant">
                    <div class="message">
                        {message["content"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Chat input
    with st.container():
        user_input = st.chat_input("Type your message here...")
        if user_input:
            # Add user message to chat history
            st.session_state.conversation_history.append({"role": "user", "content": user_input})
            
            try:
                # Initialize LLM agent if not done already
                llm_agent = get_llm_agent()
                
                # Process with LLM
                with st.spinner("Thinking..."):
                    response = llm_agent.handle_conversation(user_input)
                
                # Add assistant response to chat history
                st.session_state.conversation_history.append({"role": "assistant", "content": response})
                
                # Check if the response contains rate limit error keywords to offer alternative options
                if "rate limit" in response.lower() or "usage limit" in response.lower() or "try again later" in response.lower():
                    # Show alternative options to the user
                    with st.expander("⚠️ AI Service Unavailable - View Alternatives", expanded=True):
                        st.info("""
                        While our AI assistant is temporarily unavailable, you can still:
                        1. Browse restaurants directly by clicking "Browse Restaurants" in the sidebar
                        2. Check your existing reservations via "My Reservations" 
                        3. Contact our support team at support@foodiespot.com
                        """)
                        col1, col2 = st.columns(2)
                        if col1.button("Browse Restaurants Instead"):
                            st.session_state.current_view = "browse"
                            st.rerun()
                        if col2.button("Check My Reservations"):
                            st.session_state.current_view = "reservations"
                            st.rerun()
                
                # Force a rerun to update the UI
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.session_state.conversation_history.append({"role": "assistant", "content": f"I'm sorry, but I encountered an error: {str(e)}"})
                st.rerun()

elif st.session_state.current_view == "browse":
    st.header("Browse Our Restaurants")
    
    # Filtering options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        cuisine_filter = st.selectbox(
            "Cuisine",
            options=["All"] + sorted(db.restaurants["cuisine"].unique().tolist())
        )
    
    with col2:
        location_filter = st.selectbox(
            "Location",
            options=["All"] + sorted(db.restaurants["location"].unique().tolist())
        )
    
    with col3:
        price_filter = st.selectbox(
            "Price Range",
            options=["All", "₹ (Under 500)", "₹₹ (500-1000)", "₹₹₹ (1000-1500)", "₹₹₹₹ (1500+)"]
        )
    
    # Apply filters
    filtered_restaurants = db.restaurants.copy()
    
    if cuisine_filter != "All":
        filtered_restaurants = filtered_restaurants[filtered_restaurants["cuisine"] == cuisine_filter]
    
    if location_filter != "All":
        filtered_restaurants = filtered_restaurants[filtered_restaurants["location"] == location_filter]
    
    if price_filter != "All":
        filtered_restaurants = filtered_restaurants[filtered_restaurants["price_range"] == price_filter]
    
    # Display restaurants
    if len(filtered_restaurants) > 0:
        for _, restaurant in filtered_restaurants.iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"""
                    <div class="restaurant-card">
                        <div class="restaurant-title">{restaurant['name']} - {restaurant['price_range']}</div>
                        <div>{restaurant['cuisine']} cuisine • {restaurant['location']}</div>
                        <div>Rating: {'⭐' * int(restaurant['rating'])} ({restaurant['rating']})</div>
                        <div>Capacity: {restaurant['capacity']} seats • Hours: {restaurant['opening_time']} to {restaurant['closing_time']}</div>
                        <div><em>Special feature: {restaurant['special_features']}</em></div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("Book Now", key=f"book_{restaurant['id']}"):
                        # Store restaurant details and switch to reservation form
                        st.session_state.reservation_details = {
                            "restaurant_id": restaurant['id'],
                            "restaurant_name": restaurant['name'],
                            "cuisine": restaurant['cuisine'],
                            "location": restaurant['location']
                        }
                        st.session_state.current_view = "make_reservation"
                        st.rerun()
    else:
        st.info("No restaurants found with the selected filters.")

elif st.session_state.current_view == "make_reservation":
    restaurant = st.session_state.reservation_details
    st.header(f"Make a Reservation at {restaurant['restaurant_name']}")
    st.subheader(f"{restaurant['cuisine']} cuisine • {restaurant['location']}")
    
    # Reservation form
    date = st.date_input(
        "Date",
        value=datetime.now() + timedelta(days=1)
    ).strftime("%Y-%m-%d")
    
    time = st.time_input(
        "Time",
        value=datetime.strptime("19:00", "%H:%M")
    ).strftime("%H:%M")
    
    party_size = st.number_input(
        "Number of People",
        min_value=1,
        max_value=20,
        value=2
    )
    
    special_requests = st.text_area(
        "Special Requests",
        placeholder="Any special requests for your reservation?"
    )
    
    # Create columns for buttons
    col1, col2 = st.columns(2)
    
    # Check availability button in the first column
    check_availability = col1.button("Check Availability")
    
    # Confirm reservation button in the second column (always visible)
    confirm_reservation = col2.button("Confirm Reservation")
    
    # Check availability when the button is clicked
    if check_availability:
        # Check if the chosen time is available
        availability = db.get_available_tables(
            restaurant_id=restaurant["restaurant_id"],
            date=date,
            time=time,
            party_size=party_size
        )
        
        if availability["available"]:
            st.success(f"Great news! We have availability for {party_size} people on {date} at {time}.")
        else:
            st.error(availability["reason"])
            
            # Suggest alternative times if the restaurant is open but full
            if "Not enough seats" in availability["reason"]:
                st.info("Would you like to try a different time or date?")
    
    # Handle reservation confirmation separately
    if confirm_reservation:
        # First check availability again to ensure it's still available
        availability = db.get_available_tables(
            restaurant_id=restaurant["restaurant_id"],
            date=date,
            time=time,
            party_size=party_size
        )
        
        if availability["available"]:
            # Create the reservation
            result = db.create_reservation(
                customer_name=user_name,
                customer_email=user_email,
                restaurant_id=restaurant["restaurant_id"],
                date=date,
                time=time,
                party_size=party_size,
                special_requests=special_requests
            )
            
            if result["success"]:
                st.success(result["message"])
                # Set the view to reservations and rerun
                st.session_state.current_view = "reservations"
                st.rerun()
            else:
                st.error(result["message"])
        else:
            st.error("Please check availability first. " + availability["reason"])
    
    # Button to go back to browse
    if st.button("Back to Browse"):
        st.session_state.current_view = "browse"
        st.rerun()

elif st.session_state.current_view == "reservations":
    st.header("My Reservations")
    
    # Get user's reservations by email
    # import pdb; pdb.set_trace()
    reservations = db.get_reservations_by_email(user_email)
    
    
    if reservations:
        for reservation in reservations:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"""
                    <div class="restaurant-card">
                        <div class="restaurant-title">{reservation['restaurant_name']}</div>
                        <div>Date: {reservation['date']} at {reservation['time']}</div>
                        <div>Party size: {reservation['party_size']} people</div>
                        <div>Reservation ID: {reservation['id']}</div>
                        <div>Special requests: {reservation['special_requests'] or 'None'}</div>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    if st.button("Cancel", key=f"cancel_{reservation['id']}"):
                        # Cancel the reservation
                        result = db.cancel_reservation(reservation['id'])
                        if result["success"]:
                            st.success(result["message"])
                            st.rerun()
                        else:
                            st.error(result["message"])
    else:
        st.info(f"No reservations found for {user_email}. Make a reservation to see it here!")
        
        # Button to go to browse restaurants
        if st.button("Browse Restaurants to Book"):
            st.session_state.current_view = "browse"
            st.rerun()

# Run the app with: streamlit run app.py