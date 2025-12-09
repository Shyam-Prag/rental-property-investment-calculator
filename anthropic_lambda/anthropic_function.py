import json
import boto3
import time
from datetime import datetime
import logging 
logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client('bedrock-runtime', region_name='eu-west-1')
model_id = "anthropic.claude-3-haiku-20240307-v1:0"
# modelId = anthropic.claude-sonnet-4-20250514-v1:0

def lambda_handler(event, context):
    start_time = time.time()
    
    # Parse input
    if isinstance(event.get('body'), str):
        data = json.loads(event['body'])
        logger.info(f"incoming body converted to JSON object: {data}")
    else:
        data = json.loads(event['body'])
    
    request_id = data.get('requestId', 'unknown')
    
    # Build the prompt
    prompt = build_analysis_prompt(data)
    
    # Call Bedrock
    response = bedrock.invoke_model(
        modelId=model_id,
        contentType='application/json',
        accept='application/json',
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
    )
    logger.info(f"response from bedrock: {response}")
    # Parse response
    response_body = json.loads(response['body'].read())
    logger.info(f"Response body: {response_body}")
    
    ai_text = response_body['content'][0]['text']
    logger.info(f"AI TEXT: {ai_text}")
    
    # Extract JSON from response
    analysis = extract_json(ai_text)
    
    processing_time = int((time.time() - start_time) * 1000)
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type'
        },
        'body': json.dumps({
            'success': True,
            'requestId': request_id,
            'analysis': analysis,
            'metadata': {
                'modelUsed': model_id,
                'processingTimeMs': processing_time,
                'tokensUsed': {
                    'input': response_body.get('usage', {}).get('input_tokens', 0),
                    'output': response_body.get('usage', {}).get('output_tokens', 0)
                }
            }
        })
    }

