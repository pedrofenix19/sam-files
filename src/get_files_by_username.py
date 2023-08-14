import boto3
import json
import traceback
import os

S3_BUCKET_NAME = os.environ['S3_BUCKET_NAME']
TABLE_NAME = os.environ['DYNAMODB_TABLE_NAME']
SQS_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/280023753708/pedro-clase'

# Create SQS client
sqs = boto3.client('sqs')
s3 = boto3.client('s3')
#Creamos el recurso dynamodb
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    print(json.dumps(event))

    #Creamos el objeto tabla de DynamoDB
    table = dynamodb.Table(TABLE_NAME)

    #Obtenemos el parametro UserId del evento
    user_id = event['requestContext']['authorizer']['claims']['cognito:username']
    try:
        response = table.query(
            KeyConditionExpression='UserId = :id',
            ExpressionAttributeValues={
                ':id': user_id
            }
        )
        items = response['Items']
        
        #Debido a que las respuestas de la operacion Scan tienen un limite,
        #Debemos llamar a la funcion tantas veces sea necesario para obtener
        #todos los items
        while 'LastEvaluatedKey' in response:
            
            #Realizamos nuevamente la llamada a la operacion Scan
            response = table.query(KeyConditionExpression='UserId = :id',
                ExpressionAttributeValues={
                    ':id': user_id
                },
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            
            
            #Agregamos los items recibidos en la lista de items
            items.extend(response['Items'])
            
        #Para cada archivo obtenido, generaremos un diccionario
        #con 3 campos: filename, filesize y downloadUrl
        response_body = []
        for item in items:

            #El formato de nombre del objeto en S3 es: 
            #<nombre_usuario>/<nombre_archivo>
            object_key = f"{user_id}/{item['Filename']}"

            #Obtenemos el tamano del archivo
            object_attrs = s3.get_object_attributes(
                Bucket=S3_BUCKET_NAME,
                Key=object_key,
                ObjectAttributes=[
                    'ObjectSize'
                ]
            )
            
            #Generamos una URL prefirmada para que el 
            #usuario se pueda descargar el archivo
            presigned_url = s3.generate_presigned_url(
                ClientMethod = 'get_object',
                Params = {'Bucket': S3_BUCKET_NAME, 'Key': object_key}, 
                ExpiresIn=3600 #La URL prefirmada expira en 1 hora (3600 segundos)
            )
            
            #Armamos el objeto que se retornara para
            #este archivo
            response_item = {
                'filename': item['Filename'],
                'filesize': object_attrs['ObjectSize'],
                'downloadUrl': presigned_url
            }
            
            #Añadimos el objeto armado en la lista de objetos
            #a retornar por la api
            response_body.append(response_item)

            ##Se env'ia el mensaje a la cola SQS
            message = {
                "message": f"Archivo {response_item['filename']} de tamano {response_item['filesize']}"
            }

            response = sqs.send_message(
                QueueUrl=SQS_QUEUE_URL,
                DelaySeconds=0,
                MessageBody=json.dumps(message)
            )

        
        #Retornamos una respuesta exitosa
        return {
            'statusCode': 200,
            'body': json.dumps(response_body),
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
            'body': str(e),
            "isBase64Encoded": False,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                "Access-Control-Allow-Credentials": True
            }
        }