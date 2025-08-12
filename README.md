                                            # Simple script to download udemy course materiales

## Prerequisites
### Create a .env file
Login to any udemy course in your browser, open developer tools, look for a "Fetch/XHR" request, get contents of "Cookie"
and paste it in the `UDEMY_COOKIE` field.

Set your destination folder in the `UDEMY_DESTINATION_FOLDER`
```bash
# Folder where files will be finally written. If it is a onedrive folder, synchronization problems might
# occur so it first downloaded into a temporary folder and then copied to the final location
UDEMY_DESTINATION_FOLDER=
# Get cookie from the "Cookie" request headers of any Fetch/XHR request in developer tools of a browser with a logged in udemy course
UDEMY_COOKIE = '__stripe_mid=your_cookie_goes_here'
# As a default, this value is 260 chars and chapter and lessons folders are adjusted to fit in this chars
# Use a different value if your system has no such restrictions
UDEMY_FOLDER_CHAR_LIMIT=260
```
### Create a config.yaml file
Create a list of courses to download, grouped by topics (each course will be downloaded to a subfolder topic under the destination folder),
like this:
```yaml
Algo:
    - your udemy link would come here
    - another link such as  https://www.udemy.com/course/name-of-the-course/
Data:
  -
Python:
  -
Modelos:
  -
```


## Run __main__.py
Will download all resource files in the destination folder and will also create a contents.json with the course
structure. 

The program is meant to run in Windows OS with limited chars on folder length (260chars).

**Note**: files are first downloaded to a temp folder and moved later to the destination folder.