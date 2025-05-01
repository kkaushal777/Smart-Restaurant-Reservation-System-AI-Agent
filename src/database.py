import pandas as pd
import os
import json
from datetime import datetime, timedelta
import random

class RestaurantDatabase:
    def __init__(self, data_dir=None):
         # Use absolute path for data directory
        if data_dir is None:
            # Get the directory of the current file (database.py)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level and then to data directory
            self.data_dir = os.path.abspath(os.path.join(current_dir, "..", "data"))
        else:
            # If a path is provided, make it absolute if it's not already
            self.data_dir = os.path.abspath(data_dir) if not os.path.isabs(data_dir) else data_dir
        self.restaurants = self._load_restaurants()
        self.reservations_file = os.path.join(self.data_dir, "reservations.json")
        self.reservations = self._load_reservations()
        
    def _load_restaurants(self):
        """Load restaurant data from CSV file"""
        try:
            restaurants_file = os.path.join(self.data_dir, "restaurants.csv")
            return pd.read_csv(restaurants_file)
        except Exception as e:
            print(f"Error loading restaurants: {e}")
            return pd.DataFrame()
    
    def _load_reservations(self):
        """Load reservations from JSON file or create empty reservations"""
        if os.path.exists(self.reservations_file):
            try:
                with open(self.reservations_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading reservations: {e}")
                return []
        else:
            return []
    
    def _save_reservations(self):
        """Save reservations to JSON file"""
        try:
            # Make sure the directory exists
            os.makedirs(os.path.dirname(self.reservations_file), exist_ok=True)
            
            # Save reservations with atomic write pattern for better reliability
            temp_file = f"{self.reservations_file}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(self.reservations, f, indent=2)
                
            # Ensure the write is flushed to disk
            f.flush()
            os.fsync(f.fileno())
            
            # Rename is atomic on most file systems - ensure file exists
            os.replace(temp_file, self.reservations_file)
                
        except Exception as e:
            print(f"Error saving reservations: {e}")
            # In a production system, this should use proper logging
            # import logging
            # logging.error(f"Failed to save reservations: {str(e)}")
            # Consider additional recovery mechanisms here
    
    def get_all_restaurants(self):
        """Return all restaurants"""
        return self.restaurants.to_dict('records')
    
    def get_restaurant_by_id(self, restaurant_id):
        """Get a specific restaurant by ID"""
        restaurant = self.restaurants[self.restaurants['id'] == int(restaurant_id)]
        if len(restaurant) > 0:
            return restaurant.iloc[0].to_dict()
        return None
    
    def search_restaurants(self, **kwargs):
        """
        Search restaurants based on criteria
        Possible kwargs: location, cuisine, min_rating, price_range, etc.
        """
        filtered_df = self.restaurants.copy()
        
        if 'location' in kwargs and kwargs['location']:
            filtered_df = filtered_df[filtered_df['location'].str.contains(kwargs['location'], case=False)]
        
        if 'cuisine' in kwargs and kwargs['cuisine']:
            filtered_df = filtered_df[filtered_df['cuisine'].str.contains(kwargs['cuisine'], case=False)]
        
        if 'min_rating' in kwargs and kwargs['min_rating']:
            filtered_df = filtered_df[filtered_df['rating'] >= float(kwargs['min_rating'])]
            
        if 'price_range' in kwargs and kwargs['price_range']:
            filtered_df = filtered_df[filtered_df['price_range'] == kwargs['price_range']]
            
        if 'min_capacity' in kwargs and kwargs['min_capacity']:
            filtered_df = filtered_df[filtered_df['capacity'] >= int(kwargs['min_capacity'])]
        
        return filtered_df.to_dict('records')
    
    def get_available_tables(self, restaurant_id, date, time, party_size):
        """Check table availability for a restaurant at a specific date and time"""
        # Validate inputs
        try:
            # Validate date format (YYYY-MM-DD)
            datetime.strptime(date, "%Y-%m-%d")
            # Validate time format (HH:MM)
            datetime.strptime(time, "%H:%M")
            # Validate party_size is a positive integer
            party_size = int(party_size)
            if party_size <= 0:
                return {"available": False, "reason": "Party size must be a positive number"}
            # Validate restaurant_id
            restaurant_id = int(restaurant_id)
        except ValueError as e:
            return {"available": False, "reason": f"Invalid input format: {str(e)}"}
        
        restaurant = self.get_restaurant_by_id(restaurant_id)
        if not restaurant:
            return {"available": False, "reason": "Restaurant not found"}
        
        # Check if the restaurant is open at the requested time
        if not self._is_restaurant_open(restaurant, time):
            return {"available": False, "reason": "Restaurant is not open at this time"}
        
        # Check if there's capacity available
        booked_seats = self._get_booked_seats(restaurant_id, date, time)
        available_seats = restaurant['capacity'] - booked_seats
        
        if available_seats >= party_size:
            return {
                "available": True, 
                "restaurant": restaurant,
                "available_seats": available_seats
            }
        else:
            return {
                "available": False, 
                "reason": f"Not enough seats available. Only {available_seats} seats left."
            }
    
    def _is_restaurant_open(self, restaurant, time_str):
        """Check if a restaurant is open at the given time"""
        time_format = "%H:%M"
        try:
            request_time = datetime.strptime(time_str, time_format).time()
            opening_time = datetime.strptime(restaurant['opening_time'], time_format).time()
            closing_time = datetime.strptime(restaurant['closing_time'], time_format).time()
            
            return opening_time <= request_time <= closing_time
        except Exception as e:
            print(f"Error checking restaurant hours: {e}")
            return False
    
    def _get_booked_seats(self, restaurant_id, date, time):
        """Get the number of already booked seats"""
        booked = 0
        for reservation in self.reservations:
            if (reservation['restaurant_id'] == restaurant_id and 
                reservation['date'] == date and 
                reservation['time'] == time):
                booked += reservation['party_size']
        return booked
    
    def create_reservation(self, customer_name, customer_email, restaurant_id, 
                         date, time, party_size, special_requests=""):
        """Create a new reservation"""
        availability = self.get_available_tables(restaurant_id, date, time, party_size)
        
        if not availability["available"]:
            return {"success": False, "message": availability["reason"]}
        
        # Generate unique reservation ID
        reservation_id = self._generate_reservation_id()
        
        # Create reservation object
        reservation = {
            "id": reservation_id,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "restaurant_id": restaurant_id,
            "restaurant_name": availability["restaurant"]["name"],
            "date": date,
            "time": time,
            "party_size": party_size,
            "special_requests": special_requests,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Add to reservations and save
        self.reservations.append(reservation)
        self._save_reservations()
        
        return {
            "success": True, 
            "reservation": reservation,
            "message": f"Reservation confirmed at {availability['restaurant']['name']} for {party_size} people on {date} at {time}"
        }
    
    def get_reservation(self, reservation_id):
        """Get a reservation by ID"""
        for reservation in self.reservations:
            if reservation['id'] == reservation_id:
                return reservation
        return None
    
    def get_reservations_by_email(self, email):
        """Get all reservations for a customer by email"""
        # return [r for r in self.reservations if r['customer_email'].lower() == email.lower()]
        return [r for r in self.reservations]
    
    def modify_reservation(self, reservation_id, **kwargs):
        """Modify an existing reservation"""
        for i, reservation in enumerate(self.reservations):
            if reservation['id'] == reservation_id:
                # Check availability if changing date, time, party_size or restaurant
                if ('date' in kwargs or 'time' in kwargs or 
                    'party_size' in kwargs or 'restaurant_id' in kwargs):
                    
                    new_date = kwargs.get('date', reservation['date'])
                    new_time = kwargs.get('time', reservation['time'])
                    new_party_size = kwargs.get('party_size', reservation['party_size'])
                    new_restaurant_id = kwargs.get('restaurant_id', reservation['restaurant_id'])
                    
                    # If changing restaurant, check availability at new restaurant
                    if new_restaurant_id != reservation['restaurant_id']:
                        availability = self.get_available_tables(
                            new_restaurant_id, new_date, new_time, new_party_size
                        )
                        if not availability["available"]:
                            return {"success": False, "message": availability["reason"]}
                        
                        # Update restaurant name
                        kwargs['restaurant_name'] = availability['restaurant']['name']
                    
                    # If changing date/time/party_size at same restaurant
                    elif (new_date != reservation['date'] or 
                          new_time != reservation['time'] or 
                          new_party_size != reservation['party_size']):
                        
                        # First "remove" the current reservation to check real availability
                        temp_reservations = self.reservations.copy()
                        self.reservations = [r for r in self.reservations if r['id'] != reservation_id]
                        
                        availability = self.get_available_tables(
                            new_restaurant_id, new_date, new_time, new_party_size
                        )
                        
                        # Restore reservations
                        self.reservations = temp_reservations
                        
                        if not availability["available"]:
                            return {"success": False, "message": availability["reason"]}
                
                # Update the reservation
                for key, value in kwargs.items():
                    reservation[key] = value
                
                self._save_reservations()
                return {"success": True, "reservation": reservation, "message": "Reservation updated successfully"}
        
        return {"success": False, "message": "Reservation not found"}
    
    def cancel_reservation(self, reservation_id):
        """Cancel a reservation"""
        for i, reservation in enumerate(self.reservations):
            if reservation['id'] == reservation_id:
                cancelled = self.reservations.pop(i)
                self._save_reservations()
                return {
                    "success": True, 
                    "message": f"Reservation at {cancelled['restaurant_name']} on {cancelled['date']} at {cancelled['time']} has been cancelled"
                }
        
        return {"success": False, "message": "Reservation not found"}
    
    def recommend_restaurants(self, **kwargs):
        """
        Recommend restaurants based on criteria and availability
        Possible kwargs: location, cuisine, rating, party_size, date, time
        """
        # First filter by the search criteria
        matching_restaurants = self.search_restaurants(
            location=kwargs.get('location', ''),
            cuisine=kwargs.get('cuisine', ''),
            min_rating=kwargs.get('min_rating', 0),
            price_range=kwargs.get('price_range', ''),
            min_capacity=kwargs.get('party_size', 0)
        )
        
        # If date and time are provided, check availability
        if 'date' in kwargs and 'time' in kwargs and 'party_size' in kwargs:
            available_restaurants = []
            for restaurant in matching_restaurants:
                availability = self.get_available_tables(
                    restaurant['id'], 
                    kwargs['date'], 
                    kwargs['time'],
                    kwargs['party_size']
                )
                if availability["available"]:
                    restaurant['available_seats'] = availability["available_seats"]
                    available_restaurants.append(restaurant)
            
            # Sort by rating (highest first)
            return sorted(available_restaurants, key=lambda x: x['rating'], reverse=True)
        
        # If no date/time specified, just return matches sorted by rating
        return sorted(matching_restaurants, key=lambda x: x['rating'], reverse=True)
    
    def _generate_reservation_id(self):
        """Generate a unique reservation ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = str(random.randint(100, 999))
        return f"RES-{timestamp}-{random_suffix}"