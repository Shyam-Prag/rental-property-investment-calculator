"""
AWS Lambda Function for Investment Property Analysis
This file is for reference only - copy to your AWS Lambda environment.

Requires:
- Python 3.9+
- boto3 (included in Lambda runtime)
- Bedrock access enabled in your AWS account
"""

import json
import boto3
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock = boto3.client('bedrock-runtime', region_name='eu-west-1')

# Using Claude 3 Haiku - requires stronger prompt engineering for JSON compliance
model_id = "anthropic.claude-3-haiku-20240307-v1:0"


def lambda_handler(event, context):
    start_time = time.time()
    
    # Parse input
    if isinstance(event.get('body'), str):
        data = json.loads(event['body'])
        logger.info(f"Incoming request parsed successfully")
    else:
        data = event.get('body', {})
        if isinstance(data, str):
            data = json.loads(data)
    
    request_id = data.get('requestId', 'unknown')
    
    try:
        # Build the prompt
        prompt = build_analysis_prompt(data)
        logger.info(f"Prompt built successfully for request {request_id}")
        
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
        
        # Parse response
        response_body = json.loads(response['body'].read())
        logger.info(f"Bedrock response received")
        
        ai_text = response_body['content'][0]['text']
        logger.info(f"AI TEXT length: {len(ai_text)}")
        
        # Extract and validate JSON from response
        analysis = extract_json(ai_text)
        
        # Validate the response has required structure
        if 'scorecard' not in analysis:
            logger.warning("AI returned invalid structure, using fallback")
            analysis = get_fallback_response()
        
        processing_time = int((time.time() - start_time) * 1000)

        logger.info(f"response object: {json.dumps({
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
            })}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
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
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization'
            },
            'body': json.dumps({
                'success': False,
                'requestId': request_id,
                'error': str(e),
                'analysis': get_fallback_response()
            })
        }


def build_analysis_prompt(data):
    """Build the full analysis prompt with all property data and JSON schema."""
    
    # Extract property details with defaults
    pd = data.get('propertyDetails', {})
    loc = data.get('location', {})
    metrics = data.get('calculatedMetrics', {})
    
    # Build property details section
    property_details_section = ""
    if pd:
        property_details_section = f"""
## Property Details
- Property Name: {pd.get('propertyName', 'Not specified')}
- Complex Name: {pd.get('complexName', 'Not specified')}
- Bedrooms: {pd.get('bedrooms', 'Not specified')}
- Bathrooms: {pd.get('bathrooms', 'Not specified')}
- Square Meters: {pd.get('squareMeters', 'Not specified')}
- Floor Level: {pd.get('floorLevel', 'Not specified')}
- Parking Bays: {pd.get('parkingBays', 'Not specified')}
- Building Age: {pd.get('buildingAge', 'Not specified')} years

## SA Infrastructure
- Load Shedding Ready: {pd.get('loadSheddingReady', 'Not specified')}
- Fibre Available: {'Yes' if pd.get('fibreAvailable') else 'No' if pd.get('fibreAvailable') is False else 'Not specified'}
- Water Backup: {'Yes' if pd.get('waterBackup') else 'No' if pd.get('waterBackup') is False else 'Not specified'}

## Security & Building
- 24hr Security: {'Yes' if pd.get('security24hr') else 'No' if pd.get('security24hr') is False else 'Not specified'}
- Access Control: {pd.get('accessControlType', 'Not specified')}
- CCTV Coverage: {'Yes' if pd.get('cctvCoverage') else 'No' if pd.get('cctvCoverage') is False else 'Not specified'}

## Body Corporate
- Reserve Fund Adequate: {'Yes' if pd.get('reserveFundAdequate') else 'No' if pd.get('reserveFundAdequate') is False else 'Not specified'}
- Special Levy History: {'Yes' if pd.get('specialLevyHistory') else 'No' if pd.get('specialLevyHistory') is False else 'Not specified'}

## Rental Strategy
- Short-term Allowed: {'Yes' if pd.get('shortTermAllowed') else 'No' if pd.get('shortTermAllowed') is False else 'Not specified'}
- Pet Friendly: {'Yes' if pd.get('petFriendly') else 'No' if pd.get('petFriendly') is False else 'Not specified'}
- Furnished Status: {pd.get('furnished', 'Not specified')}"""

    # Build yearly projection summary
    projections = metrics.get('yearlyProjections', [])
    projection_summary = ""
    if len(projections) >= 20:
        projection_summary = f"""
## 20-Year Projection Summary
- Year 1 Cashflow: {data['currency']} {projections[0].get('yearlyCashflow', 0):,.2f}
- Year 5 Cashflow: {data['currency']} {projections[4].get('yearlyCashflow', 0):,.2f}
- Year 10 Cashflow: {data['currency']} {projections[9].get('yearlyCashflow', 0):,.2f}
- Year 20 Cashflow: {data['currency']} {projections[19].get('yearlyCashflow', 0):,.2f}"""

    return f"""You are a JSON-only API. You output ONLY valid JSON with no other text.

TASK: Analyze this South African property investment and return a JSON response.

CRITICAL RULES:
1. Output ONLY the JSON object - no explanations, no markdown, no text before or after
2. Use the EXACT structure shown at the end of this prompt
3. All numbers must be raw (use 1450000 not 1,450,000)
4. Start your response with {{ and end with }}

## Financial Data
- Purchase Price: {data['currency']} {data['propertyData']['price']:,}
- Deposit: {data['currency']} {data['propertyData']['deposit']:,}
- Loan Amount: {data['currency']} {data['propertyData']['loanAmount']:,}
- Interest Rate: {data['propertyData']['interestRate']}%
- Loan Term: {data['propertyData']['loanTermYears']} years
{property_details_section}

## Location
- Suburb: {loc.get('suburb', 'Not specified')}
- City: {loc.get('city', 'Not specified')}
- Province: {loc.get('province', 'Not specified')}
- Country: {loc.get('country', 'South Africa')}

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
- Monthly Bond Payment: {data['currency']} {metrics.get('monthlyBondPayment', 0):,.2f}
- Year 1 Monthly Cashflow: {data['currency']} {metrics.get('year1MonthlyCashflow', 0):,.2f}
- Year 1 Yearly Cashflow: {data['currency']} {metrics.get('year1YearlyCashflow', 0):,.2f}
- Break-even Year: {metrics.get('breakEvenYear', 'N/A')}
- Required Deposit for Break-even: {data['currency']} {metrics.get('requiredDepositForBreakEven', 0):,.2f}
- Gross Yield: {metrics.get('grossYield', 0):.2f}%
- Net Yield: {metrics.get('netYield', 0):.2f}%
{projection_summary}

Consider these SA-specific factors in your analysis:
- Load shedding readiness significantly impacts tenant demand and rental premiums
- Fibre availability is increasingly important for remote workers
- Security features are crucial for SA rental properties
- Body corporate health affects long-term investment viability
- Short-term rental allowance can significantly impact yield potential

Return ONLY valid JSON (no markdown, no explanation) in this EXACT format:
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
      "fiveYear": {{"totalEquity": <number>, "cashOnCashReturn": <decimal>}},
      "tenYear": {{"totalEquity": <number>, "cashOnCashReturn": <decimal>}},
      "twentyYear": {{"totalEquity": <number>, "cashOnCashReturn": <decimal>}}
    }}
  }}
}}

Scoring guidelines:
- overallScore: 80+ = EXCELLENT, 65-79 = GOOD, 50-64 = FAIR, 35-49 = POOR, <35 = AVOID
- Consider SA market conditions, current interest rates ({data['propertyData']['interestRate']}%), and location-specific factors
- Be realistic about {loc.get('suburb', 'the area')}'s rental market in {loc.get('city', 'South Africa')}"""


