import os


async def filepath_name(uploaded_file=None,folder_path='uploads',filename=None):
    
    if not os.path.exists(folder_path):        
        os.makedirs(folder_path)
    if uploaded_file:
        filename = uploaded_file.name
        print(filename)
    save_path = os.path.join(folder_path, filename)        
    return save_path


if __name__ == "__main__":    
    pass