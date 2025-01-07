import os
from scrapy import Spider, Request
from pdf2image import convert_from_path 

class tasas(Spider):
    '''
    clase para descarga de archivos pdf de las operaciones de estabilización monetaria historica y conversión a imagenes
    '''
    name = 'tasas'
    allowed_domains = ['banguat.gob.gt']
    start_urls = ['https://banguat.gob.gt/page/resultados-de-operaciones-de-estabilizacion-monetaria-historicos-1']

    def parse(self, response):

        # ruta de pdfs 
        urls = response.xpath('//div[@id="block-solucionweb-content"]/article/div/div/div/ul/li/a/@href').extract()
        
        for url in urls:
            url_absolute = response.urljoin(url)
        
            if url_absolute.endswith('.pdf'):
                yield Request(url = url_absolute, callback= self.save_pdf)
    
    def save_pdf(self, response):
        
        # crear carpeta si no existe
        pdf_folder = 'temporaly'

        if  not os.path.exists(pdf_folder):
            os.makedirs(pdf_folder)
        
        # Nombrar archivo y generar ruta de descarga, ademas guarda archivo
        pdf_name = response.url.split('/')[-1]
        pdf_path = os.path.join(pdf_folder, pdf_name)

        with open(pdf_path, 'wb') as f:
            f.write(response.body)
        
        self.log(f"Archivo PDF guardado temporalmente: {pdf_path}")
        
        # funcion llamada para convertir cada una de las paginas del pdf como imagenes
        self.convert_pdf_to_images(pdf_path)
        os.remove(pdf_path)
    
    def convert_pdf_to_images(self, pdf_path):
        
        # Crear folder si no existe
        image_folder = 'images'
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)
        
        # Uso de libreria para converir las imagenes
        images = convert_from_path(pdf_path, dpi=300)
        
        for i, image in enumerate(images):
            base_name = os.path.basename(pdf_path).replace('.pdf', '')
            image_file = os.path.join(image_folder, f"{base_name}_page_{i + 1}.jpg")
            image.save(image_file, 'JPEG')
            
            self.log(f"Página convertida a imagen: {image_file}")
