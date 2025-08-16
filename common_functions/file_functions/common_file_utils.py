import os

def get_folder_path_and_filename(file_path):
    """
    Get the folder path and filename from a given file path.
    Works across Mac, Windows, and Linux by normalizing path separators.
    
    Args:
        file_path (str): The file path to process
        
    Returns:
        tuple: (folder_path, filename) where:
            - folder_path (str): The directory path without the filename
            - filename (str): The filename extracted from the path
            
    Examples:
        >>> get_folder_path_and_filename("/path/to/file.txt")
        ('/path/to', 'file.txt')
        
        >>> get_folder_path_and_filename("C:\\Users\\user\\file.txt")
        ('C:\\Users\\user', 'file.txt')
        
        >>> get_folder_path_and_filename("file.txt")
        ('', 'file.txt')
    """
    if not file_path or not isinstance(file_path, str):
        return '', ''
    
    # Normalize path separators for cross-platform compatibility
    # Convert backslashes to forward slashes for consistent processing
    normalized_path = file_path.replace('\\', '/')
    
    # Remove trailing slash if present
    if normalized_path.endswith('/'):
        normalized_path = normalized_path.rstrip('/')
    
    # Split the path to get folder and filename
    if '/' in normalized_path:
        # Split on the last occurrence of '/'
        parts = normalized_path.rsplit('/', 1)
        folder_path = parts[0] if parts[0] else '/'
        filename = parts[1] if len(parts) > 1 else ''
    else:
        # No path separators found, treat as filename only
        folder_path = ''
        filename = normalized_path
    
    # Convert back to original path separator style for folder_path
    if os.name == 'nt':  # Windows
        folder_path = folder_path.replace('/', '\\')
    
    return folder_path, filename


def get_folder_path(file_path):
    """
    Get only the folder path from a given file path.
    
    Args:
        file_path (str): The file path to process
        
    Returns:
        str: The directory path without the filename
    """
    folder_path, _ = get_folder_path_and_filename(file_path)
    return folder_path


def get_filename_only(file_path):
    """
    Get only the filename from a given file path.
    
    Args:
        file_path (str): The file path to process
        
    Returns:
        str: The filename extracted from the path
    """
    _, filename = get_folder_path_and_filename(file_path)
    return filename