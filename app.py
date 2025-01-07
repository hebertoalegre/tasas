import re
import os
import cv2
import pytesseract
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from unidecode import unidecode


#####################################################################################################################
#                                                                                                                   #
#                                                  FUNCIONES AUXILIARES                                             #
#                                                                                                                   #
#####################################################################################################################

def fecha(f):
    '''
    Intenta parsear con el formato más específico las fechas correspondientes
    '''
    for fmt in ('%d%m%y', '%d%m%Y'):
        try:
            return datetime.strptime(f, fmt)
        except ValueError:
            continue  # Si falla, intenta el siguiente formato
    raise ValueError(f"No se pudo parsear la fecha: {f}")


# Patrón regex para dividir las líneas relevante e ignorar las que no
split_pattern = r'\s+(?=\S)'  
ignore_pattern = r'^[A-ZÁÉÍÓÚÑa-záéíóúñ\.\,\*\(\)\-\'\"\s]+$'

# Función para procesar cada línea
def process_line(line):
    line = unidecode(line).strip()
    if re.match(ignore_pattern, line):
        return [line]  
    else:
        return re.split(split_pattern, line)


#####################################################################################################################
#                                                                                                                   #
#                                              EXTRACCIÓN DE DATA DE PDFS                                           #
#                                                                                                                   #
#####################################################################################################################
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\heberto_alegre\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'


route = os.path.abspath('images')
files = os.listdir(route)

dfs = []
for file in tqdm(files):
    try:

        # Cargar la imagen en escala de grises
        img = cv2.imread(os.path.join(route, file), cv2.IMREAD_GRAYSCALE)

        n = 4
        height, width = img.shape
        new_width = int(width * n)  # nx el tamaño original en ancho
        new_height = int(height * n)  # nx el tamaño original en altura

        resized_image = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        blurred_image = cv2.GaussianBlur(resized_image, (5, 5), 1.5)

        # Aplicar un umbral
        ret, thresh = cv2.threshold(blurred_image, 127, 255, cv2.THRESH_BINARY)

        # find countors
        cnts = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]

        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.0135 * peri, True)
            area = cv2.contourArea(c)
            if len(approx) == 4 and area > 1000:
                x,y,w,h = cv2.boundingRect(c)
                ROI = 255 - img[y:y+h,x:x+w]
                img[y:y+h, x:x+w] = ROI


        result =thresh.copy()
        #basics input to remove lines 
        thresh_lines = cv2.Canny(blurred_image, 0, 255)


        # Remove horizontal lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (120,1))
        remove_horizontal = cv2.morphologyEx(thresh_lines, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
        cnts = cv2.findContours(remove_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        for c in cnts:
            cv2.drawContours(result, [c], -1, (255,255,255), 25)

        # Remove vertical lines
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,120))
        remove_vertical = cv2.morphologyEx(thresh_lines, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
        cnts = cv2.findContours(remove_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        for c in cnts:
            cv2.drawContours(result, [c], -1, (255,255,255), 25)

        # Mostrar la imagen umbralizada
        # cv2.imwrite('thresholded_image.jpg', result)

        config = '-l spa --oem 1 --psm 6'      
        text = pytesseract.image_to_string(result, config=config).replace('_', '-').replace('|', '').replace('"', '-').replace('!','-').replace(':', '').replace(']','').split('\n')

        # Texto parcial que buscamos
        start_phrase = 'SUBASTA DE DEPOSITOS A PLAZO, POR FECHA DE VENCIMIENTO, EN QUETZALES'
        end_phrase = 'Para consulta de precios ver cuadro'

        data = []
        for line in text:
            line = re.sub('\s+', ' ', line)
            result = process_line(line)
            data.append(result)


        start_index = next((i for i, item in enumerate(data) if any(start_phrase in str(x) for x in item)), None)
        end_index = next((i for i, item in enumerate(data) if any(end_phrase in str(x) for x in item)), None)

        selected_data = pd.DataFrame(data[start_index+3:end_index-1])
        selected_data['fecha'] = fecha(file.split('_')[0])

        dfs.append(selected_data)
    except:
        print(f'Error en el archivo {file}')
        continue

df = pd.concat(dfs, axis=0)
print(df)    
df.to_excel('data_tasas.xlsx', index=False)
