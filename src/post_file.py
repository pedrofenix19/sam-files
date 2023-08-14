import os
import boto3
import base64
import traceback
import json

# Utilizamos variables de entorno para el nombre del bucket
# y la tabla de dynamodb
S3_BUCKET_NAME = os.environ['S3_BUCKET_NAME']
DYNAMODB_TABLE_NAME = os.environ['DYNAMODB_TABLE_NAME']

def lambda_handler(event, context):
    try:
        print(json.dumps(event))
        # Obtenemos el nombre de usuario, el nombre del archivo 
        #y el contenido del mismo en base64
        username = event['requestContext']['authorizer']['claims']['cognito:username']
        body = json.loads(event['body'])
        filename = body['filename']
        file_content_base64 = body['content']

        # Decodificamos a bytes el contenido del archivo en base64
        file_content_bytes = base64.b64decode(file_content_base64)

        # Subimos el archivo a S3
        s3 = boto3.client('s3')
        s3.put_object(Bucket=S3_BUCKET_NAME, Key=f"{username}/{filename}", Body=file_content_bytes)

        # Copiamos la información sobre el usuario y el nombre del archivo a dynamodb
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        table.put_item(Item={
            'UserId': username,
            'Filename': filename
        })

        # Retornamos una respuesta exitosa
        return {
            'statusCode': 200,
            'body': f'El archivo {filename} del usuario {username} fue subido.',
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
            'body': f'Error uploading file to S3 or writing item to DynamoDB: {str(e)}',
            "isBase64Encoded": False,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                "Access-Control-Allow-Credentials": True
            }
        }
