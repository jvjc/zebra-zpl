import uuid
import qrcode
import cups
from zplgrf import GRF
from io import BytesIO
import argparse

# Parser de opciones del script
parser = argparse.ArgumentParser(description="Envia los qr a la impresora Zebra mediante cups")
parser.add_argument("printer_name", help="Nombre de la impresora")
parser.add_argument("--prefix", help="Prefix añadido al uuid del qr", default="*:")
parser.add_argument("--rows", help="Filas a imprimir", default=1)
parser.add_argument("--cols", help="Número de columnas [2 o 3 disponible]", default=3)

# Validación de los args
args = parser.parse_args()

def main(prefix = "*:", rows = 1, cols = 3):
    # Se crea la conexión con cups
    conn = cups.Connection()

    # Se obtiene el nombre de la impresora a usar
    printer_name = args.printer_name
    
    # Archivo temporal a enviar como raw
    label_file_path = "/tmp/label.zpl"
    
    # Se revisar si existe la impresora, en caso contrario se despliegan las disponibles
    if printer_name != "None":
        printers = conn.getPrinters()
        if printer_name not in printers.keys():
            print("printer not found\n\navailable printer:")
            print("\n".join(printers.keys()))
            return False
    
    # Comenzamos el archivo zql vacío
    global_zpl = ""
    
    for idx in range(int(rows)):
        # Se verifica cuantas columnas se ingresó para crear el tamaño del qr
        if cols == 3:
            qr_size = 2
        else:
            qr_size = 4
            
        # Se obtiene el qr izquiedo
        grf_left = GRF.from_image(generate_qr(prefix, qr_size), "L" + str(idx)[:7])
        grf_left.optimise_barcodes()
        qr_left = grf_left.to_zpl_line(compression=3, quantity=1)
        
        # Se obtiene el qr derecho
        grf_right = GRF.from_image(generate_qr(prefix, qr_size), "R" + str(idx)[:7])
        grf_right.optimise_barcodes()
        qr_right = grf_right.to_zpl_line(compression=3, quantity=1)
        
        # Si es de 3 columnas, entonces es el qr pequeño
        if cols == 3:
            # Se crea un qr central
            grf_center = GRF.from_image(generate_qr(prefix, qr_size), "C" + str(idx)[:7])
            grf_center.optimise_barcodes()
            qr_center = grf_center.to_zpl_line(compression=3, quantity=1)
            
            # Se posicionan los qr en la fila en diferente x
            zpl = [
                qr_left,
                qr_right,
                qr_center,
                "^XA",
                "^LH32,8",
                "^XGR:L" + str(idx)[:7] + ".GRF,1,1",
                "^FS",
                "^LH172,8",
                "^XGR:C" + str(idx)[:7] + ".GRF,1,1",
                "^FS",
                "^LH312,8",
                "^XGR:R" + str(idx)[:7] + ".GRF,1,1",
                "^FS",
                "^XZ"
            ] 
        else: # Si es de 2 columnas es el qr super y sólo necesita 2, es el default
            zpl = [
                qr_left,
                qr_right,
                "^XA",
                "^LH0,20",
                "^XGR:L" + str(idx)[:7] + ".GRF,1,1",
                "^FS",
                "^LH214,20",
                "^XGR:R" + str(idx)[:7] + ".GRF,1,1",
                "^FS",
                "^XZ"
            ]
        
        global_zpl = global_zpl + "\n".join(zpl) + "\n"
    
    # Si viene la etiqueta no-print entonces se regresa el archivo zpl
    if printer_name == "None":
        print(global_zpl)
    else:
        f = open(label_file_path, "w")
        # Se guarda el archivo y se agrega el comando para eliminar las imagenes que se requirieron en la máquina
        f.write(global_zpl + "^XA^IDR:*.GRF^FS^XZ")
        f.close()

        # Se manda a imprimir como raw
        job_id = conn.printFile(printer_name, label_file_path, "Label Print", { "raw": "True" })
        
        print(job_id)
    
def generate_qr(prefix = "", size=4):
    with BytesIO() as output:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=0,
        )
        qr.add_data(prefix + str(uuid.uuid4()))
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        img.save(output, "BMP")

        return output.getvalue()

main(args.prefix, args.rows, args.cols)