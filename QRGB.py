from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image as KivyImage
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.widget import Widget
from PIL import Image
import qrcode
import os
import cv2
import webbrowser
import logging
import sys
from pathlib import Path

# Obtener la ruta base del ejecutable o script
if getattr(sys, 'frozen', False):
    # Si es un ejecutable
    BASE_PATH = os.path.dirname(sys.executable)
else:
    # Si es el script Python
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# Configurar carpetas
FOLDER_PATH = os.path.join(BASE_PATH, 'qrgb_files')
LOG_PATH = os.path.join(FOLDER_PATH, 'qrgb.log')

# Crear directorios necesarios
os.makedirs(FOLDER_PATH, exist_ok=True)

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_qr_with_logo(data, color, logo_path, qr_version=10, box_size=10):
    qr = qrcode.QRCode(
        version=qr_version,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=4
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color=color, back_color="white").convert('RGBA')

    if not os.path.exists(logo_path):
        raise FileNotFoundError(f"Logo file not found: {logo_path}")

    logo = Image.open(logo_path).convert("RGBA")
    basewidth = img.size[0] // 4
    wpercent = (basewidth / float(logo.size[0]))
    hsize = int((float(logo.size[1]) * float(wpercent)))
    logo = logo.resize((basewidth, hsize), Image.LANCZOS)

    pos = ((img.size[0] - logo.size[0]) // 2, (img.size[1] - logo.size[1]) // 2)
    img.paste(logo, pos, logo)

    return img

def combine_qr_images(img1, img2, img3, logo_path):
    size = img1.size
    if img2.size != size or img3.size != size:
        raise ValueError("All QR images must be the same size")

    final_image = Image.new("RGBA", size, "black")

    data_red = img1.getdata()
    data_green = img2.getdata()
    data_blue = img3.getdata()

    new_data = []
    for i in range(len(data_red)):
        r1, g1, b1, a1 = data_red[i]
        red_pixel = (r1, g1, b1) != (255, 255, 255)
        r2, g2, b2, a2 = data_green[i]
        green_pixel = (r2, g2, b2) != (255, 255, 255)
        r3, g3, b3, a3 = data_blue[i]
        blue_pixel = (r3, g3, b3) != (255, 255, 255)

        if red_pixel and green_pixel and blue_pixel:
            new_data.append((255, 255, 255, 255))
        elif red_pixel and green_pixel:
            new_data.append((255, 255, 0, 255))
        elif red_pixel and blue_pixel:
            new_data.append((255, 0, 255, 255))
        elif green_pixel and blue_pixel:
            new_data.append((0, 255, 255, 255))
        elif red_pixel:
            new_data.append((255, 0, 0, 255))
        elif green_pixel:
            new_data.append((0, 255, 0, 255))
        elif blue_pixel:
            new_data.append((0, 0, 255, 255))
        else:
            new_data.append((0, 0, 0, 255))

    final_image.putdata(new_data)

    logo = Image.open(logo_path).convert("RGBA")
    basewidth = final_image.size[0] // 4
    wpercent = (basewidth / float(logo.size[0]))
    hsize = int((float(logo.size[1]) * float(wpercent)))
    logo = logo.resize((basewidth, hsize), Image.LANCZOS)

    pos = ((final_image.size[0] - logo.size[0]) // 2, (final_image.size[1] - logo.size[1]) // 2)
    final_image.paste(logo, pos, logo)

    return final_image

def generate_qrgb(red_data, green_data, blue_data, logo_path, mode):
    qr_version = 10 if mode == 'link' else 3
    box_size = 10 if mode == 'link' else 20

    img_red = create_qr_with_logo(red_data, "red", logo_path, qr_version, box_size)
    img_green = create_qr_with_logo(green_data, "green", logo_path, qr_version, box_size)
    img_blue = create_qr_with_logo(blue_data, "blue", logo_path, qr_version, box_size)

    img_red.save(os.path.join(FOLDER_PATH, "qr_red.png"))
    img_green.save(os.path.join(FOLDER_PATH, "qr_green.png"))
    img_blue.save(os.path.join(FOLDER_PATH, "qr_blue.png"))

    combined_img = combine_qr_images(img_red, img_green, img_blue, logo_path)
    combined_img.save(os.path.join(FOLDER_PATH, "superposed_qr.png"))

    return combined_img

def read_qr(filename):
    img = cv2.imread(filename)
    detector = cv2.QRCodeDetector()
    data, vertices_array, _ = detector.detectAndDecode(img)
    if vertices_array is not None:
        return data
    else:
        return None

def manual_decode_superposed_qr(filename):
    superposed_img = Image.open(filename)
    superposed_data = superposed_img.getdata()

    size = superposed_img.size
    red_data = [(255, 255, 255, 255)] * len(superposed_data)
    green_data = [(255, 255, 255, 255)] * len(superposed_data)
    blue_data = [(255, 255, 255, 255)] * len(superposed_data)

    for i in range(len(superposed_data)):
        r, g, b, a = superposed_data[i]
        if r != 0:  # Red
            red_data[i] = (0, 0, 0, 255)
        if g != 0:  # Green
            green_data[i] = (0, 0, 0, 255)
        if b != 0:  # Blue
            blue_data[i] = (0, 0, 0, 255)

    red_img = Image.new("RGBA", size)
    green_img = Image.new("RGBA", size)
    blue_img = Image.new("RGBA", size)

    red_img.putdata(red_data)
    green_img.putdata(green_data)
    blue_img.putdata(blue_data)

    red_img.save(os.path.join(FOLDER_PATH, "decoded_red.png"))
    green_img.save(os.path.join(FOLDER_PATH, "decoded_green.png"))
    blue_img.save(os.path.join(FOLDER_PATH, "decoded_blue.png"))

    data_red = read_qr(os.path.join(FOLDER_PATH, "decoded_red.png"))
    data_green = read_qr(os.path.join(FOLDER_PATH, "decoded_green.png"))
    data_blue = read_qr(os.path.join(FOLDER_PATH, "decoded_blue.png"))

    return data_red, data_green, data_blue

class MainMenu(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10
        self.setup_ui()

    def setup_ui(self):
        # Título
        self.title = Label(
            text="Generador QRGB",
            font_size='24sp',
            size_hint_y=None,
            height=50
        )
        self.add_widget(self.title)
        
        # Botones principales
        buttons_layout = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=50,
            spacing=10
        )
        
        self.btn_encode = Button(
            text="Codificar QRGB",
            background_color=(0.2, 0.6, 1, 1)
        )
        self.btn_encode.bind(on_release=self.open_encode_menu)
        
        self.btn_decode = Button(
            text="Decodificar QRGB",
            background_color=(0.2, 0.8, 0.2, 1)
        )
        self.btn_decode.bind(on_release=self.decode_qr)
        
        buttons_layout.add_widget(self.btn_encode)
        buttons_layout.add_widget(self.btn_decode)
        self.add_widget(buttons_layout)

    def open_encode_menu(self, instance):
        self.clear_widgets()
        self.setup_encode_ui()

    def setup_encode_ui(self):
        self.add_widget(Label(
            text="Introduce el texto o link para cada capa de color:",
            size_hint_y=None,
            height=30
        ))
        
        self.red_input = TextInput(
            hint_text="Texto para capa roja",
            multiline=False,
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.red_input)

        self.green_input = TextInput(
            hint_text="Texto para capa verde",
            multiline=False,
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.green_input)

        self.blue_input = TextInput(
            hint_text="Texto para capa azul",
            multiline=False,
            size_hint_y=None,
            height=40
        )
        self.add_widget(self.blue_input)

        self.btn_select_logo = Button(
            text="Seleccionar Logo",
            size_hint_y=None,
            height=50,
            background_color=(0.8, 0.8, 0.8, 1)
        )
        self.btn_select_logo.bind(on_release=self.select_logo)
        self.add_widget(self.btn_select_logo)

        self.btn_generate = Button(
            text="Generar QRGB",
            size_hint_y=None,
            height=50,
            background_color=(0.2, 0.6, 1, 1)
        )
        self.btn_generate.bind(on_release=self.generate_qrgb)
        self.add_widget(self.btn_generate)

        self.btn_back = Button(
            text="Volver",
            size_hint_y=None,
            height=50,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        self.btn_back.bind(on_release=self.return_to_main)
        self.add_widget(self.btn_back)

    def return_to_main(self, instance):
        self.clear_widgets()
        self.setup_ui()

    def select_logo(self, instance):
        filechooser = FileChooserIconView(path=FOLDER_PATH)
        filechooser.filters = ['*.png', '*.jpg', '*.jpeg']
        filechooser.bind(on_submit=self.load_logo)
        self.popup = Popup(
            title="Selecciona el archivo de logo",
            content=filechooser,
            size_hint=(0.9, 0.9)
        )
        self.popup.open()

    def load_logo(self, filechooser, selection, *args):
        if selection:
            self.logo_path = selection[0]
            self.popup.dismiss()
            self.show_popup("Éxito", "Logo cargado correctamente")
        else:
            self.show_popup("Error", "No se seleccionó ningún archivo")

    def generate_qrgb(self, instance):
        if not hasattr(self, 'logo_path'):
            self.show_popup("Error", "Por favor, selecciona un archivo de logo")
            return

        red_data = self.red_input.text
        green_data = self.green_input.text
        blue_data = self.blue_input.text

        if not all([red_data, green_data, blue_data]):
            self.show_popup("Error", "Por favor, completa todos los campos de texto")
            return

        try:
            mode = 'link' if any('http' in text.lower() for text in [red_data, green_data, blue_data]) else 'text'
            combined_img = generate_qrgb(red_data, green_data, blue_data, self.logo_path, mode)
            combined_img.show()
            self.show_popup(
                "Éxito",
                f"QRGB generado correctamente\nGuardado en: {FOLDER_PATH}"
            )
        except Exception as e:
            logger.error(f"Error generating QRGB: {str(e)}")
            self.show_popup("Error", f"Error al generar QRGB: {str(e)}")

    def decode_qr(self, instance):
        filechooser = FileChooserIconView(path=FOLDER_PATH)
        filechooser.filters = ['*.png']
        filechooser.bind(on_submit=self.load_qrgb)
        self.popup = Popup(
            title="Selecciona el archivo QRGB",
            content=filechooser,
            size_hint=(0.9, 0.9)
        )
        self.popup.open()

    def load_qrgb(self, filechooser, selection, *args):
        if selection:
            try:
                data_red, data_green, data_blue = manual_decode_superposed_qr(selection[0])
                
                # Crear layout vertical para el contenido
                content = BoxLayout(orientation='vertical', padding=10, spacing=10)
                
                # Añadir la imagen del QR redimensionada
                qr_image = KivyImage(
                    source=selection[0],
                    size_hint=(None, None),
                    size=(200, 200),
                    allow_stretch=True
                )
                
                # Centrar la imagen
                image_container = BoxLayout(
                    size_hint_y=None, 
                    height=220,
                    orientation='horizontal'
                )
                image_container.add_widget(Widget())
                image_container.add_widget(qr_image)
                image_container.add_widget(Widget())
                
                content.add_widget(image_container)
                
                # Mostrar los datos decodificados con botones de URL
                text_container = BoxLayout(orientation='vertical', spacing=5)
                
                # Función para verificar y abrir URLs
                def is_valid_url(text):
                    return text and ('http://' in text.lower() or 'https://' in text.lower())
                
                def open_url(url):
                    if is_valid_url(url):
                        webbrowser.open(url)
                
                # Crear contenedores horizontales para cada capa
                for color, data in [("Roja", data_red), ("Verde", data_green), ("Azul", data_blue)]:
                    layer_container = BoxLayout(orientation='horizontal', spacing=5, size_hint_y=None, height=40)
                    layer_container.add_widget(Label(
                        text=f"Capa {color}: {data}",
                        size_hint_x=0.8,
                        text_size=(None, None),
                        halign='left'
                    ))
                    
                    if is_valid_url(data):
                        url_button = Button(
                            text="Ir URL",
                            size_hint_x=0.2,
                            background_color=(0.2, 0.6, 1, 1)
                        )
                        url_button.bind(on_release=lambda x, url=data: open_url(url))
                        layer_container.add_widget(url_button)
                    
                    text_container.add_widget(layer_container)
                
                content.add_widget(text_container)
                
                # Botón de cerrar
                btn_close = Button(
                    text="Cerrar",
                    size_hint=(1, 0.2),
                    background_color=(0.8, 0.8, 0.8, 1)
                )
                content.add_widget(btn_close)
                
                # Crear y mostrar el popup
                popup = Popup(
                    title="Resultado de Decodificación",
                    content=content,
                    size_hint=(0.8, 0.8)
                )
                btn_close.bind(on_release=popup.dismiss)
                
                self.popup.dismiss()
                popup.open()
                
            except Exception as e:
                self.show_popup("Error", f"Error al decodificar: {str(e)}")
        else:
            self.show_popup("Error", "No se seleccionó ningún archivo")

    def show_popup(self, title, message):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        label = Label(text=message)
        btn_close = Button(
            text="Cerrar",
            size_hint=(1, 0.5),
            background_color=(0.8, 0.8, 0.8, 1)
        )
        
        content.add_widget(label)
        content.add_widget(btn_close)
        
        if "http" in message.lower():
            btn_open_link = Button(
                text="Abrir enlace",
                size_hint=(1, 0.5),
                background_color=(0.2, 0.6, 1, 1)
            )
            btn_open_link.bind(on_release=lambda x: webbrowser.open(message))
            content.add_widget(btn_open_link)
        
        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.75, 0.5)
        )
        btn_close.bind(on_release=popup.dismiss)
        popup.open()

class QRGBApp(App):
    def build(self):
        Window.clearcolor = (1, 1, 1, 1)
        return MainMenu()

if __name__ == '__main__':
    QRGBApp().run()