def extract_json(text):
    """Extract JSON from AI response text."""
    logger.info(f"Extracting JSON from response")
    
    # Try to parse directly first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.info("Direct JSON parse failed, trying to extract from text")
    
    # Remove markdown code blocks if present
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    
    # Try parsing again after removing markdown
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    
    # Find JSON in response by locating outermost braces
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError as e:
            logger.error(f"JSON extraction failed: {str(e)}")
    
    # Return fallback
    logger.warning("Falling back to default response")
    return get_fallback_response()


def get_fallback_response():
    """Return a fallback response when AI fails to generate valid analysis."""
    return {
        "scorecard": {
            "overallScore": 50,
            "verdict": "FAIR",
            "categories": {
                "cashFlow": {"score": 50, "label": "Fair", "summary": "Analysis could not be completed - please try again."},
                "yield": {"score": 50, "label": "Fair", "summary": "Analysis could not be completed - please try again."},
                "risk": {"score": 50, "label": "Moderate", "summary": "Analysis could not be completed - please try again."},
                "growth": {"score": 50, "label": "Fair", "summary": "Analysis could not be completed - please try again."},
                "location": {"score": 50, "label": "Fair", "summary": "Analysis could not be completed - please try again."}
            },
            "strengths": ["Data received successfully", "Calculator metrics computed"],
            "weaknesses": ["AI analysis could not be generated", "Please retry the analysis"]
        },
        "locationInsights": {
            "neighborhoodProfile": "Location analysis could not be completed. Please try again.",
            "rentalDemand": {"level": "Unknown", "trend": "Unknown", "details": "Analysis unavailable"},
            "marketTrends": {"priceGrowth": "Unknown", "rentalGrowth": "Unknown"},
            "growthProjection": {"fiveYear": "Unknown", "tenYear": "Unknown"},
            "risks": ["Analysis incomplete - please retry"]
        },
        "recommendations": {
            "actions": [
                {"priority": 1, "title": "Retry Analysis", "description": "The AI analysis did not complete successfully. Please try again.", "impact": "High"}
            ],
            "financialProjections": {
                "fiveYear": {"totalEquity": 0, "cashOnCashReturn": 0},
                "tenYear": {"totalEquity": 0, "cashOnCashReturn": 0},
                "twentyYear": {"totalEquity": 0, "cashOnCashReturn": 0}
            }
        }
    }