def build_analysis_prompt(data):
    return f"""You are an expert South African property investment analyst. Analyze this rental property investment and return a JSON response.

IMPORTANT JSON RULES:
1. Return ONLY valid JSON - no markdown code blocks, no explanation text
2. All numbers must be raw integers or decimals - NO commas, NO percentage signs, NO currency symbols
3. Example: use 1450000 not 1,450,000 and use 8.5 not 8 % or 8%

## Property Data
- Purchase Price: {data['currency']} {data['propertyData']['price']:,}
- Deposit: {data['currency']} {data['propertyData']['deposit']:,}
- Loan Amount: {data['currency']} {data['propertyData']['loanAmount']:,}
- Interest Rate: {data['propertyData']['interestRate']}%
- Loan Term: {data['propertyData']['loanTermYears']} years

## Income Data
- Monthly Rent: {data['currency']} {data['incomeData']['monthlyRent']:,}
- Annual Rent Increase: {data['incomeData']['annualRentIncrease']}%
- Vacancy: {data['incomeData']['vacancyMonths']} months/year

## Monthly Expenses
- Rates: {data['currency']} {data['expenseData']['monthlyRates']}
- Levies: {data['currency']} {data['expenseData']['monthlyLevies']}
- Insurance: {data['currency']} {data['expenseData']['monthlyInsurance']}
- Water/Electricity: {data['currency']} {data['expenseData']['monthlyWaterElec']}
- WiFi: {data['currency']} {data['expenseData']['monthlyWifi']}
- Security: {data['currency']} {data['expenseData']['monthlySecurity']}
- Maintenance: {data['expenseData']['maintenancePercent']}% of rent
- Agent Commission: {data['expenseData']['commissionPercent']}% of rent
- Cleaning: {data['expenseData']['cleaningPercent']}% of rent
- Annual Expense Increase: {data['expenseData']['annualExpenseIncrease']}%

## Pre-Calculated Metrics
- Monthly Bond Payment: {data['currency']} {data['calculatedMetrics']['monthlyBondPayment']:,.2f}
- Year 1 Monthly Cashflow: {data['currency']} {data['calculatedMetrics']['year1MonthlyCashflow']:,.2f}
- Year 1 Yearly Cashflow: {data['currency']} {data['calculatedMetrics']['year1YearlyCashflow']:,.2f}
- Break-even Year: {data['calculatedMetrics']['breakEvenYear']}
- Required Deposit for Break-even: {data['currency']} {data['calculatedMetrics']['requiredDepositForBreakEven']:,.2f}
- Gross Yield: {data['calculatedMetrics']['grossYield']:.2f}%
- Net Yield: {data['calculatedMetrics']['netYield']:.2f}%

## Location
- Suburb: {data.get('location', {}).get('suburb', 'Not specified')}
- City: {data.get('location', {}).get('city', 'Not specified')}
- Province: {data.get('location', {}).get('province', 'Not specified')}
- Country: {data.get('location', {}).get('country', 'South Africa')}

## 20-Year Projection Summary
- Year 1 Cashflow: {data['currency']} {data['calculatedMetrics']['yearlyProjections'][0]['yearlyCashflow']:,.2f}
- Year 5 Cashflow: {data['currency']} {data['calculatedMetrics']['yearlyProjections'][4]['yearlyCashflow']:,.2f}
- Year 10 Cashflow: {data['currency']} {data['calculatedMetrics']['yearlyProjections'][9]['yearlyCashflow']:,.2f}
- Year 20 Cashflow: {data['currency']} {data['calculatedMetrics']['yearlyProjections'][19]['yearlyCashflow']:,.2f}

Return ONLY valid JSON (no markdown, no explanation) in this exact format:
{{
  "scorecard": {{
    "overallScore": <0-100 integer>,
    "verdict": "<EXCELLENT|GOOD|FAIR|POOR|AVOID>",
    "categories": {{
      "cashFlow": {{"score": <0-100>, "label": "<Excellent|Good|Fair|Poor>", "summary": "<1 sentence>"}},
      "yield": {{"score": <0-100>, "label": "<Excellent|Good|Fair|Poor>", "summary": "<1 sentence>"}},
      "risk": {{"score": <0-100>, "label": "<Low|Moderate|High|Very High>", "summary": "<1 sentence>"}},
      "growth": {{"score": <0-100>, "label": "<Excellent|Good|Fair|Poor>", "summary": "<1 sentence>"}},
      "location": {{"score": <0-100>, "label": "<Excellent|Good|Fair|Poor>", "summary": "<1 sentence>"}}
    }},
    "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"]
  }},
  "locationInsights": {{
    "neighborhoodProfile": "<2-3 sentences about the area>",
    "rentalDemand": {{"level": "<High|Medium|Low>", "trend": "<Growing|Stable|Declining>", "details": "<1 sentence>"}},
    "marketTrends": {{"priceGrowth": "<X-Y% annually>", "rentalGrowth": "<X-Y% annually>"}},
    "growthProjection": {{"fiveYear": "<X-Y% appreciation>", "tenYear": "<X-Y% appreciation>"}},
    "risks": ["<risk 1>", "<risk 2>"]
  }},
  "recommendations": {{
    "actions": [
      {{"priority": 1, "title": "<action title>", "description": "<1-2 sentences>", "impact": "<High|Medium|Low>"}},
      {{"priority": 2, "title": "<action title>", "description": "<1-2 sentences>", "impact": "<High|Medium|Low>"}},
      {{"priority": 3, "title": "<action title>", "description": "<1-2 sentences>", "impact": "<High|Medium|Low>"}}
    ],
    "financialProjections": {{
      "fiveYear": {{"totalEquity": 1450000, "cashOnCashReturn": 8.5}},
      "tenYear": {{"totalEquity": 2200000, "cashOnCashReturn": 12.0}},
      "twentyYear": {{"totalEquity": 3800000, "cashOnCashReturn": 18.0}}
    }}
  }}
}}

Scoring guidelines:
- overallScore: 80+ = EXCELLENT, 65-79 = GOOD, 50-64 = FAIR, 35-49 = POOR, <35 = AVOID
- Consider SA market conditions, current interest rates, and location-specific factors
- Be realistic about {data.get('location', {}).get('suburb', 'the area')}'s rental market"""

def extract_json(text):
    # Try to parse directly first
    logger.info(f"extracting json: {text}")
    try:
        return json.loads(text)
    except:
        logger.error("unable to pass incoming json")
        pass
        
    
    # Find JSON in response
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except:
            pass
    
    # Return fallback
    print("Falling back to default response.")
    return {
        "scorecard": {
            "overallScore": 50,
            "verdict": "FAIR",
            "categories": {
                "cashFlow": {"score": 50, "label": "Fair", "summary": "Analysis unavailable"},
                "yield": {"score": 50, "label": "Fair", "summary": "Analysis unavailable"},
                "risk": {"score": 50, "label": "Moderate", "summary": "Analysis unavailable"},
                "growth": {"score": 50, "label": "Fair", "summary": "Analysis unavailable"},
                "location": {"score": 50, "label": "Fair", "summary": "Analysis unavailable"}
            },
            "strengths": ["Data received successfully"],
            "weaknesses": ["Could not parse AI response"]
        },
        "locationInsights": {
            "neighborhoodProfile": "Analysis unavailable",
            "rentalDemand": {"level": "Unknown", "trend": "Unknown", "details": ""},
            "marketTrends": {"priceGrowth": "Unknown", "rentalGrowth": "Unknown"},
            "growthProjection": {"fiveYear": "Unknown", "tenYear": "Unknown"},
            "risks": []
        },
        "recommendations": {
            "actions": [],
            "financialProjections": {
                "fiveYear": {"totalEquity": 0, "cashOnCashReturn": 0},
                "tenYear": {"totalEquity": 0, "cashOnCashReturn": 0},
                "twentyYear": {"totalEquity": 0, "cashOnCashReturn": 0}
            }
        }
    }
