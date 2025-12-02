import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';

import * as lambda from "aws-cdk-lib/aws-lambda";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { join } from 'path';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { HttpMethod } from 'aws-cdk-lib/aws-events';
import * as iam from 'aws-cdk-lib/aws-iam';

export class RentalPropertyInvestmentCalculatorStack extends cdk.Stack {
  public readonly rentalPropertyCalcRole: iam.Role;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create the DynamoDB table
    const propertyAnalysisTable = new dynamodb.Table(this, 'PropertyAnalysisTable1', {
      tableName: "rentalPropertyInvestmentCalculator1",
      partitionKey: {
        name: 'id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN, 
    });

    // Export the table name for use in Lambda
    new cdk.CfnOutput(this, 'TableName', {
      value: propertyAnalysisTable.tableName,
    });
    


    //Create Lambda execution role for retrieveAnalysis
    this.rentalPropertyCalcRole = new iam.Role(this, 'rentalPropertyCalcRole1', {
      roleName: 'rentalPropertyCalcRole1',
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      managedPolicies: [iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AWSLambdaBasicExecutionRole')],
    });
    this.rentalPropertyCalcRole.applyRemovalPolicy(cdk.RemovalPolicy.RETAIN);

    this.rentalPropertyCalcRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['dynamodb:PutItem', 'dynamodb:GetItem', 'dynamodb:UpdateItem'],
        resources: [propertyAnalysisTable.tableArn]
      }),
    );

    const myFunction = new lambda.Function(this, "rental-property-investment-calc1", {
    functionName: "rental-property-investment-calc1",
    runtime: lambda.Runtime.PYTHON_3_13, 
    handler: "lambda_function.lambda_handler",
    code: lambda.Code.fromAsset(join(__dirname, '../lambda')),
    timeout: cdk.Duration.minutes(1),
    role: this.rentalPropertyCalcRole,
    environment: {
      "DDB_TABLE":propertyAnalysisTable.tableName}
  });

  const api = new apigateway.RestApi(this, 'rentalPropApi1', {
    restApiName: 'rentalPropApi1',
    defaultCorsPreflightOptions: {
    allowOrigins: apigateway.Cors.ALL_ORIGINS,
    allowMethods: apigateway.Cors.ALL_METHODS,
    allowHeaders: apigateway.Cors.DEFAULT_HEADERS,
    allowCredentials: true,
  },
    deployOptions: {
      stageName: 'prod',
    }
  });

  const listPath = api.root.addResource('send-analysis');
  listPath.addMethod(HttpMethod.POST, new apigateway.LambdaIntegration(myFunction));
  
  }
}
