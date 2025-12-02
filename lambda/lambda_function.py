import logging 
import json 
import os 
import boto3 
import uuid 
from datetime import datetime
logger = logging.getLogger()
logger.setLevel(logging.INFO)

DDB_TABLE = os.environ.get("DDB_TABLE")
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DDB_TABLE)

def lambda_handler(event, context):
    
    try:
    
        logger.info(f"event")
        logger.info(f"{json.dumps(event)}")

        body = json.loads(event['body'])
        logger.info(f"body")
        logger.info(body)

        inputs = body['inputs']
        propertyPrice = inputs.get("propertyPrice")
        deposit = inputs.get("deposit")
        initialRentalIncome = inputs.get("initialRentalIncome")
        annualRentIncrease = inputs.get("annualRentIncrease")
        vacancyMonths = inputs.get("vacancyMonths")
        monthlyRates = inputs.get("monthlyRates")
        monthlyLevies = inputs.get("monthlyLevies")
        monthlyInsurance = inputs.get("monthlyInsurance")
        maintenancePercent = inputs.get("maintenancePercent")
        commissionPercent = inputs.get("commissionPercent")
        cleaningPercent = inputs.get("cleaningPercent")
        monthlyWaterElec = inputs.get("monthlyWaterElec")
        monthlyWifi = inputs.get("monthlyWifi")
        monthlySecurity = inputs.get("monthlySecurity")
        annualExpenseIncrease = inputs.get("annualExpenseIncrease")
        loanTerm = inputs.get("loanTerm")
        
        # Generate a unique ID
        analysis_id = str(uuid.uuid4())
        current_time = str(datetime.now())

        # Create the DynamoDB item
        item = {
            'id': analysis_id,
            'createdAt': current_time,
            'propertyPrice': propertyPrice,
            'deposit': deposit,
            'initialRentalIncome': initialRentalIncome,
            'annualRentIncrease': annualRentIncrease,
            'vacancyMonths': vacancyMonths,
            'monthlyRates': monthlyRates,
            'monthlyLevies': monthlyLevies,
            'monthlyInsurance': monthlyInsurance,
            'maintenancePercent': maintenancePercent,
            'commissionPercent': commissionPercent,
            'cleaningPercent': cleaningPercent,
            'monthlyWaterElec': monthlyWaterElec,
            'monthlyWifi': monthlyWifi,
            'monthlySecurity': monthlySecurity,
            'annualExpenseIncrease': annualExpenseIncrease,
            'loanTerm': loanTerm,
        }
        
        # Store in DynamoDB
        table.put_item(Item=item)

        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers" : "*",
                "Access-Control-Allow-Methods" : "POST, OPTIONS",
                "Content-Type": "application/json"
                        },
            "body": json.dumps({"message": "Success"})
        }
    except Exception as e:
        logger.error(f"failed to process: {e}")
        return {
            'statusCode': 500,
            'headers': {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers" : "*",
                "Access-Control-Allow-Methods" : "POST, OPTIONS",
                "Content-Type": "application/json"
                    },
            'body': json.dumps({
                'message': 'Error storing analysis',
                'error': str(e)
            })
        }