import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
import shutil

import yaml
from fake_useragent import UserAgent
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from udemy_dl import client, cookies, headers, httpx
from udemy_dl.windows import nombre_carpeta_valido, CourseFolderStructure, find_config_file


class UdemyLesson(BaseModel):
    lesson_name: str
    description: Optional[str] = None
    body: Optional[str] = None


class UdemyChapter(BaseModel):
    chapter_name: str
    description: str | None
    contents: List[UdemyLesson] = []


class UdemyCourse(BaseModel):
    course_name: str
    chapters: List[UdemyChapter] = []


class UdemyDownloader:
    API_BASE = "https://www.udemy.com/api-2.0"

    def __init__(self, course_url: str):
        """Inits downloader with the course url"""
        self.random_ua = UserAgent(os="Windows").random
        parsed = urlparse(course_url)
        self.course_url = course_url
        self.course_name = parsed.path.split("/")[2]
        self.course_id = self.get_course_id()
        self.destination = None
        self.temp_destination = None
        self.numbered_chapter_name = None
        self.numbered_lesson_name = None
        self.current_dest_dir = None
        self.folder_structure = None
        self.course_structure = None
        # Folder por temporary downloads
        self.temp_destination = None

    # Reintenta hasta 5 veces, con espera exponencial entre intentos
    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    def get_course_id(self) -> int:
        """Reads course id from one of the requests of the main course URL"""
        response = httpx.get(
            self.course_url,
            headers={
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'user-agent': self.random_ua,
                "User-Agent": self.random_ua
            },
            cookies={},
            follow_redirects=True
        )
        response.raise_for_status()
        content = response.text
        match = re.search(r'<meta property="og:image" content="https://img-c\.udemycdn\.com/course/[^/]+/(\d+)_',
                          content)
        if match:
            course_id = int(match.group(1))
            return course_id
        raise ValueError(f"Course could not be found: {self.course_url}")

    # Reintenta hasta 10 veces, con espera exponencial entre intentos
    @retry(
        stop=stop_after_attempt(10),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    def get_js(self, url_path: str, params: dict, **kwargs) -> dict:

        response = client.get(
            # f'{self.API_BASE}/courses/{course_id}/subscriber-curriculum-items/?curriculum_types=chapter,lecture,practice,quiz,role-play&page_size=200&fields[lecture]=title,object_index,is_published,sort_order,created,asset,supplementary_assets,is_free&fields[quiz]=title,object_index,is_published,sort_order,type&fields[practice]=title,object_index,is_published,sort_order&fields[chapter]=title,object_index,is_published,sort_order&fields[asset]=title,filename,asset_type,status,time_estimation,is_external,download_urls&caching_intent=True',
            self.API_BASE + url_path,
            params=params,
            cookies=kwargs.pop("cookies", cookies),
            headers=kwargs.pop("headers", headers),
            **kwargs
        )
        response.raise_for_status()
        js = response.json()
        return js

    def download_materials(self, destination: str | Path):
        destination = Path(destination)
        with tempfile.TemporaryDirectory() as temp_path:
            temp_destination = Path(temp_path)
            print(f"Descargando {self.course_name} en carpeta temporal: {temp_destination}")

            self.course_structure = UdemyCourse(course_name=self.course_name)

            self.folder_structure = CourseFolderStructure(destination, temp_destination)
            idx_course = 0
            self.folder_structure.set_course_title(idx_course, self.course_name)

            ### Gets information on all the lectures, quizs, practices, chapters and assets of the course
            js = self.get_js(
                f"/courses/{self.course_id}/subscriber-curriculum-items/",
                params={
                    # 'curriculum_types': 'chapter,lecture,practice,quiz,role-play',
                    # Ignore quizzes
                    'curriculum_types': 'chapter,lecture,practice,role-play',
                    'page_size': 200,
                    'fields[lecture]': 'title,object_index,is_published,sort_order,created,asset,supplementary_assets,is_free',
                    'fields[quiz]': 'title,object_index,is_published,sort_order,type',
                    'fields[practice]': 'title,object_index,is_published,sort_order',
                    'fields[chapter]': 'title,object_index,is_published,sort_order',
                    'fields[asset]': 'title,filename,asset_type,status,time_estimation,is_external,download_urls',
                    'caching_intent': 'True'
                }
            )
            idx_chapter = 0
            idx_lesson = 0
            for lesson in js['results']:
                title = lesson['title']
                description = lesson.get("description")
                if lesson['_class'] == "chapter":
                    idx_chapter += 1
                    chapter_name = nombre_carpeta_valido(title)
                    # print(chapter_name)
                    numbered_chapter_name = f"{idx_chapter:03} - {chapter_name}"
                    self.folder_structure.set_lesson_title(idx_course, idx_chapter, numbered_chapter_name)
                    self.course_structure.chapters.append(UdemyChapter(chapter_name=chapter_name, description=description))
                    idx_lesson = 0
                    continue
                idx_lesson += 1
                lesson_title = nombre_carpeta_valido(title)
                numbered_lesson_name = f"{idx_lesson:02} - {lesson_title}"
                self.folder_structure.set_content_title(idx_course, idx_chapter, idx_lesson, numbered_lesson_name)
                self.course_structure.chapters[-1].contents.append(UdemyLesson(lesson_name=title))
                lecture_id = lesson['id']
                asset_js = self.get_js(
                    f"/users/me/subscribed-courses/{self.course_id}/lectures/{lecture_id}/",
                    params={
                        "fields[lecture]": "asset,description,download_url,is_free,last_watched_second",
                        "fields[asset]": "asset_type,length,media_license_token,course_is_drmed,media_sources,captions,thumbnail_sprite,slides,slide_urls,download_urls,external_url,body",
                        # "q": 0.10664847299098668
                    }
                )
                if description := asset_js['description']:
                    self.course_structure.chapters[-1].contents[-1].description = description
                    print(description)

                if asset := lesson.get('asset'):
                    # Only articles have a body
                    if asset['asset_type'] == "Article":
                        asset_id = asset['id']
                        asset_body_js = self.get_js(
                            f"/assets/{asset_id}/",
                            params={
                                "fields[asset]": "@min,status,delayed_asset_message,processing_errors,body",
                                "course_id": self.course_id,
                                "lecture_id": lecture_id}
                        )
                        if body := asset_body_js.get("body"):
                            self.course_structure.chapters[-1].contents[-1].body = body
                            # self.folder_structure.write(idx_course, idx_chapter, idx_lesson, "body.html", body)
                            # print(body)

                # Now let's get the additional resources (downloadable)
                if supplementary_assets := lesson.get('supplementary_assets'):
                    for asset in supplementary_assets:
                        asset_type = asset['asset_type']
                        if not (download_urls := asset.get("download_urls")):
                            continue
                        url = download_urls[asset_type][0]
                        if file := url.get("file"):
                            filename = asset['filename']
                            print(lesson_title, filename, url['file'])
                            dl = client.get(url['file'], cookies=cookies, headers=headers)
                            dl.raise_for_status()
                            self.folder_structure.write(idx_course, idx_chapter, idx_lesson, filename, dl.content)
                            # self.write_bytes(filename, dl.content)
                            # (self.get_dest_dir() / filename).write_bytes(dl.content)
            self.folder_structure.write(idx_course, None, None, "contents.json",
                                        self.course_structure.model_dump_json(indent=4, exclude_none=True))

            # Moverlo todo a la carpeta de destino final

            # Asegurar que la carpeta de destino existe
            destination.mkdir(parents=True, exist_ok=True)

            # Mover todo el contenido de la carpeta temporal al destino
            for item in temp_destination.rglob("*"):
                if item.is_file():
                    destino_final = destination / item.relative_to(temp_destination)
                    destino_final.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(destino_final))
                    print(f"Movido a {destino_final}")


if __name__ == '__main__':
    destination = os.getenv("UDEMY_DESTINATION_FOLDER")
    config_file = find_config_file("config.yaml")
    if not config_file:
        raise FileNotFoundError("File 'config.yaml' not found")

    config = yaml.safe_load(config_file.read_text())

    for topic, urls in config.items():
        destination_folder = Path(destination) / topic
        for url in urls:
            if not url:
                continue
            # print(UdemyDownloader(url).get_course_id())
            downloader = UdemyDownloader(url)
            downloader.download_materials(destination_folder)
