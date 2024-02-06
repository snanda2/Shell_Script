import os

def list_text_files(directory):
    """List all text files in the given directory."""
    text_files = [f for f in os.listdir(directory) if f.lower().endswith('.txt')]
    return text_files

downloads_directory = r'C:\Users\admin\Downloads'  # Replace with the actual path to your Downloads directory

# Print all text files in the Downloads directory
print("\nAll Text Files in Downloads Directory:")
text_files_in_downloads = list_text_files(downloads_directory)

if text_files_in_downloads:
    for file in text_files_in_downloads:
        print(file)
else:
    print("No text files found in the Downloads directory.
