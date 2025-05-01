import os
import json
from openai import OpenAI
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Define tools that the LLM can use
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_restaurants",
            "description": "Search for restaurants based on location, cuisine type, or other criteria",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The area or district where the restaurant is located",
                    },
                    "cuisine": {
                        "type": "string",
                        "description": "The type of cuisine (e.g., Italian, Chinese, Seafood)",
                    },
                    "min_rating": {
                        "type": "number",
                        "description": "Minimum rating of the restaurant (1-5)",
                    },
                    "price_range": {
                        "type": "string",
                        "description": "Price range indicators ($ = budget, $$ = mid-range, $$$ = high-end, $$$$ = fine dining)",
                    },
                    "min_capacity": {
                        "type": "integer",
                        "description": "Minimum seating capacity required",
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_restaurants",
            "description": "Get restaurant recommendations based on user preferences and availability",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "Preferred location or area",
                    },
                    "cuisine": {
                        "type": "string",
                        "description": "Preferred cuisine type",
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "Number of people in the party",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date for the reservation (YYYY-MM-DD format)",
                    },
                    "time": {
                        "type": "string",
                        "description": "Time for the reservation (HH:MM format in 24-hour)",
                    },
                    "min_rating": {
                        "type": "number",
                        "description": "Minimum rating (1-5)",
                    },
                    "price_range": {
                        "type": "string",
                        "description": "Price range ($ = budget, $$ = mid-range, $$$ = high-end, $$$$ = fine dining)",
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check if a specific restaurant has availability for a given date, time, and party size",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_id": {
                        "type": "integer",
                        "description": "ID of the restaurant",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date for the reservation (YYYY-MM-DD format)",
                    },
                    "time": {
                        "type": "string",
                        "description": "Time for the reservation (HH:MM format in 24-hour)",
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "Number of people in the party",
                    }
                },
                "required": ["restaurant_id", "date", "time", "party_size"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_reservation",
            "description": "Create a new reservation at a restaurant",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "Full name of the customer",
                    },
                    "customer_email": {
                        "type": "string",
                        "description": "Email address of the customer",
                    },
                    "restaurant_id": {
                        "type": "integer",
                        "description": "ID of the restaurant",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date for the reservation (YYYY-MM-DD format)",
                    },
                    "time": {
                        "type": "string",
                        "description": "Time for the reservation (HH:MM format in 24-hour)",
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "Number of people in the party",
                    },
                    "special_requests": {
                        "type": "string",
                        "description": "Any special requests or notes for the reservation",
                    }
                },
                "required": ["customer_name", "customer_email", "restaurant_id", "date", "time", "party_size"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_reservation",
            "description": "Get details of a specific reservation by ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {
                        "type": "string",
                        "description": "Unique ID of the reservation",
                    }
                },
                "required": ["reservation_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_reservations_by_email",
            "description": "Get all reservations for a customer by email",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_email": {
                        "type": "string",
                        "description": "Email address of the customer",
                    }
                },
                "required": ["customer_email"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_reservation",
            "description": "Modify an existing reservation",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {
                        "type": "string",
                        "description": "ID of the reservation to modify",
                    },
                    "date": {
                        "type": "string",
                        "description": "New date for the reservation (YYYY-MM-DD format)",
                    },
                    "time": {
                        "type": "string",
                        "description": "New time for the reservation (HH:MM format in 24-hour)",
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "New number of people in the party",
                    },
                    "restaurant_id": {
                        "type": "integer",
                        "description": "ID of a new restaurant (if changing location)",
                    },
                    "special_requests": {
                        "type": "string",
                        "description": "Updated special requests",
                    }
                },
                "required": ["reservation_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reservation",
            "description": "Cancel an existing reservation",
            "parameters": {
                "type": "object",
                "properties": {
                    "reservation_id": {
                        "type": "string",
                        "description": "ID of the reservation to cancel",
                    }
                },
                "required": ["reservation_id"]
            }
        }
    }
]


