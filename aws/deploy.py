import boto3

def deploy_api(file_path):
    client = boto3.client("apigateway")

    with open(file_path, "r") as f:
        body = f.read()

    response = client.import_rest_api(
        body=body
    )

    api_id = response["id"]

    client.create_deployment(
        restApiId=api_id,
        stageName="prod"
    )

    return api_id
