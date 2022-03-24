import io
import argparse
import json
from typing import Union

from PyPDF2 import PdfFileWriter, PdfFileReader, PdfFileMerger
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
from reportlab.lib.units import mm
from reportlab.graphics.barcode import eanbc, qr
from reportlab.graphics.shapes import Drawing

class ElementProcessor:
    def process(self, elem_options: dict, can: canvas.Canvas):
        pass


class ExampleTextElementProcessor(ElementProcessor):
    def process(self, elem_options: dict, can: canvas.Canvas):
        print(elem_options)
        text = elem_options['text'] if 'text' in elem_options else "<Text>"
        can.setFont('Helvetica', 10)
        can.setFillColorRGB(0.5, 0.5, 0.5)
        can.drawString(250, 25, text)


# TODO: This should use Aruco markers or so
class ExampleCornerMarkersElementProcessor(ElementProcessor):
    def process(self, elem_options: dict, can: canvas.Canvas):
        can.setFillColorRGB(0, 0, 0)

        qr_code = qr.QrCodeWidget('example')
        bounds = qr_code.getBounds()
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        d = Drawing(50, 50, transform=[50. / width, 0, 0, 50. / height, 0, 0])
        d.add(qr_code)
        d.drawOn(can, 525, 775)

        qr_code = qr.QrCodeWidget(str('example'))
        bounds = qr_code.getBounds()
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        d = Drawing(50, 50, transform=[50. / width, 0, 0, 50. / height, 0, 0])
        d.add(qr_code)

        d.drawOn(can, 25, 775)

        can.setLineWidth(1.5)
        can.rect(25, 25, 10, 10, stroke=1, fill=0)
        can.rect(560, 25, 10, 10, stroke=1, fill=0)

        can.setLineWidth(3)
        can.rect(28.5, 28.5, 3, 3, stroke=1, fill=0)
        can.rect(563.5, 28.5, 3, 3, stroke=1, fill=0)


# A simple dictionary with element processor callbacks
element_processors = {
    'example_text': ExampleTextElementProcessor(),
    'example_corner_markers': ExampleCornerMarkersElementProcessor(),
}



def register_element_processor(type : str, ep: ElementProcessor, override : bool = False):
    assert override or type not in element_processors
    element_processors[type] = ep


def process(template_path: str, json_config_path: str, output_path: str):

    json_config = {}
    with open(json_config_path) as json_file:
        json_config = json.load(json_file)


    # we convert a single config to a list (when we want to
    if isinstance(json_config, dict):
        json_config = [json_config]

    # Create new output
    output = PdfFileWriter()

    for config in json_config:
        # Load template file into memory
        # TODO: can we cache this?
        template = PdfFileReader(open(template_path, 'rb'))

        if 'pages' in config:
            max_pages = max(template.getNumPages(), len(config['pages']))
        else:
            max_pages = template.getNumPages()

        for p in range(0, max_pages):

            if p < template.getNumPages():
                template_page = template.getPage(p)

            if 'pages' in config and p < len(config['pages']):
                page_config = config['pages'][p]

                # Create an overlay for this page with Reportlab
                # TODO: Support other pagesizes etc.
                packet = io.BytesIO()
                overlay_can = canvas.Canvas(packet, pagesize=A4)

                if 'elements' in page_config:
                    for elem_config in page_config['elements']:
                        assert 'type' in elem_config
                        assert elem_config['type'] in element_processors
                        elem_options = elem_config['options'] if 'options' in elem_config else {}
                        element_processors[elem_config['type']].process(elem_options, overlay_can)

                overlay_can.save()
                packet.seek(0)
                overlay = PdfFileReader(packet)

            assert template_page or overlay

            if template_page and overlay:
                page = template_page
                page.mergePage(overlay.getPage(0))
            elif template_page:
                page = template_page
            else:
                page = overlay # no template page given
            output.addPage(page)

    # Finally, write "output" to a real file
    outputStream = open(output_path, "wb")
    output.write(outputStream)
    outputStream.close()



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Overlay Elements')
    parser.add_argument('--template_path', '-t', type=str, help='The path to the template')
    parser.add_argument('--config_path', '-c', type=str, help='The path to the base template')
    parser.add_argument('--output_path', '-o', type=str, help='The path to the base template')

    args = parser.parse_args()
    process(args.template_path, args.config_path, args.output_path)