class LLMAgent:
    def __init__(self, db_instance, api_key=None):
        """
        Initialize the LLM Agent for restaurant reservations
        
        Args:
            db_instance: An instance of the RestaurantDatabase class
            api_key: API key (optional if set in environment)
            model: LLM model to use
        """
        self.db = db_instance
        self.model = "openai/gpt-4.1"
        # Use environment variable instead of hardcoding API key
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("GITHUB_TOKEN")

        self.client = OpenAI(
            base_url="https://models.github.ai/inference",
            api_key=self.api_key
        )
        
        # Initialize conversation history
        self.conversation_history = []
        
        # System prompt to define agent behavior
        self.system_prompt = """You are an AI reservation assistant for FoodieSpot restaurants. 
You help customers make reservations, provide recommendations, modify or cancel bookings.
Always be polite, professional, and helpful. When making recommendations, consider the customer's 
preferences and suggest suitable restaurants.
If information is missing to complete a task, ask for it politely.
When dealing with reservations, always confirm the details with the customer.
Don't share information about reservations without verifying customer identity by email.
"""
    
    def handle_conversation(self, user_message: str) -> str:
        """
        Process a user message and generate a response
        
        Args:
            user_message: The message from the user
            
        Returns:
            str: Assistant's response
        """
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        try:
            # Prepare messages for the API call
            messages = [{"role": "system", "content": self.system_prompt}] + self.conversation_history
            
            # Call the API with tool definition
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            # Save the complete assistant message to history
            self.conversation_history.append(assistant_message.model_dump())
            
            # Check if the model wanted to call a function
            if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
                tool_responses = []
                
                for tool_call in assistant_message.tool_calls:
                    # Extract function name and arguments
                    function_name = tool_call.function.name
                    
                    # Add error handling for JSON parsing
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        error_response = {"error": "Failed to parse function arguments"}
                        tool_responses.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "content": json.dumps(error_response)
                        })
                        continue
                    
                    # Call the appropriate database function based on the tool called
                    tool_response = self._execute_tool(function_name, function_args)
                    
                    # Add tool response
                    tool_responses.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": json.dumps(tool_response)
                    })
                
                # Add all tool responses to the conversation history
                self.conversation_history.extend(tool_responses)
                
                # Get a new response from the model that incorporates the tool results
                second_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": self.system_prompt}] + self.conversation_history
                )
                
                # Add the final response to the conversation history
                final_message = second_response.choices[0].message
                self.conversation_history.append(final_message.model_dump())
                
                return final_message.content or ""

            # if no tool was called, just return the assistant response
            return assistant_message.content or ""
            
        except Exception as e:
            error_message = f"I apologize, but I encountered an error: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_message})
            return error_message
    
    def _execute_tool(self, function_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the appropriate function based on the tool called by the LLM
        
        Args:
            function_name: Name of the function to call
            args: Arguments to pass to the function
            
        Returns:
            Dict: Result of the function call
        """
        try:
            if function_name == "search_restaurants":
                return {"results": self.db.search_restaurants(**args)}
            
            elif function_name == "recommend_restaurants":
                return {"recommendations": self.db.recommend_restaurants(**args)}
            
            elif function_name == "check_availability":
                return self.db.get_available_tables(**args)
            
            elif function_name == "create_reservation":
                return self.db.create_reservation(**args)
            
            elif function_name == "get_reservation":
                reservation = self.db.get_reservation(args["reservation_id"])
                return {"reservation": reservation}
            
            elif function_name == "get_reservations_by_email":
                reservations = self.db.get_reservations_by_email(args["customer_email"])
                return {"reservations": reservations}
            
            elif function_name == "modify_reservation":
                reservation_id = args.pop("reservation_id")
                return self.db.modify_reservation(reservation_id, **args)
            
            elif function_name == "cancel_reservation":
                return self.db.cancel_reservation(args["reservation_id"])
            
            else:
                return {"error": f"Unknown function: {function_name}"}
                
        except Exception as e:
            return {"error": f"Error executing {function_name}: {str(e)}"}