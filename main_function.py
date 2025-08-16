import json
from datetime import datetime
from test_config import test_run_config
from common_functions.file_functions.excel_operations import multi_sheet_excel_reader
# from common_functions.db_service.mysql_db_service import my_sql_databasefrom common_functions.aws_service.aws_common_function import (s3_operations_manager)


from common_functions.utils.logging_config import logger




### Excel Operations ###
def read_source_tc_file(file_path):
    # Read the Excel file
    excel_data = multi_sheet_excel_reader(file_path)
    
    # # Convert all values to strings in each sheet's DataFrame
    # for sheet_name in excel_data:
    #     excel_data[sheet_name] = excel_data[sheet_name].astype(str)
    
    return excel_data


def get_tc_data_from_excel(excel_data, tc_master_column_data, tc_sheet_name):

    tc_master_data = excel_data[tc_sheet_name]

    #drop the rows where to_process is     
    tc_master_data = tc_master_data[tc_master_data['to_process'] == 'Yes']

    tc_meta_columns = tc_master_column_data

    tc_modify_data_columns = [
        col for col in tc_master_data.columns if col not in tc_meta_columns
    ]

    # Transform each row into the desired JSON structure
    json_data = []
    for _, row in tc_master_data.iterrows():
        test_case_id = row['test_case_id']
        tc_meta = {col: row[col] for col in tc_meta_columns if col in row}
        tc_modify_data = {col: row[col] for col in tc_modify_data_columns if col in row}
        
        # Filter out keys where the value is "nan"
        tc_modify_data = {key: value for key, value in tc_modify_data.items() if value != "nan"}

        # Create the JSON structure
        json_row = {
            "test_case_id": test_case_id,
            "tc_meta": [tc_meta],
            "tc_modify_data": [tc_modify_data]
        }

        # Format the JSON with indent=4
        # formatted_json_row = json.dumps(json_row, indent=4)
        # formatted_json_row = json.dumps(json_row)

        # formatted_json_row = json_row

        json_data.append(json_row)
        
    final_tc_json_data = json_data

    return final_tc_json_data


def get_default_payload_from_excel(excel_data, sheet_name):
    # Extract providers field data from the Excel sheets
    
    if sheet_name == "default_payload":
    
        default_payload_sheet_data = excel_data[sheet_name]
    
    elif sheet_name == "platform_api_default_payload":

        default_payload_sheet_data = excel_data[sheet_name]
    
    else:
        logger.error(f" Sheet name --> {sheet_name} is not found")

    return default_payload_sheet_data.to_dict('records')



def get_default_payload_by_api_name(api_name, excel_data, sheet_name):

    default_payload_data = get_default_payload_from_excel(excel_data, sheet_name)
        
    if sheet_name == "platform_api_default_payload" or sheet_name == "default_payload":
        try:
            default_payload = next(payload for payload in default_payload_data 
                                if payload['api_name'] == api_name and payload['environment'] == test_run_config["environment"])
        except StopIteration:
            raise ValueError(f"API name '{api_name}' not found in the default payload data for sheet '{sheet_name}'")
    else:
        logger.error(f" Sheet name --> {sheet_name} is not found")

    return default_payload


