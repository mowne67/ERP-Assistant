from langchain_core.messages import AIMessage
import json

def delete(state):
    attribute = state['delete_attribute']
    values = state['delete_value']  # This can be a single value or a list of values

    # Ensure values is always a list for consistent processing
    if not isinstance(values, list):
        values = [values]

    # Convert all values to the appropriate type (e.g., int if needed)
    try:
        values = [int(value) if isinstance(value, str) and value.isdigit() else value for value in values]
    except Exception as e:
        return {'messages': AIMessage(content=f"Error processing delete values: {str(e)}")}

    # Define the unique key for each schema
    if state['output_schema'] == 'user':
        json_file_path = r'users.json'
        unique_key = 'id'
    elif state['output_schema'] == 'customer':
        json_file_path = r'customers.json'
        unique_key = 'id'
    elif state['output_schema'] == 'office':
        json_file_path = r'offices.json'
        unique_key = 'id'
    else:
        return {'messages': AIMessage(content="Invalid schema type provided.")}

    # Ensure deletion is only allowed based on the unique key
    if attribute != unique_key:
        return {'messages': AIMessage(content=f"Deletion can only be performed using the unique key '{unique_key}' for {state['output_schema']} schema.")}

    try:
        # Load the existing data from the JSON file
        with open(json_file_path, 'r') as file:
            data = json.load(file)

        # Filter out the entries that match any of the values in the list
        filtered_data = [entry for entry in data if entry.get(unique_key) not in values]

        # Check if any entries were deleted
        deleted_count = len(data) - len(filtered_data)
        if deleted_count == 0:
            # No entries were deleted, meaning none of the unique key-value pairs exist
            return {'messages': AIMessage(content=f"No {state['output_schema']} found with {unique_key} in {values} in the database.")}

        # Write the updated data back to the JSON file
        with open(json_file_path, 'w') as file:
            json.dump(filtered_data, file, indent=4)

        # Return success message
        return {'messages': AIMessage(content=f"Successfully deleted {deleted_count} {state['output_schema']}(s) with {unique_key} in {values} from the database.")}

    except Exception as e:
        # Handle any unexpected errors
        return {'messages': AIMessage(content=f"An error occurred while deleting: {str(e)}")}