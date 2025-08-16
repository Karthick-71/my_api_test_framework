import os
import pandas as pd


def multi_sheet_excel_reader(file_path):
    excel_file = pd.ExcelFile(file_path)
    sheets_dict = {}
    for sheet_name in excel_file.sheet_names:
        # Read the sheet and convert all columns to string type immediately
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        sheets_dict[sheet_name] = df.astype(str)
    return sheets_dict


def save_dataframe_to_csv(df, file_path):
    """Save a DataFrame to a CSV file, creating the directory if it doesn't exist."""
    # Get the directory from the file path
    directory = os.path.dirname(file_path)
    
    # Check if the directory exists, if not, create it
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Save the DataFrame to a CSV file
    df.to_csv(file_path, index=False)
    print(f"CSV file saved to this local_path: {file_path}")


def save_dataframe_to_excel(df, file_path):
    """Save a DataFrame to an Excel file, creating the directory if it doesn't exist."""
    # Get the directory from the file path
    directory = os.path.dirname(file_path)
    
    # Check if the directory exists, if not, create it
    if not os.path.exists(directory):
        os.makedirs(directory)
    
    # Save the DataFrame to an Excel file
    df.to_excel(file_path, index=False)
    print(f"File saved to {file_path}")