# new_data_str is the new data to be updated in the temp_data_str
def update_json_data_with_new_json(new_data_str, temp_data_str):
    # new_data_str is the new data to be updated in the temp_data_str
    
    # Convert string inputs to Python dictionaries
    # Ensure New_data and Temp_data are dictionaries
    # if isinstance(new_data_str, str):
    #     new_data = json.loads(new_data_str.strip('"'))
    # if isinstance(temp_data_str, str):
    #     temp_data = json.loads(temp_data_str.strip('"'))

    def set_nested_value(d, key_path, value):
        # Handle bracket notation by removing brackets and splitting
        keys = key_path.replace('][', ' ').replace('[', '').replace(']', '').split()
        
        current = d
        # Navigate through existing structure
        for key in keys[:-1]:
            if key in current:
                current = current[key]
            else:
                logger.info(f"Warning: Key path '{key_path}' not found in the dictionary structure")
                return
        # Update the value at the final level
        if keys[-1] in current:
            current[keys[-1]] = value
        else:
            logger.info(f"Warning: Final key '{keys[-1]}' not found in the dictionary structure")

    # Update Temp_data with New_data values
    for key, value in new_data_str.items():
        if '[' in key and ']' in key:
            # Handle nested dictionary access
            if "input_data" in temp_data_str:
                set_nested_value(temp_data_str["input_data"], key, value)
            elif "data" in temp_data_str:
                set_nested_value(temp_data_str["data"], key, value)
            else:
                set_nested_value(temp_data_str, key, value)
        else:
            # Original logic for non-nested keys
            if key in temp_data_str:
                # If the key is at the top level, replace its value
                temp_data_str[key] = value
            elif "input_data" in temp_data_str and key in temp_data_str["input_data"]:  # this input key is for currier_int curd  api
                # If the key is nested in "input_data", replace its value
                temp_data_str["input_data"][key] = value
            elif "data" in temp_data_str and key in temp_data_str["data"]: # this input key is for platform  api (places )
                # If the key is nested in "data", replace its value
                temp_data_str["data"][key] = value
            else:
                # Log if the key is not found in Temp_data
                logger.info(f"Warning --> Iam update_json_data_with_new_json function: Key '{key}' from New_data is not available in Temp_data")
    
    return temp_data_str

    # # Example usage
    # New_data = '"{"provider_id": 1177, "username": "PPPP", "password": "384783", "env": "QA", "AA":"23"}"'
    # Temp_data = '"{"supports": "RATES", "source": "INTEGRATION", "mode": "FTL", "leg": "", "provider_type": "SUBVENDOR", "provider_id": 1177, "input_data": {"username": "ejgdjnked", "password": "ekmsmvksmdkv", "type": "export", "env": "production"}}"' 

    # updated_data = update_json_data_with_new_json(New_data, Temp_data)

    # # Print the updated Temp_data
    # print(json.dumps(updated_data, indent=4))


def new_update_json_data_with_new_json(new_data_str, temp_data_str):
    """
    Updates a nested JSON object (`temp_data_str`) with values from another JSON object (`new_data_str`).
    Supports nested keys in bracket notation (e.g., "key1[key2][key3]").

    Args:
        new_data_str (dict): Dictionary containing updates in key-value pairs.
        temp_data_str (dict): Target dictionary to be updated.

    Returns:
        dict: Updated dictionary.
    """

    def set_nested_value(data, key_path, value):
        """
        Navigates to a nested key in a dictionary (or list) using bracket notation
        and sets its value, creating intermediate levels as needed.
        """
        keys = key_path.replace('][', '.').replace('[', '.').replace(']', '').split('.')
        current = data

        for i, key in enumerate(keys[:-1]):
            if key.isdigit():
                # Handle numeric keys for lists
                key = int(key)
                if not isinstance(current, list):
                    raise TypeError(f"Expected list at '{keys[:i]}' but found {type(current)}.")
                while len(current) <= key:
                    current.append({})
            else:
                # Ensure intermediate keys exist as dictionaries
                if key not in current:
                    current[key] = {}
            current = current[key]

        # Set the final value
        last_key = keys[-1]
        if last_key.isdigit():
            last_key = int(last_key)
            if not isinstance(current, list):
                raise TypeError(f"Expected list at '{keys}' but found {type(current)}.")
            while len(current) <= last_key:
                current.append({})
            current[last_key] = value
        else:
            current[last_key] = value

    # Iterate through each key-value pair in new_data_str
    for key, value in new_data_str.items():
        try:
            set_nested_value(temp_data_str, key, value)
        except Exception as e:
            print(f"Error updating key '{key}': {e}")

    return temp_data_str



