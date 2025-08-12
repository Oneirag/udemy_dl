import os
import httpx
import truststore
from dotenv import load_dotenv
load_dotenv()

# Inyecta certificados del sistema en el entorno SSL
truststore.inject_into_ssl()

# As a default, this value is 260 chars and chapter and lessons folders are adjusted to fit in this chars
# Use a different value if your system has no such restrictions
UDEMY_FOLDER_CHAR_LIMIT = os.getenv("UDEMY_FOLDER_CHAR_LIMIT", 260)

__full_cookie = os.getenv("UDEMY_COOKIE")
access_token = __full_cookie.split("access_token=")[1].split(";")[0]


cookies = {
    'access_token': access_token,
}

headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'}

client = httpx.Client(cookies=cookies, headers=headers)

