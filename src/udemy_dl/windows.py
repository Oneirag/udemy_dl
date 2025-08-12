import re
from pathlib import Path
from udemy_dl import UDEMY_FOLDER_CHAR_LIMIT


def find_config_file(filename="config.yaml"):
    current_dir = Path.cwd()

    for parent in [current_dir] + list(current_dir.parents):
        potential_path = parent / filename
        if potential_path.is_file():
            return potential_path

    return None


def nombre_carpeta_valido(texto):
    """Eliminar caracteres no válidos para nombres de carpeta en Windows"""
    texto_limpio = re.sub(r'[<>:"/\\|?*]', '', texto)

    # Eliminar caracteres de control (ASCII 0-31)
    texto_limpio = re.sub(r'[\x00-\x1F]', '', texto_limpio)

    # Eliminar puntos al final (no válidos en nombres de carpeta)
    texto_limpio = texto_limpio.rstrip('. ')
    # Eliminar comas al final (no válidas en nombres de carpeta)
    texto_limpio = texto_limpio.rstrip(', ')

    texto_limpio = texto_limpio.strip()
    # Limitar a 128 caracteres
    texto_limpio = texto_limpio[:128]

    return texto_limpio

class CourseFolderStructure:
    def __init__(self, base_folder, temp_folder):
        self.base_folder = Path(base_folder)
        self.temp_folder = Path(temp_folder)
        self.adjust_len = max(0, len(str(base_folder)) - len(str(self.temp_folder)))
        self.current_course_name = None
        self.current_lesson_name = None
        self.current_content_name = None
        self.current_course_idx = None
        self.current_lesson_idx = None
        self.current_content_idx = None
        self.filename = None

    def get_course_folder(self) -> Path:
        return self.temp_folder / self.current_course_name

    def get_lesson_folder(self) -> Path:
        return self.get_course_folder() / self.current_lesson_name

    def get_content_folder(self) -> Path:
        return self.get_lesson_folder() / self.current_content_name

    def set_course_title(self, idx_course: int, course_name: str):
        idx = (idx_course,)
        valid_folder_name = nombre_carpeta_valido(course_name)
        if self.current_course_idx != idx:
            self.current_course_name = valid_folder_name
            self.current_course_idx = idx
            # self.__get_course_folder().mkdir(parents=True, exist_ok=True)
        if (self.get_course_folder().name != valid_folder_name and
                self.get_course_folder().exists() and
                not self.get_course_folder().with_name(valid_folder_name).exists()):
            self.get_course_folder().rename(self.get_course_folder().with_name(valid_folder_name))
        self.current_course_name = valid_folder_name

    def set_lesson_title(self, idx_course: int, idx_lesson: int, lesson_name: str):
        idx = (idx_course, idx_lesson)
        valid_folder_name = nombre_carpeta_valido(lesson_name)
        if self.current_lesson_idx != idx:
            self.current_lesson_name = valid_folder_name
            self.current_lesson_idx = idx
            # self.__get_lesson_folder().mkdir(parents=True, exist_ok=True)
        if (self.get_lesson_folder().name != valid_folder_name and
                self.get_lesson_folder().exists() and
                not self.get_lesson_folder().with_name(valid_folder_name).exists()):
            self.get_lesson_folder().rename(self.get_lesson_folder().with_name(valid_folder_name))
        self.current_lesson_name = valid_folder_name

    def set_content_title(self, idx_course: int, idx_lesson: int, idx_content: int, content_name: str):
        idx = (idx_course, idx_lesson, idx_content)
        valid_folder_name = nombre_carpeta_valido(content_name)
        if self.current_content_idx != idx:
            self.current_content_name = valid_folder_name
            self.current_content_idx = idx
            # self.__get_content_folder().mkdir(parents=True, exist_ok=True)
        if (self.get_content_folder().name != valid_folder_name and
                self.get_content_folder().exists() and
                not self.get_content_folder().with_name(valid_folder_name).exists()):
            self.get_content_folder().rename(self.get_content_folder().with_name(valid_folder_name))
        self.current_content_name = valid_folder_name

    def ajustar_y_renombrar_ruta(self, idx_curso: int, idx_lesson: int, idx_content: int,
                                 nombre_archivo: str, max_length=UDEMY_FOLDER_CHAR_LIMIT) -> Path:
        """Devuelve solo la ruta a la carpeta actual, sin el fichero. real_base_path_len es la longitud real de la carpeta
        final de destino, para ajustarla bien si se descarga en una temporal"""

        def recortar(texto, longitud):
            return nombre_carpeta_valido(texto[:max(1, longitud)])

        longitud_fija = len(self.base_folder.as_posix()) + len(nombre_archivo) + 2 + self.adjust_len
        espacio_disponible = max_length - longitud_fija

        # Recorte inicial proporcional
        mitad = espacio_disponible // 3
        carpeta_curso_recortada = recortar(self.current_course_name, mitad)
        carpeta_leccion_recortada = recortar(self.current_lesson_name, mitad)
        carpeta_contenido_recortada = recortar(self.current_content_name, mitad)

        def ruta_actual():
            return str(
                self.temp_folder / carpeta_curso_recortada / carpeta_leccion_recortada / carpeta_contenido_recortada)

        MIN_FOLDER_LEN = 3  # Tamaño minimo de las carpetas
        # Ajuste fino: recortar empezando por el nombre más largo
        while (len(ruta_actual()) + self.adjust_len) > max_length:
            longitudes = {
                'curso': len(carpeta_curso_recortada),
                'leccion': len(carpeta_leccion_recortada),
                'contenido': len(carpeta_contenido_recortada)
            }
            carpeta_mas_larga = max(longitudes, key=longitudes.get)

            if carpeta_mas_larga == 'curso' and len(carpeta_curso_recortada) > MIN_FOLDER_LEN:
                carpeta_curso_recortada = nombre_carpeta_valido(carpeta_curso_recortada[:-1])
            elif carpeta_mas_larga == 'leccion' and len(carpeta_leccion_recortada) > MIN_FOLDER_LEN:
                carpeta_leccion_recortada = nombre_carpeta_valido(carpeta_leccion_recortada[:-1])
            elif carpeta_mas_larga == 'contenido' and len(carpeta_contenido_recortada) > MIN_FOLDER_LEN:
                carpeta_contenido_recortada = nombre_carpeta_valido(carpeta_contenido_recortada[:-1])
            else:
                break  # No se puede recortar más

        nueva_ruta_final = Path(ruta_actual())
        self.set_course_title(idx_curso, carpeta_curso_recortada)
        self.set_lesson_title(idx_curso, idx_lesson, carpeta_leccion_recortada)
        self.set_content_title(idx_curso, idx_lesson, idx_content, carpeta_contenido_recortada)
        return nueva_ruta_final

    def write(self, idx_curso: int, idx_lesson, idx_content, filename: str, data_or_text):
        if idx_lesson is None and idx_content is None:
            new_folder = self.get_course_folder()
        else:
            new_folder = self.ajustar_y_renombrar_ruta(idx_curso, idx_lesson, idx_content, filename)
        if not new_folder.exists():
            new_folder.mkdir(exist_ok=True, parents=True)
        if isinstance(data_or_text, str):
            (new_folder / filename).write_text(data_or_text)
        else:
            (new_folder / filename).write_bytes(data_or_text)


