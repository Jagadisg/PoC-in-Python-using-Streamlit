import os
from loguru import logger

async def filepath_name(uploaded_file=None,folder_path='uploads',filename=None):
    
    if not os.path.exists(folder_path):        
        logger.info("filepathname")
        os.makedirs(folder_path)
    if uploaded_file:
        filename = uploaded_file.name
        print(filename)
    save_path = os.path.join(folder_path, filename)        
    return save_path

async def create_directory():
    current_directory = os.getcwd()
    new_directory_path = os.path.join(current_directory, 'uploads')
    if not os.path.exists(new_directory_path):
        try:
            os.mkdir(new_directory_path)
            print(f"Directory '{new_directory_path}' created successfully.")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        print(f"Directory '{new_directory_path}' already exists.")


if __name__ == "__main__":    
    pass