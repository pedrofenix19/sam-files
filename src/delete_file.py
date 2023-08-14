import boto3
import json
import traceback
import os

# Utilizamos variables de entorno para el nombre del bucket
# y la tabla de dynamodb
S3_BUCKET_NAME = os.environ['S3_BUCKET_NAME']
DYNAMODB_TABLE_NAME = os.environ['DYNAMODB_TABLE_NAME']

def lambda_handler(event, context):
    print(json.dumps(event))
    try:
        # Extraemos el nombre de usuario de la data retornada por Cognito
        username = event['requestContext']['authorizer']['claims']['cognito:username']
        
        # Extraemos el nombre del archivo a borrar del query string
        filename = event['queryStringParameters']['filename']

        #Creamos el cliente de S3
        s3 = boto3.client('s3')
        
        # Borramos el archivo de S3
        # Recordemos que en el bucket los archivos se guardan en la carpeta
        # correspondiente al usuario que inici'o sesi'on
        s3.delete_object(Bucket=S3_BUCKET_NAME, Key=f"{username}/{filename}")

        # Creamos el objeto resource de dynamodb
        dynamodb = boto3.resource('dynamodb')
        
        # Creamos el objeto Table de dynamodb
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        
        #De la tabla de dynamodb, borramos el item con clave hash 'userId'
        #y sort key filename
        table.delete_item(Key={
            'UserId': username,
            'Filename': filename
        })

        # Retornamos una respuesta exitosa
        return {
            'statusCode': 200,
            'body': f'El archivo {filename} del usuario {username} fue borrado.',
            "isBase64Encoded": False,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                "Access-Control-Allow-Credentials": True
            }
        }
    except Exception as e:
        #En caso de error imprimimos un mensaje de error
        #en los logs
        print(f"Error: {e}")

        #Tambien imprimimos el stack trace
        traceback.print_exc()

        #Retornamos codigo de error 500
        return {
            'statusCode': 500,
            'body': f'Error borrando archivo: {str(e)}',
            "isBase64Encoded": False,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                "Access-Control-Allow-Credentials": True
            }
        }
